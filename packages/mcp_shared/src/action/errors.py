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

"""Unified error-code registry and error taxonomy for the shared action layer.

This module is the single source of truth for the numeric error codes, the
stable textual error-message labels, the coarse machine-readable error
categories (``errorType``), retryability defaults, severity defaults, and the
optional schema-version-gated canonical code remap described in the MCP schema
RFC.
"""

from __future__ import annotations

from enum import StrEnum

# ---------------------------------------------------------------------------
# Schema versioning
# ---------------------------------------------------------------------------

# The default (legacy) envelope schema version. With this version the emitted
# numeric codes are the historical ones, so nothing changes for existing
# clients. Callers negotiate CANONICAL_SCHEMA_VERSION to opt into the
# de-overloaded numeric code space.
DEFAULT_SCHEMA_VERSION = "1.0"
CANONICAL_SCHEMA_VERSION = "2.0"


def supports_canonical_codes(schema_version: str | None) -> bool:
    """Return True when *schema_version* opts into the canonical code remap.

    The rule is intentionally simple: any major version >= 2 gets the
    de-overloaded codes. Malformed or missing versions fall back to legacy.
    """

    if not schema_version:
        return False
    head = schema_version.strip().split(".", 1)[0]
    try:
        return int(head) >= 2
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Legacy numeric error codes (historical values, preserved verbatim)
# ---------------------------------------------------------------------------

# JSON-RPC 2.0 standard codes. Never redefine these.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# MCP application-level codes historically minted in the JSON-RPC reserved
# server range (-32099..-32000). These are the values in use today.
UNKNOWN_ACTION = -32001
FORWARD_ERROR = -32002
RESULT_NORMALIZATION_FAILED = -32003
ACTION_TIMEOUT = -32004
EXECUTION_FAILED = -32000
CONFIRMATION_REQUIRED = -32010


# ---------------------------------------------------------------------------
# Stable textual error-message labels
# ---------------------------------------------------------------------------

class ErrorLabel(StrEnum):
    """Stable, machine-oriented textual labels emitted as ``error.message``."""

    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    INVALID_PARAMS = "INVALID_PARAMS"
    INVALID_SEARCH_STRATEGY = "INVALID_SEARCH_STRATEGY"
    SEARCH_FAILED = "SEARCH_FAILED"
    IDE_CALL_FAILED = "IDE_CALL_FAILED"
    IDE_UNREACHABLE = "IDE_UNREACHABLE"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    BRIDGE_REQUEST_FAILED = "BRIDGE_REQUEST_FAILED"
    ACTION_FAILED = "ACTION_FAILED"
    HANDLER_ERROR = "HANDLER_ERROR"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    RESULT_NORMALIZATION_FAILED = "RESULT_NORMALIZATION_FAILED"
    ACTION_TIMEOUT = "ACTION_TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# Error categories (coarse, machine-readable, used for routing / retry)
# ---------------------------------------------------------------------------

class ErrorType(StrEnum):
    """Coarse machine-readable error category (``errorType``)."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    PRECONDITION_ERROR = "PRECONDITION_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class Severity(StrEnum):
    """Operational severity of a failure (``severity``)."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


# ---------------------------------------------------------------------------
# Classification tables
# ---------------------------------------------------------------------------

# Primary classification is by the stable message label, because a single
# numeric code (notably -32002) is overloaded across several distinct labels.
_ERROR_TYPE_BY_LABEL: dict[str, ErrorType] = {
    ErrorLabel.UNKNOWN_ACTION: ErrorType.NOT_FOUND_ERROR,
    ErrorLabel.INVALID_PARAMS: ErrorType.VALIDATION_ERROR,
    ErrorLabel.INVALID_SEARCH_STRATEGY: ErrorType.VALIDATION_ERROR,
    ErrorLabel.SEARCH_FAILED: ErrorType.INTERNAL_ERROR,
    ErrorLabel.IDE_CALL_FAILED: ErrorType.TOOL_EXECUTION_ERROR,
    ErrorLabel.IDE_UNREACHABLE: ErrorType.DEPENDENCY_ERROR,
    ErrorLabel.PRECONDITION_FAILED: ErrorType.PRECONDITION_ERROR,
    ErrorLabel.MISSING_CONTEXT: ErrorType.PRECONDITION_ERROR,
    ErrorLabel.BRIDGE_REQUEST_FAILED: ErrorType.DEPENDENCY_ERROR,
    ErrorLabel.ACTION_FAILED: ErrorType.TOOL_EXECUTION_ERROR,
    ErrorLabel.HANDLER_ERROR: ErrorType.TOOL_EXECUTION_ERROR,
    ErrorLabel.EXECUTION_FAILED: ErrorType.TOOL_EXECUTION_ERROR,
    ErrorLabel.CONFIRMATION_REQUIRED: ErrorType.CONFIRMATION_REQUIRED,
    ErrorLabel.RESULT_NORMALIZATION_FAILED: ErrorType.INTERNAL_ERROR,
    ErrorLabel.ACTION_TIMEOUT: ErrorType.TIMEOUT_ERROR,
    ErrorLabel.INTERNAL_ERROR: ErrorType.INTERNAL_ERROR,
}

# Fallback classification by numeric code when the label is unknown/custom.
_ERROR_TYPE_BY_CODE: dict[int, ErrorType] = {
    PARSE_ERROR: ErrorType.VALIDATION_ERROR,
    INVALID_REQUEST: ErrorType.VALIDATION_ERROR,
    METHOD_NOT_FOUND: ErrorType.NOT_FOUND_ERROR,
    INVALID_PARAMS: ErrorType.VALIDATION_ERROR,
    INTERNAL_ERROR: ErrorType.INTERNAL_ERROR,
    UNKNOWN_ACTION: ErrorType.NOT_FOUND_ERROR,
    RESULT_NORMALIZATION_FAILED: ErrorType.INTERNAL_ERROR,
    ACTION_TIMEOUT: ErrorType.TIMEOUT_ERROR,
    CONFIRMATION_REQUIRED: ErrorType.CONFIRMATION_REQUIRED,
    EXECUTION_FAILED: ErrorType.TOOL_EXECUTION_ERROR,
    FORWARD_ERROR: ErrorType.TOOL_EXECUTION_ERROR,
}

# Error categories for which an identical retry may succeed.
_RETRYABLE_TYPES: frozenset[ErrorType] = frozenset(
    {
        ErrorType.TIMEOUT_ERROR,
        ErrorType.DEPENDENCY_ERROR,
        ErrorType.RATE_LIMIT_ERROR,
    }
)

# Canonical (de-overloaded) numeric codes keyed by message label. Only applied
# when the caller negotiates CANONICAL_SCHEMA_VERSION. Labels absent from this
# table keep their legacy numeric code. Ranges:
#   protocol   -32700, -32600..-32603 (unchanged)
#   transport  -31099..-31000
#   application-32099..-32000 reserved for MCP; app codes -30099..-30000
#   tool       -29999..-29000
_CANONICAL_CODE_BY_LABEL: dict[str, int] = {
    ErrorLabel.UNKNOWN_ACTION: -30001,
    ErrorLabel.RESULT_NORMALIZATION_FAILED: -30003,
    ErrorLabel.ACTION_TIMEOUT: -30004,
    ErrorLabel.INVALID_SEARCH_STRATEGY: -30010,
    ErrorLabel.SEARCH_FAILED: -30011,
    ErrorLabel.IDE_CALL_FAILED: -29001,
    ErrorLabel.IDE_UNREACHABLE: -31001,
    ErrorLabel.PRECONDITION_FAILED: -29002,
    ErrorLabel.MISSING_CONTEXT: -29003,
    ErrorLabel.BRIDGE_REQUEST_FAILED: -29004,
    ErrorLabel.ACTION_FAILED: -29005,
    ErrorLabel.HANDLER_ERROR: -29006,
    ErrorLabel.EXECUTION_FAILED: -29007,
    ErrorLabel.CONFIRMATION_REQUIRED: -29010,
    # INVALID_PARAMS and INTERNAL_ERROR intentionally keep their JSON-RPC codes.
}


# ---------------------------------------------------------------------------
# Public classification helpers
# ---------------------------------------------------------------------------

def classify_error_type(code: int | None, message: str | None) -> ErrorType:
    """Return the coarse ``errorType`` for a (code, message) pair.

    Classification is label-first (to disambiguate overloaded codes), then
    code-based, then a conservative INTERNAL_ERROR fallback.
    """

    if message:
        by_label = _ERROR_TYPE_BY_LABEL.get(message)
        if by_label is not None:
            return by_label
    if code is not None:
        by_code = _ERROR_TYPE_BY_CODE.get(code)
        if by_code is not None:
            return by_code
    return ErrorType.INTERNAL_ERROR


def default_retryable(error_type: ErrorType) -> bool:
    """Return the conservative default retryability for an ``errorType``."""

    return error_type in _RETRYABLE_TYPES


def default_severity(error_type: ErrorType) -> Severity:
    """Return the default severity for an ``errorType``."""

    if error_type is ErrorType.INTERNAL_ERROR:
        return Severity.FATAL
    if error_type is ErrorType.CONFIRMATION_REQUIRED:
        return Severity.WARNING
    return Severity.ERROR


def canonical_code(code: int | None, message: str | None) -> int | None:
    """Return the de-overloaded numeric code for a (code, message) pair.

    Applied only when the caller has negotiated the canonical schema version.
    Labels without a canonical mapping keep their legacy code.
    """

    if message and message in _CANONICAL_CODE_BY_LABEL:
        return _CANONICAL_CODE_BY_LABEL[message]
    return code


def emit_code(code: int | None, message: str | None, *, schema_version: str | None) -> int | None:
    """Return the numeric code to emit for the negotiated *schema_version*."""

    if supports_canonical_codes(schema_version):
        return canonical_code(code, message)
    return code
