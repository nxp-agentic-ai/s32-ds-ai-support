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

"""Public shared API for the action package.

This package re-exports the canonical executable-action models, loading,
search, validation, dispatch, and helpers that components reuse to implement a
consistent search-and-execute action flow.
"""

from . import errors
from .dispatch import execute_action
from .envelope import (
    StandardizingServer,
    normalize_tool_payload,
    standardize_tool_response,
    unhandled_exception_payload,
)
from .middleware import (
    build_envelope_validation_middleware,
    install_envelope_middleware,
)
from .errors import (
    CANONICAL_SCHEMA_VERSION,
    DEFAULT_SCHEMA_VERSION,
    ErrorLabel,
    ErrorType,
    Severity,
    canonical_code,
    classify_error_type,
    default_retryable,
    default_severity,
    emit_code,
    supports_canonical_codes,
)
from .models import (
    ActionCatalog,
    ActionContract,
    ActionExecutable,
    ActionExecutionError,
    ActionOutcome,
    ActionParameter,
    action_parameters_from_openrpc,
    category_from_openrpc,
)
from .search import search_actions
from .synthesis import (
    example_from_openrpc,
    make_method_handler,
    openrpc_method_to_executable_action,
    workflow_hints_from_openrpc,
)

__all__ = [
    "ActionCatalog",
    "ActionContract",
    "ActionExecutable",
    "ActionExecutionError",
    "ActionOutcome",
    "ActionParameter",
    "CANONICAL_SCHEMA_VERSION",
    "DEFAULT_SCHEMA_VERSION",
    "ErrorLabel",
    "ErrorType",
    "Severity",
    "StandardizingServer",
    "action_parameters_from_openrpc",
    "build_envelope_validation_middleware",
    "canonical_code",
    "category_from_openrpc",
    "classify_error_type",
    "default_retryable",
    "default_severity",
    "emit_code",
    "errors",
    "example_from_openrpc",
    "execute_action",
    "install_envelope_middleware",
    "make_method_handler",
    "normalize_tool_payload",
    "openrpc_method_to_executable_action",
    "search_actions",
    "standardize_tool_response",
    "supports_canonical_codes",
    "unhandled_exception_payload",
    "workflow_hints_from_openrpc",
]
