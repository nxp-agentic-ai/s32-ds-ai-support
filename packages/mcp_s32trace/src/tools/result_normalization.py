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


# S32Trace-specific execute_action result normalizer.
# Handlers already return dicts or raise ActionExecutionError for failures,
# so this normalizer only needs to wrap unexpected raw scalar/string values.
def normalize_s32trace_execution_result(raw: Any) -> Any:
    if isinstance(raw, (dict, list, int, float, bool)) or raw is None:
        return raw

    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {"message": raw}
        return {"message": raw}

    return {"value": raw}
