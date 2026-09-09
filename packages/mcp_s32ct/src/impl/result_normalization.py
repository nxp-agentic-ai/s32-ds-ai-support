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

"""S32CT-specific ``execute_action`` result normalizer.

The shared dispatcher treats normalization as opt-in and keeps all
business-specific output shaping in the component. S32CT handlers return a mix
of shapes inherited from the pre-action tool surface:

* ``dict``  - the ``cli_impl`` contract
  (``{exit_code, command, stdout_tail, stderr_tail, values, summary}``) and the
  inspect / validate / sanitize payloads;
* ``list``  - ``gtm_list_usecases`` returns a bare list of use-case names;
* ``str``   - ``generate_code_impl`` / ``gtm_create_from_usecase_impl`` /
  ``get_version_impl`` return a human-readable summary line.

JSON-compatible values pass through untouched so the documented S32CT payload
keys stay byte-identical to the pre-refactor contract. ``Path`` objects are
stringified because the launcher helpers occasionally hand one back, and any
other object is wrapped in a stable envelope rather than being allowed to fail
JSON serialization inside the transport layer.
"""

from pathlib import Path
from typing import Any


def normalize_s32ct_execution_result(raw: Any) -> Any:
    """Shape one S32CT handler result into a JSON-safe payload."""

    if raw is None or isinstance(raw, (dict, list, int, float, bool, str)):
        return raw
    if isinstance(raw, Path):
        return str(raw)
    if isinstance(raw, tuple):
        return list(raw)
    return {"value": str(raw)}
