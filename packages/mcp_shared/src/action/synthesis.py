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

"""Shared synthesis of executable actions from an OpenRPC document.

Any MCP server whose backend advertises its live JSON-RPC surface via the
reserved ``rpc.discover`` method turns each discovered OpenRPC Method Object
into an :class:`ActionExecutable` whose handler forwards to the live backend
through a :class:`nxp.mcp.shared.rpc.RpcClient`.

This logic used to be duplicated per component (S32DS, S32 Flash Tool, ...).
It is consolidated here so every component shares one implementation. The only
per-component variation is the human-readable ``source_label`` used in the
fallback description text.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from . import errors
from .models import (
    ActionContract,
    ActionExecutable,
    ActionExecutionError,
    action_parameters_from_openrpc,
    category_from_openrpc,
)
from ..rpc import RpcClient, RpcError

# Reserved OpenRPC discovery method; never surfaced as an action.
RESERVED_DISCOVER_METHOD = "rpc.discover"

# Error code used when a forwarded backend call fails.
FORWARD_ERROR_CODE = errors.FORWARD_ERROR


def example_from_openrpc(method_detail: dict) -> dict[str, Any] | None:
    """Build an example params dict from an OpenRPC Method Object.

    OpenRPC advertises examples as a list of ExamplePairing objects, each with a
    ``params`` list of ExampleObject entries carrying ``name`` and ``value``.
    The first pairing is folded into a flat ``{name: value}`` params mapping so
    it can be surfaced on the ActionContract.example field. Returns None when no
    usable example is declared.
    """

    pairings = method_detail.get("examples") or []
    for pairing in pairings:
        if not isinstance(pairing, dict):
            continue
        example_params = pairing.get("params") or []
        params: dict[str, Any] = {}
        for entry in example_params:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or "value" not in entry:
                continue
            params[name] = entry["value"]
        if params:
            return params
    return None


def workflow_hints_from_openrpc(method_detail: dict) -> tuple[str, ...]:
    """Collect workflow metadata from an OpenRPC Method Object.

    Without changing the action models, the most machine-friendly transport is
    to emit the entire structured ``workflow`` object as a single deterministic
    JSON string inside ``workflow_hints``. If no structured workflow is present,
    the legacy free-form ``hint`` field is forwarded as-is.
    """

    workflow = method_detail.get("workflow")
    if isinstance(workflow, dict) and workflow:
        return (json.dumps(workflow, ensure_ascii=False, sort_keys=True),)

    hint = method_detail.get("hint")
    if isinstance(hint, str) and hint.strip():
        return (hint.strip(),)

    return ()


def make_method_handler(client: RpcClient, method_name: str):
    """Build an async handler that forwards an action call to the live backend.

    The blocking ``RpcClient.call`` runs in a worker thread so the event loop is
    not stalled. Transport / validation / JSON-RPC errors are translated into
    ``ActionExecutionError`` so the shared dispatcher reports a structured error.
    """

    async def _handler(params: dict[str, Any]) -> Any:
        try:
            return await asyncio.to_thread(lambda: client.call(method_name, **(params or {})))
        except ValueError as exc:
            # Client-side validation failure (missing/unknown/typed param).
            raise ActionExecutionError(
                errors.INVALID_PARAMS,
                errors.ErrorLabel.INVALID_PARAMS,
                error_details={"message": str(exc)},
            ) from exc
        except RpcError as exc:
            raise ActionExecutionError(
                FORWARD_ERROR_CODE,
                errors.ErrorLabel.IDE_CALL_FAILED,
                error_details={"message": exc.message, "code": exc.code, "data": exc.data},
                error_type=str(errors.ErrorType.TOOL_EXECUTION_ERROR),
                cause={
                    "code": exc.code,
                    "message": exc.message,
                    "details": {"data": exc.data} if exc.data is not None else None,
                },
            ) from exc
        except ConnectionError as exc:
            # An unreachable backend is a transient dependency failure: mark it
            # retryable so agents can back off and retry rather than give up.
            raise ActionExecutionError(
                FORWARD_ERROR_CODE,
                errors.ErrorLabel.IDE_UNREACHABLE,
                error_details={"message": str(exc)},
                error_type=str(errors.ErrorType.DEPENDENCY_ERROR),
                retryable=True,
            ) from exc

    return _handler


def openrpc_method_to_executable_action(
    client: RpcClient,
    method_detail: dict,
    *,
    source_label: str = "the JSON-RPC server",
) -> ActionExecutable | None:
    """Convert one OpenRPC Method Object into an ``ActionExecutable``.

    ``source_label`` is used only for the fallback description text when the
    method advertises neither a ``description`` nor a ``summary`` (e.g.
    ``"the S32DS IDE"`` or ``"the S32 Flash Tool GUI"``).

    Returns ``None`` for entries that cannot be turned into a usable action
    (missing name, or the reserved ``rpc.discover`` method).
    """

    name = method_detail.get("name")
    if not isinstance(name, str) or not name.strip() or name == RESERVED_DISCOVER_METHOD:
        return None

    description = (
        method_detail.get("description")
        or method_detail.get("summary")
        or f"Invoke {source_label} '{name}' JSON-RPC method."
    )

    contract = ActionContract(
        name=name,
        description=description,
        params=action_parameters_from_openrpc(method_detail.get("params")),
        category=category_from_openrpc(method_detail),
        example=example_from_openrpc(method_detail),
        workflow_hints=workflow_hints_from_openrpc(method_detail),
    )
    return ActionExecutable(
        contract=contract,
        handler=make_method_handler(client, name),
    )
