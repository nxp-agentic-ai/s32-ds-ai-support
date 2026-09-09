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

"""Additive response-envelope normalization for non-action MCP tools.

Components built on the shared action mechanism already return the standardized
envelope via ``ActionOutcome.to_response()``. Some components predate that
mechanism and return component-local payload shapes instead.

This module standardizes those components **without changing their existing
keys**. ``normalize_tool_payload`` wraps a payload so that:

* every response gains a top-level ``success`` boolean, so an agent has one
  uniform way to detect failure across the entire MCP;
* failures additionally gain a standardized ``error`` object carrying
  ``code`` / ``message`` / ``errorType`` / ``severity`` / ``retryable``,
  matching the shape produced by ``ActionOutcome.to_response()``;
* all pre-existing keys are preserved verbatim at the top level, so documented
  consumers (skills, tests, agents reading ``exit_code`` / ``summary``) keep
  working unchanged.

Failure detection is deliberately conservative and driven by the conventions
actually used in this repository (see ``_looks_like_failure``). Anything not
recognized as a failure is reported as a success.
"""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable

from . import errors

# Keys that already indicate the standardized envelope is present.
_ENVELOPE_KEYS = ("success", "error")


def _looks_like_failure(payload: dict[str, Any]) -> tuple[bool, str | None]:
    """Detect a component-local failure convention in *payload*.

    Returns ``(is_failure, reason)`` where ``reason`` is a short human-readable
    explanation used to populate the error message details.
    """

    # A bare error string is the most specific diagnostic available, so it is
    # checked first: when a payload carries both `ok: false` and `error: "..."`,
    # the actual message must win over the generic flag.
    raw_error = payload.get("error")
    specific_reason = str(raw_error) if raw_error and not isinstance(raw_error, dict) else None

    exit_code = payload.get("exit_code")
    if isinstance(exit_code, int) and not isinstance(exit_code, bool) and exit_code != 0:
        return True, specific_reason or f"Tool reported a non-zero exit_code ({exit_code})."

    if payload.get("ok") is False:
        return True, specific_reason or "Tool reported ok=false."

    status = payload.get("status")
    if isinstance(status, str) and status.strip().lower() == "error":
        return True, specific_reason or "Tool reported status='error'."

    if specific_reason is not None:
        return True, specific_reason

    return False, None


def _error_block(
    *,
    reason: str,
    payload: dict[str, Any],
    tool_name: str | None,
    code: int,
    label: str,
    error_type: errors.ErrorType,
) -> dict[str, Any]:
    """Build the standardized error object for a normalized failure."""

    details: dict[str, Any] = {"message": reason}
    # Carry the component's own diagnostics so no context is lost.
    for key in ("summary", "exit_code", "command", "stderr_tail", "kind"):
        if key in payload and payload[key] not in (None, ""):
            details[key] = payload[key]
    if tool_name:
        details["tool"] = tool_name

    return {
        "code": code,
        "message": str(label),
        "errorType": str(error_type),
        "severity": str(errors.default_severity(error_type)),
        "retryable": errors.default_retryable(error_type),
        "details": details,
    }


def normalize_tool_payload(result: Any, *, tool_name: str | None = None) -> Any:
    """Return *result* augmented with the standardized envelope fields.

    Behavior:

    * A payload that already carries ``success`` (or a dict-shaped ``error``)
      is returned unchanged - components on the action mechanism are untouched.
    * A dict payload gains ``success`` and, on failure, a standardized
      ``error`` object. All original keys are preserved.
    * A non-dict payload (string, list, ...) is wrapped as
      ``{"success": True, "result": <value>}`` so the envelope is uniform.
    """

    if isinstance(result, dict):
        if any(key in result for key in _ENVELOPE_KEYS) and (
            "success" in result or isinstance(result.get("error"), dict)
        ):
            return result

        is_failure, reason = _looks_like_failure(result)
        normalized = dict(result)
        if not is_failure:
            normalized["success"] = True
            return normalized

        normalized["success"] = False
        normalized["error"] = _error_block(
            reason=reason or "Tool reported a failure.",
            payload=result,
            tool_name=tool_name,
            code=errors.EXECUTION_FAILED,
            label=errors.ErrorLabel.EXECUTION_FAILED,
            error_type=errors.ErrorType.TOOL_EXECUTION_ERROR,
        )
        return normalized

    # Non-dict payloads cannot carry an envelope; wrap them.
    return {"success": True, "result": result}


def unhandled_exception_payload(exc: BaseException, *, tool_name: str | None = None) -> dict[str, Any]:
    """Build a standardized failure envelope for an unhandled exception."""

    error_type = errors.ErrorType.INTERNAL_ERROR
    details: dict[str, Any] = {"message": str(exc), "exception": type(exc).__name__}
    if tool_name:
        details["tool"] = tool_name
    return {
        "success": False,
        "error": {
            "code": errors.INTERNAL_ERROR,
            "message": str(errors.ErrorLabel.INTERNAL_ERROR),
            "errorType": str(error_type),
            "severity": str(errors.default_severity(error_type)),
            "retryable": errors.default_retryable(error_type),
            "details": details,
        },
        "result": None
    }


def standardize_tool_response(
    func: Callable[..., Any] | None = None,
    *,
    tool_name: str | None = None,
    component_logger: logging.Logger | None = None,
) -> Callable[..., Any]:
    """Decorate an MCP tool so its response carries the standardized envelope.

    Works for both sync and async tools. Any exception escaping the tool is
    converted into a standardized failure envelope instead of propagating as an
    opaque protocol error, which is what closes the "a tool failed but the agent
    cannot tell why" gap for components that do not use the action dispatcher.

    ``functools.wraps`` is used so the MCP framework still sees the original
    name, docstring, and signature when deriving the tool schema.
    """

    def _decorate(inner: Callable[..., Any]) -> Callable[..., Any]:
        resolved_name = tool_name or getattr(inner, "__name__", None)
        logger = component_logger or logging.getLogger(__name__)

        if inspect.iscoroutinefunction(inner):

            @functools.wraps(inner)
            async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    result = await inner(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception("Unhandled error in tool '%s'", resolved_name)
                    return unhandled_exception_payload(exc, tool_name=resolved_name)
                return normalize_tool_payload(result, tool_name=resolved_name)

            return _async_wrapper

        @functools.wraps(inner)
        def _sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = inner(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Unhandled error in tool '%s'", resolved_name)
                return unhandled_exception_payload(exc, tool_name=resolved_name)
            return normalize_tool_payload(result, tool_name=resolved_name)

        return _sync_wrapper

    if func is not None:
        return _decorate(func)
    return _decorate


class StandardizingServer:
    """Proxy around an MCP server that standardizes every registered tool.

    Components that predate the shared action dispatcher register their tools
    with plain ``@server.tool(...)`` decorators and return component-local
    payloads. Wrapping the server in this proxy makes every tool registered
    through it pass its response through :func:`standardize_tool_response`,
    so the whole component becomes envelope-conformant without editing any
    individual tool body.

    Usage inside a component's ``register_tools``::

        standardized = StandardizingServer(server, component_logger=logger)
        register_my_tools(standardized, config)

    Only ``tool`` is intercepted. Every other attribute (``resource``,
    ``prompt``, ``mount``, ...) is delegated unchanged to the wrapped server, so
    resources and prompts keep their existing behavior.
    """

    def __init__(self, server: Any, *, component_logger: logging.Logger | None = None) -> None:
        self._server = server
        self._logger = component_logger

    def __getattr__(self, name: str) -> Any:
        # Delegate everything we do not explicitly override.
        return getattr(self._server, name)

    def tool(self, *decorator_args: Any, **decorator_kwargs: Any):
        """Return a decorator that registers a response-standardized tool."""

        inner_decorator = self._server.tool(*decorator_args, **decorator_kwargs)

        def _register(func: Callable[..., Any]):
            wrapped = standardize_tool_response(
                func,
                tool_name=decorator_kwargs.get("name") or getattr(func, "__name__", None),
                component_logger=self._logger,
            )
            return inner_decorator(wrapped)

        return _register


