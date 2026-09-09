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

"""JSON Schema validation helpers for action input parameters.

This module validates incoming action params against the derived agent-facing
``input_schema`` and converts validation failures into readable issue strings
that can be returned in standardized protocol error responses.
"""

from typing import Any

from jsonschema import Draft7Validator


def _format_error_path(error) -> str:
    """Convert a jsonschema error path into a stable ``$.field`` style string."""

    if not error.path:
        return "$"
    parts = ["$"]
    for item in error.path:
        if isinstance(item, int):
            parts.append(f"[{item}]")
        else:
            parts.append(f".{item}")
    return "".join(parts)


def validate_jsonschema(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Validate one object against one JSON Schema and return readable issues."""

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda item: list(item.path))
    return [f"{_format_error_path(error)}: {error.message}" for error in errors]

