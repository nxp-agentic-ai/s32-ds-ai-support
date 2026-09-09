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

"""Request-boundary middleware that standardizes the input-validation layer.

The response-envelope work (``envelope.py`` + ``ActionOutcome``) standardizes
failures raised *inside* a tool body. But FastMCP validates a tool's arguments
with Pydantic *before* the body runs (inside ``FunctionTool.run`` via
``type_adapter.validate_python``). A validation failure there raises a
``pydantic.ValidationError`` that never reaches the tool body, so it bypasses
the envelope entirely and surfaces to the agent as a raw, non-JSON error string.

This module closes that gap at the one place that sits ABOVE the Pydantic layer
and applies to every server uniformly: FastMCP middleware's ``on_call_tool``
hook. Installing :func:`install_envelope_middleware` on a server does two
things:

* coerces a JSON-string ``params`` argument into an object before validation
  runs, so a transport that delivers ``params`` as a string still validates;
* catches the ``pydantic.ValidationError`` raised during argument validation
  and returns the shared ``{success: false, error: {...}}`` envelope instead of
  a raw plaintext error.

The middleware is deliberately narrow: it only acts on validation failures and
the ``params`` string case. Successful calls and failures raised inside tool
bodies pass through untouched, preserving the additive contract.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from . import errors

logger = logging.getLogger(__name__)

# The MCP argument key that the *_execute_action tools declare as a dict but
# that the transport may deliver as a JSON string.
_PARAMS_KEY = "params"


def _validation_error_envelope(
    *,
    message: str,
    tool_name: str | None,
    validation_errors: Any | None = None,
) -> dict[str, Any]:
    """Build the standardized VALIDATION_ERROR envelope for a bad request."""

    details: dict[str, Any] = {"message": message}
    if validation_errors is not None:
        details["validation_errors"] = validation_errors
    if tool_name:
        details["tool"] = tool_name

    error_type = errors.ErrorType.VALIDATION_ERROR
    return {
        "success": False,
        "error": {
            "code": errors.INVALID_PARAMS,
            "message": str(errors.ErrorLabel.INVALID_PARAMS),
            "errorType": str(error_type),
            "severity": str(errors.default_severity(error_type)),
            "retryable": errors.default_retryable(error_type),
            "details": details,
        },
    }


def _coerce_params_argument(arguments: Any, tool_name: str | None) -> dict[str, Any] | None:
    """Coerce a JSON-string ``params`` argument into an object, in place.

    Returns ``None`` on success (arguments left ready for validation), or a
    standardized VALIDATION_ERROR envelope when the string is not valid JSON.
    Anything that is not a dict-with-string-``params`` is left untouched.
    """

    if not isinstance(arguments, dict):
        return None
    raw = arguments.get(_PARAMS_KEY)
    if not isinstance(raw, str):
        return None
    try:
        arguments[_PARAMS_KEY] = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        return _validation_error_envelope(
            message=(
                f"'{_PARAMS_KEY}' must be a JSON object or a JSON string that "
                f"decodes to an object; failed to parse: {exc}"
            ),
            tool_name=tool_name,
        )
    return None


def _make_tool_result(envelope: dict[str, Any]):
    """Wrap a standardized envelope in a FastMCP ToolResult.

    Imported lazily so ``mcp_shared`` does not hard-depend on a specific FastMCP
    module layout at import time.
    """

    from fastmcp.tools.tool import ToolResult

    return ToolResult(structured_content=envelope)


async def _on_call_tool(context: Any, call_next: Any):
    """Shared ``on_call_tool`` body used by the middleware built below.

    Kept as a module-level coroutine (rather than only a method) so it can be
    unit-tested directly without constructing the FastMCP middleware object.
    """

    message = getattr(context, "message", None)
    tool_name = getattr(message, "name", None)
    arguments = getattr(message, "arguments", None)

    # coerce a JSON-string `params` before validation runs.
    coercion_error = _coerce_params_argument(arguments, tool_name)
    if coercion_error is not None:
        return _make_tool_result(coercion_error)

    # map an argument-validation failure onto the envelope.
    try:
        return await call_next(context)
    except PydanticValidationError as exc:
        try:
            validation_errors = json.loads(exc.json())
        except Exception:  # pragma: no cover - defensive
            validation_errors = [{"message": str(exc)}]
        logger.info(
            "Tool '%s' input validation failed; returning standardized envelope",
            tool_name,
        )
        envelope = _validation_error_envelope(
            message="Input validation failed.",
            tool_name=tool_name,
            validation_errors=validation_errors,
        )
        return _make_tool_result(envelope)


def build_envelope_validation_middleware() -> Any:
    """Construct a FastMCP middleware instance for the validation boundary.

    The class subclasses ``fastmcp.server.middleware.Middleware`` and is defined
    lazily inside this function so importing ``mcp_shared`` never forces the
    FastMCP middleware import chain on code paths that do not use it.
    """

    from fastmcp.server.middleware import Middleware

    class EnvelopeValidationMiddleware(Middleware):
        """Standardizes the request-validation boundary for action tools."""

        async def on_call_tool(self, context: Any, call_next: Any):
            return await _on_call_tool(context, call_next)

    return EnvelopeValidationMiddleware()


def install_envelope_middleware(server: Any) -> Any:
    """Install the envelope-validation middleware on *server* (idempotent).

    Call this once from a server factory. Safe to call more than once - a second
    install is skipped so mounting/aggregation cannot stack duplicate handlers.
    Returns the server for convenient chaining.
    """

    if getattr(server, "_nxp_envelope_mw_installed", False):
        return server
    server.add_middleware(build_envelope_validation_middleware())
    try:
        setattr(server, "_nxp_envelope_mw_installed", True)
    except Exception:  # pragma: no cover - defensive (frozen servers)
        pass
    return server
