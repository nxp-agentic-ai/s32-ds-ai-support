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

"""Shared action execution dispatcher for executable action catalogs.

This module resolves an action by name from an ``ActionCatalog``, validates its
input parameters against the contract-derived schema, invokes the runtime
handler, optionally normalizes the execution result, and returns a structured
``ActionOutcome``.
"""

import asyncio
import inspect
import logging
import time
from dataclasses import replace
from typing import Any

from . import errors
from .models import (
    ActionCatalog,
    ActionExecutable,
    ActionExecutionError,
    ActionOutcome,
    ResultNormalizer,
)
from .validation import validate_jsonschema

# Error codes are sourced from the shared registry (nxp.mcp.shared.action.errors)
# so a single numeric value has exactly one meaning across the whole MCP layer.


def _coerce_params_object(params: dict[str, Any] | None) -> tuple[dict[str, Any] | None, ActionOutcome | None]:
    """Coerce caller params into an object or return a failed outcome."""

    if params is None:
        return {}, None
    if isinstance(params, dict):
        return params, None
    return None, ActionOutcome(
        error_code=errors.INVALID_PARAMS,
        error_message=errors.ErrorLabel.INVALID_PARAMS,
        error_details={
            "message": "Expected params to be an object.",
        },
    )


def _supported_handler_argument_count(handler: Any) -> int:
    """Return how many positional arguments one action handler accepts."""

    signature = inspect.signature(handler)
    positional_params = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    return len(positional_params)


async def _invoke_handler(
    executable: ActionExecutable,
    *,
    session_manager: Any | None,
    params_object: dict[str, Any],
) -> Any:
    """Invoke an action handler that supports either ``(params)`` or ``(params, session_manager)``."""

    handler = executable.handler
    supported_arg_count = _supported_handler_argument_count(handler)

    # 1. handler(params)
    if supported_arg_count == 1:
        return await handler(params_object)

    # 2. handler(params, session_manager)
    if supported_arg_count == 2:
        return await handler(params_object, session_manager)

    raise TypeError(
        "Action handlers must accept either (params) or (params, session_manager)."
    )


def _build_response_meta(
    *,
    request_meta: dict[str, Any] | None,
    started_at: float | None,
    server_name: str | None,
    include_timing: bool,
) -> dict[str, Any] | None:
    """Assemble the additive response ``meta`` block.

    Returns ``None`` unless there is a concrete reason to emit metadata - a
    caller correlationId to echo, a server label, or an explicit timing request.
    This keeps a plain ``execute_action(...)`` call byte-identical to the
    historical response shape (no ``meta`` block at all).
    """

    correlation_id = request_meta.get("correlationId") if request_meta else None
    emit = bool(correlation_id) or bool(server_name) or include_timing
    if not emit:
        return None

    meta: dict[str, Any] = {}
    if correlation_id is not None:
        meta["correlationId"] = correlation_id
    if server_name:
        meta["serverName"] = server_name
    if started_at is not None:
        meta["durationMs"] = round((time.perf_counter() - started_at) * 1000.0, 3)
    return meta or None


async def execute_action(
    action_name: str,
    params: dict[str, Any] | None,
    action_catalog: ActionCatalog,
    *,
    component_logger: logging.Logger | None = None,
    result_normalizer: ResultNormalizer | None = None,
    session_manager: Any | None = None,
    timeout_seconds: float | None = None,
    request_meta: dict[str, Any] | None = None,
    schema_version: str | None = None,
    server_name: str | None = None,
    include_timing: bool = False,
) -> ActionOutcome:
    """Execute one action request against an ``ActionCatalog``.

    This is the canonical shared execution entry point for component action
    catalogs built from ``ActionExecutable`` values.

    Result normalization is opt-in. When ``result_normalizer`` is ``None``, the
    raw handler output becomes ``ActionOutcome.result`` unchanged.

    Optional, fully backward-compatible parameters:

    * ``request_meta`` - the caller's ``params._meta`` object. ``correlationId``
      is echoed back on the outcome ``meta`` for end-to-end tracing, and
      ``timeoutMs`` is used as the execution timeout when ``timeout_seconds``
      was not passed explicitly.
    * ``schema_version`` - envelope schema version to stamp on the outcome; only
      a canonical version changes the emitted numeric error codes.
    * ``server_name`` - namespaced sub-server label recorded in ``meta``.

    When none of these are supplied the returned outcome renders exactly like
    before through ``ActionOutcome.to_response()``.
    """

    logger = component_logger or logging.getLogger(__name__)
    started_at = time.perf_counter()
    effective_schema_version = schema_version or errors.DEFAULT_SCHEMA_VERSION

    # A request_meta.timeoutMs acts as a soft timeout hint when the caller did
    # not pass an explicit timeout_seconds.
    if timeout_seconds is None and request_meta:
        timeout_ms = request_meta.get("timeoutMs")
        if isinstance(timeout_ms, (int, float)) and timeout_ms > 0:
            timeout_seconds = float(timeout_ms) / 1000.0

    def _finalize(outcome: ActionOutcome) -> ActionOutcome:
        """Attach tracing/version metadata without altering the legacy fields."""

        meta = _build_response_meta(
            request_meta=request_meta,
            started_at=started_at,
            server_name=server_name,
            include_timing=include_timing,
        )

        return replace(
            outcome,
            meta=meta if meta else outcome.meta,
            schema_version=effective_schema_version,
        )

    resolved_action_name = (action_name or "").strip()
    action_executable = action_catalog.get(resolved_action_name)
    if action_executable is None:
        return _finalize(
            ActionOutcome(
                error_code=errors.UNKNOWN_ACTION,
                error_message=errors.ErrorLabel.UNKNOWN_ACTION,
                error_details={
                    "message": f"Unknown action '{resolved_action_name}'. Use search_actions to discover valid actions.",
                },
            )
        )

    contract = action_executable.contract
    params_object, error_outcome = _coerce_params_object(params)
    if error_outcome is not None:
        return _finalize(error_outcome)

    validation_errors = validate_jsonschema(params_object, contract.input_schema)
    if validation_errors:
        return _finalize(
            ActionOutcome(
                error_code=errors.INVALID_PARAMS,
                error_message=errors.ErrorLabel.INVALID_PARAMS,
                error_details={
                    "message": "Input validation failed.",
                    "issues": validation_errors,
                    "input_schema": contract.input_schema,
                },
            )
        )

    try:
        invoke_coro = _invoke_handler(
            action_executable,
            session_manager=session_manager,
            params_object=params_object,
        )
        raw_result = (
            await asyncio.wait_for(invoke_coro, timeout=timeout_seconds)
            if timeout_seconds is not None
            else await invoke_coro
        )
    except asyncio.TimeoutError:
        return _finalize(
            ActionOutcome(
                error_code=errors.ACTION_TIMEOUT,
                error_message=errors.ErrorLabel.ACTION_TIMEOUT,
                error_details={
                    "message": f"Action '{contract.name}' timed out after {timeout_seconds} seconds.",
                    "timeout_seconds": timeout_seconds,
                },
            )
        )
    except ActionExecutionError as exc:
        return _finalize(_outcome_from_execution_error(exc))
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Unhandled error while executing action '%s'", contract.name)
        return _finalize(
            ActionOutcome(
                error_code=errors.INTERNAL_ERROR,
                error_message=errors.ErrorLabel.INTERNAL_ERROR,
                error_details={
                    "message": str(exc),
                },
            )
        )

    if result_normalizer is None:
        return _finalize(ActionOutcome(result=raw_result))

    try:
        result = result_normalizer(raw_result)
    except ActionExecutionError as exc:
        return _finalize(_outcome_from_execution_error(exc))
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Failed to normalize result for action '%s'", contract.name)
        return _finalize(
            ActionOutcome(
                error_code=errors.RESULT_NORMALIZATION_FAILED,
                error_message=errors.ErrorLabel.RESULT_NORMALIZATION_FAILED,
                error_details={
                    "message": f"Failed to normalize result for action '{contract.name}': {exc}",
                },
            )
        )

    return _finalize(ActionOutcome(result=result))


def _outcome_from_execution_error(exc: ActionExecutionError) -> ActionOutcome:
    """Map a raised ``ActionExecutionError`` onto an ``ActionOutcome``.

    Preserves the historical fields and forwards any optional enrichment
    (``error_type``, ``severity``, ``retryable``, ``retry_after_ms``, ``cause``)
    the handler chose to set.
    """

    return ActionOutcome(
        error_code=exc.error_code,
        error_message=exc.error_message,
        error_details=exc.error_details or None,
        error_type=exc.error_type,
        severity=exc.severity,
        retryable=exc.retryable,
        retry_after_ms=exc.retry_after_ms,
        cause=exc.cause,
    )
