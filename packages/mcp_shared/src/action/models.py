# Copyright 2026 NXP
#
# NXP Proprietary. This software is owned or controlled by NXP and may
# only be used strictly in accordance with the applicable license terms.
# By expressly accepting such terms or by downloading, installing,
# activating and/or otherwise using the software, you are agreeing that
# you have read, and that you agree to comply with and are bound by,
# such license terms.  If you do not agree to be bound by the applicable
# license terms, then you may not retain, install, activate or otherwise
# use the software.

"""Core action data models.

This module defines the canonical in-memory representation for action metadata,
executable action entries, mutable action catalogs, and agent-facing payloads
such as ``input_schema`` and contract payloads.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable

from .errors import (
    DEFAULT_SCHEMA_VERSION,
    INTERNAL_ERROR,
    classify_error_type,
    default_retryable,
    default_severity,
    emit_code,
    supports_canonical_codes,
)

JSONSchema = dict[str, Any]
ActionHandler = Callable[[dict[str, Any]], Awaitable[Any]]
ContextualActionHandler = Callable[[dict[str, Any], Any], Awaitable[Any]]
ExecutableActionHandler = ActionHandler | ContextualActionHandler
ResultNormalizer = Callable[[Any], Any]


class DuplicatePolicy(StrEnum):
    """Supported strategies for handling duplicate action names."""

    ERROR = "error"
    REPLACE = "replace"
    IGNORE = "ignore"


class ActionExecutionError(Exception):
    """Structured execution error that maps directly to protocol error payloads.

    The ``error_code`` and ``error_message`` fields are the stable, historical
    contract. The keyword-only ``error_type``, ``severity``, ``retryable``,
    ``retry_after_ms``, and ``cause`` fields are optional enrichments; when a
    caller leaves them unset the shared response builder derives sensible
    defaults from the (code, message) pair, so raising this exception the old
    way keeps working unchanged.
    """

    def __init__(
        self,
        error_code: int,
        error_message: str,
        *,
        error_details: dict[str, Any] | None = None,
        error_type: str | None = None,
        severity: str | None = None,
        retryable: bool | None = None,
        retry_after_ms: int | None = None,
        cause: dict[str, Any] | None = None,
    ) -> None:
        """Store protocol-facing error fields for later response generation."""

        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.error_details = error_details or {}
        self.error_type = error_type
        self.severity = severity
        self.retryable = retryable
        self.retry_after_ms = retry_after_ms
        self.cause = cause


@dataclass(frozen=True)
class ActionOutcome:
    """Structured result for action-related operations.

    ``result`` / ``error_code`` / ``error_message`` / ``error_details`` are the
    historical, stable fields. The remaining fields are additive enrichments
    that only surface extra keys in :meth:`to_response`; they never change the
    legacy keys, and the numeric ``code`` is only remapped when the caller
    negotiates a canonical ``schema_version``.
    """

    result: Any = None
    error_code: int | None = None
    error_message: str | None = None
    error_details: dict[str, Any] | None = None
    error_type: str | None = None
    severity: str | None = None
    retryable: bool | None = None
    retry_after_ms: int | None = None
    cause: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    warnings: list[dict[str, Any]] | None = None
    schema_version: str = DEFAULT_SCHEMA_VERSION

    @property
    def success(self) -> bool:
        """Return ``True`` when execution completed without a protocol error."""

        return self.error_code is None

    def to_response(self, *, schema_version: str | None = None) -> dict[str, Any]:
        """Convert the outcome into the standard tool response payload.

        With the default (legacy) schema version the ``error.code`` and
        ``error.message`` are byte-for-byte identical to the historical
        behavior. Enrichment keys (``errorType``, ``severity``, ``retryable``,
        ``retryAfterMs``, ``cause``) are added additively. Passing (or setting
        on the outcome) a canonical schema version opts into the de-overloaded
        numeric code space.
        """

        effective_version = schema_version or self.schema_version

        if self.success:
            response: dict[str, Any] = {
                "success": True,
                "result": self.result,
            }
            if self.warnings:
                response["warnings"] = self.warnings
            meta = self._build_meta(effective_version)
            if meta:
                response["meta"] = meta
            return response

        message = self.error_message or "INTERNAL_ERROR"
        error_type = self.error_type or classify_error_type(self.error_code, message)
        emitted_code = emit_code(
            self.error_code if self.error_code is not None else INTERNAL_ERROR,
            message,
            schema_version=effective_version,
        )

        error_block: dict[str, Any] = {
            "code": emitted_code if emitted_code is not None else INTERNAL_ERROR,
            "message": message,
            "errorType": str(error_type),
            "severity": self.severity or str(default_severity(error_type)),
            "retryable": (
                self.retryable
                if self.retryable is not None
                else default_retryable(error_type)
            ),
        }
        if self.retry_after_ms is not None:
            error_block["retryAfterMs"] = self.retry_after_ms
        if self.error_details:
            error_block["details"] = self.error_details
        if self.cause:
            error_block["cause"] = self.cause

        response = {
            "success": False,
            "error": error_block,
        }
        meta = self._build_meta(effective_version)
        if meta:
            response["meta"] = meta
        return response

    def _build_meta(self, effective_version: str | None) -> dict[str, Any]:
        """Assemble the additive ``meta`` block, if any metadata is present.

        To keep the default (legacy) response byte-identical, the ``meta`` block
        is emitted only when there is caller-supplied metadata or when a
        canonical (non-legacy) schema version was negotiated. A plain default
        call therefore returns exactly ``{"success": ..., ...}`` as before.
        """

        meta: dict[str, Any] = dict(self.meta) if self.meta else {}
        if meta or supports_canonical_codes(effective_version):
            if effective_version:
                meta.setdefault("schemaVersion", effective_version)
        return meta


@dataclass(frozen=True)
class ActionParameter:
    """Declarative description of one public action parameter."""

    name: str
    required: bool
    schema: JSONSchema


def action_parameters_from_openrpc(declared: Any) -> tuple[ActionParameter, ...]:
    """Map an OpenRPC Method Object's ``params`` into ``ActionParameter`` values.

    Defensive by design: entries that are not dicts, or that lack a string
    ``name``, are skipped. Suitable for both discovered (live) method objects
    and locally-declared static-method param lists.
    """

    parameters: list[ActionParameter] = []
    for entry in declared or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        parameters.append(
            ActionParameter(
                name=name,
                required=bool(entry.get("required", False)),
                schema=dict(entry.get("schema") or {}),
            )
        )
    return tuple(parameters)


def category_from_openrpc(method_detail: dict) -> str | None:
    """Return the first OpenRPC tag name, used as the action category."""

    tags = method_detail.get("tags") or []
    if tags and isinstance(tags[0], dict):
        name = tags[0].get("name")
        if isinstance(name, str) and name.strip():
            return name
    return None


@dataclass(frozen=True)
class ActionContract:
    """Declarative metadata for one action exposed to an agent or caller."""

    name: str
    description: str
    params: tuple[ActionParameter, ...]
    category: str | None = None
    example: dict[str, Any] | None = None
    preconditions: tuple[str, ...] = field(default_factory=tuple)
    workflow_hints: tuple[str, ...] = field(default_factory=tuple)
    related_actions: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        # runtime validation in post init
        if not isinstance(self.params, tuple):
            object.__setattr__(self, 'params', tuple(self.params))
        if not self.name or not self.name.strip():
            raise ValueError("ActionContract.name must not be empty")
        if not self.description or not self.description.strip():
            raise ValueError("ActionContract.description must not be empty")

    @property
    def input_schema(self) -> JSONSchema:
        """Derive the JSON Schema used to validate public action params."""

        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.params:
            properties[param.name] = dict(param.schema)
            if param.required:
                required.append(param.name)

        schema: JSONSchema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return schema

    def to_contract_payload(self) -> dict[str, Any]:
        """Serialize the contract into the standard agent-facing payload."""

        payload: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
        if self.category:
            payload["category"] = self.category
        if self.example is not None:
            payload["example"] = self.example
        if self.preconditions:
            payload["preconditions"] = list(self.preconditions)
        if self.workflow_hints:
            payload["workflow_hints"] = list(self.workflow_hints)
        if self.related_actions:
            payload["related_actions"] = list(self.related_actions)
        return payload


@dataclass(frozen=True)
class ActionExecutable:
    """Executable action entry composed of contract metadata plus a runtime handler."""

    contract: ActionContract
    handler: ExecutableActionHandler


@dataclass
class ActionCatalog:
    """Mutable active action catalog owned by one component."""

    actions: dict[str, ActionExecutable]

    @property
    def categories(self) -> list[str]:
        """Return the sorted set of explicit action categories present in the catalog."""

        return sorted({action.contract.category for action in self.actions.values() if action.contract.category})

    def get(self, action_name: str) -> ActionExecutable | None:
        """Look up one executable action by its public action name."""

        return self.actions.get(action_name)

    def add_action(self, action: ActionExecutable, *, replace: bool = False) -> None:
        """Add one executable action to the active catalog.

        Set ``replace=True`` to overwrite an existing action with the same name.

        TODO: This API is intended to support live addition to the active
        catalog. It is not currently covered by dedicated tests and is kept as
        a public API for future expansion and hardening.
        """

        action_name = action.contract.name
        if action_name in self.actions and not replace:
            raise ValueError(f"Duplicate action '{action_name}'")
        self.actions[action_name] = action

    def merge_actions(
        self,
        actions: Iterable[ActionExecutable],
        *,
        duplicate_policy: str = "error",
    ) -> None:
        """Merge multiple executable actions into the active catalog.

        Supported duplicate policies are ``error``, ``replace``, and ``ignore``.
        """

        policy = DuplicatePolicy(duplicate_policy)

        for action in actions:
            action_name = action.contract.name
            if action_name in self.actions:
                if policy is DuplicatePolicy.ERROR:
                    raise ValueError(f"Duplicate action '{action_name}'")
                if policy is DuplicatePolicy.IGNORE:
                    continue
            self.actions[action_name] = action
