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
from nxp.mcp.s32trace.handlers.action_handlers import coverage_function

COVERAGE_FUNCTION_ACTION = ActionExecutable(
    contract=ActionContract(
        name="coverage.function",
        description=(
            "Return coverage metrics for a specific function (symbol name).  Because inline "
            "functions may appear at multiple addresses, all instances are returned.\n\n"
            "Each instance includes: address, covered/not-covered/partial percentages for ASM "
            "and source lines, execution time, and - when source detail is available - a "
            "per-source-line breakdown showing line number, file, coverage state, hit count, "
            "and execution time.\n\n"
            "INPUTS\n"
            "- session_id:          ID returned by coverage.load.\n"
            "- name:                Exact function name (e.g. 'slow_mid1', 'crc16_step_0x33d843b0').\n"
            "- core (optional):     Restrict to a single core.\n"
            "- include_source_rows: Include per-source-line detail (default true)."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from coverage.load."},
            ),
            ActionParameter(
                name="name",
                required=True,
                schema={"type": "string", "description": "Exact function/symbol name."},
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
            ActionParameter(
                name="include_source_rows",
                required=False,
                schema={"type": "boolean", "description": "Include per-source-line detail (default true)."},
            ),
        ),
        category="coverage",
        workflow_hints=("Call coverage.load first. Use coverage.uncovered to discover function names.",),
        related_actions=("coverage.load", "coverage.uncovered", "coverage.get_source"),
    ),
    handler=coverage_function,
)
