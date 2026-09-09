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

import json
from typing import Any

from nxp.mcp.shared.action import ActionExecutionError, errors


# Debugger-specific execute_action result normalizer. This custom implementation
# is responsible for shaping component-specific execution results before they are
# returned to the agent.
#
# NOTE: the only failure signal available from a bare string result
# is a textual prefix. We keep that detection but centralize the marker list and
# emit a structured, categorized error (errorType=TOOL_EXECUTION_ERROR) via the
# shared registry so the ambiguity is at least classified consistently. A fully
# robust fix requires the backend to return a structured failure envelope.
_FAILURE_PREFIXES = ("Error:", "Failed to", "HTTPError", "URLError", "Traceback")


def normalize_s32debugger_execution_result(raw: Any) -> Any:
    if isinstance(raw, (dict, list, int, float, bool)) or raw is None:
        return raw

    if not isinstance(raw, str):
        return {"value": raw}

    prefix = "Created bridge-enabled GDB config:"
    if raw.startswith(prefix):
        return {
            "message": raw,
            "config_file": raw[len(prefix):].strip(),
        }

    text = raw.strip()
    if not text:
        return {"message": raw}

    if text.startswith(_FAILURE_PREFIXES):
        raise ActionExecutionError(
            errors.FORWARD_ERROR,
            errors.ErrorLabel.ACTION_FAILED,
            error_details={"message": raw},
            error_type=str(errors.ErrorType.TOOL_EXECUTION_ERROR),
        )

    if text[0] in "[{":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    return {"message": raw}
