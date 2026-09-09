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

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter
from nxp.mcp.s32trace.handlers.action_handlers import coverage_file

COVERAGE_FILE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="coverage.file",
        description=(
            "Return coverage metrics for a specific source file.  Accepts either a full absolute "
            "path or just a filename (e.g. 'slow_path.c').\n\n"
            "Returns: file-level ASM and source coverage percentages, list of fully uncovered "
            "functions inside the file, and covered/uncovered line counts derived from the "
            "detailed source-row data.\n\n"
            "INPUTS\n"
            "- session_id:       ID returned by coverage.load.\n"
            "- file_hint:        Full path or filename of the source file.\n"
            "- core (optional):  Restrict to a single core."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from coverage.load."},
            ),
            ActionParameter(
                name="file_hint",
                required=True,
                schema={"type": "string", "description": "Full path or filename of the source file."},
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
        ),
        category="coverage",
        workflow_hints=("Call coverage.load first. Combine with coverage.get_source to inspect uncovered lines.",),
        related_actions=("coverage.load", "coverage.get_source", "coverage.uncovered"),
    ),
    handler=coverage_file,
)
