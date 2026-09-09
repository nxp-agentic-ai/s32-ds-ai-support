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
from nxp.mcp.s32trace.handlers.action_handlers import coverage_get_source

COVERAGE_GET_SOURCE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="coverage.get_source",
        description=(
            "Return a source snippet annotated with per-line coverage state and execution time.  "
            "Identify the target by symbol name OR by file + optional line number.\n\n"
            "Each line entry includes: line number, source text, coverage state "
            "('covered' / 'not covered' / 'partially covered' / ''), execution time, and "
            "instruction count on that line.\n\n"
            "INPUTS\n"
            "- session_id:           ID returned by coverage.load.\n"
            "- symbol (optional):    Function name to anchor on.\n"
            "- file_hint (optional): Source file path or filename.\n"
            "- line (optional):      1-based line number to center the snippet on.\n"
            "- core (optional):      Restrict to a single core.\n"
            "- snippet_window (optional): Context lines above and below the target line (default from session).\n\n"
            "Provide either 'symbol' or 'file_hint', not both."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from coverage.load."},
            ),
            ActionParameter(
                name="symbol",
                required=False,
                schema={"type": "string", "description": "Function name to anchor on."},
            ),
            ActionParameter(
                name="file_hint",
                required=False,
                schema={"type": "string", "description": "Source file path or filename."},
            ),
            ActionParameter(
                name="line",
                required=False,
                schema={"type": "integer", "description": "1-based line number to center the snippet on."},
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
            ActionParameter(
                name="snippet_window",
                required=False,
                schema={"type": "integer", "description": "Context lines above and below the anchor (default from session)."},
            ),
        ),
        category="coverage",
        workflow_hints=(
            "Call coverage.load first. "
            "Use coverage.uncovered or coverage.hotspots to identify interesting symbols before calling this action.",
        ),
        related_actions=("coverage.load", "coverage.function", "coverage.uncovered", "coverage.hotspots"),
    ),
    handler=coverage_get_source,
)
