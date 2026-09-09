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

from typing import Any


__all__ = ["normalize_s32flashtool_execution_result"]


# S32FlashTool-specific execute_action result normalizer. This custom implementation
# is responsible for shaping component-specific execution results before they are
# returned to the agent. S32FlashTool handlers already return structured payloads
# (dict/list/scalars), so JSON-compatible values pass through unchanged; any other
# object is wrapped in a stable envelope.
def normalize_s32flashtool_execution_result(raw: Any) -> Any:
    if isinstance(raw, (dict, list, int, float, bool, str)) or raw is None:
        return raw
    return {"value": raw}


