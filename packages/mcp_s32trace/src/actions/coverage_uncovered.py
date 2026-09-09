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
from nxp.mcp.s32trace.handlers.action_handlers import coverage_uncovered

COVERAGE_UNCOVERED_ACTION = ActionExecutable(
    contract=ActionContract(
        name="coverage.uncovered",
        description=(
            "List uncovered code items, sorted by size or line number.  Three granularity levels:\n"
            "  - 'function': functions with 0%% ASM coverage (sorted by binary size).\n"
            "  - 'line':     individual source lines marked 'not covered'.\n"
            "  - 'asm':      individual assembly instructions marked 'not covered'.\n\n"
            "The '_No source info' bucket is excluded by default.\n\n"
            "INPUTS\n"
            "- session_id:             ID returned by coverage.load.\n"
            "- granularity (optional): 'function' (default), 'line', or 'asm'.\n"
            "- sort_by (optional):     'size' (default for function) or 'total_src_lines'.\n"
            "- top_k (optional):       Maximum items to return (default 20).\n"
            "- core (optional):        Restrict to a single core.\n"
            "- include_no_source_info: Include libc/runtime symbols (default false)."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from coverage.load."},
            ),
            ActionParameter(
                name="granularity",
                required=False,
                schema={
                    "type": "string",
                    "enum": ["function", "line", "asm"],
                    "description": "Granularity level (default 'function').",
                },
            ),
            ActionParameter(
                name="sort_by",
                required=False,
                schema={"type": "string", "description": "Sort key: 'size' or 'total_src_lines' (default 'size')."},
            ),
            ActionParameter(
                name="top_k",
                required=False,
                schema={"type": "integer", "description": "Max items to return (default 20)."},
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
            ActionParameter(
                name="include_no_source_info",
                required=False,
                schema={"type": "boolean", "description": "Include libc/runtime symbols (default false)."},
            ),
        ),
        category="coverage",
        workflow_hints=("Call coverage.load first. Use coverage.function or coverage.get_source to drill into a result.",),
        related_actions=("coverage.load", "coverage.function", "coverage.get_source"),
    ),
    handler=coverage_uncovered,
)
