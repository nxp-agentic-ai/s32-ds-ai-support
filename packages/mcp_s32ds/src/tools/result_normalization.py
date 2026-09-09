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

"""Result normalization for S32DS ``execute_action`` output.

Preserves the historical S32DS ``execute`` behaviour: a handler that returns a
dict is passed through unchanged; any other (scalar) value is wrapped under a
``value`` key so the tool output is always a JSON object.
"""

from typing import Any


def normalize_s32ds_execution_result(raw: Any) -> Any:
    """Return dicts unchanged; wrap any other value under ``value``."""

    if isinstance(raw, dict):
        return raw
    return {"value": raw}
