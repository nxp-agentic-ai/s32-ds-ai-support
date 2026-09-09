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
from nxp.mcp.s32trace.handlers.action_handlers import coverage_hotspots

COVERAGE_HOTSPOTS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="coverage.hotspots",
        description=(
            "Return the most-executed functions or source lines, ranked by execution time or "
            "instruction count.  Use this to find where the CPU spends most of its time.\n\n"
            "INPUTS\n"
            "- session_id:             ID returned by coverage.load.\n"
            "- sort_by (optional):     'time' (default) or 'total_asm' or 'size' for function granularity; "
            "'time' or 'asm_count' for line granularity.\n"
            "- granularity (optional): 'function' (default) or 'line'.\n"
            "- top_k (optional):       Max items to return (default 10).\n"
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
                name="sort_by",
                required=False,
                schema={"type": "string", "description": "Sort key (default 'time')."},
            ),
            ActionParameter(
                name="granularity",
                required=False,
                schema={
                    "type": "string",
                    "enum": ["function", "line"],
                    "description": "Granularity level (default 'function').",
                },
            ),
            ActionParameter(
                name="top_k",
                required=False,
                schema={"type": "integer", "description": "Max items to return (default 10)."},
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
        workflow_hints=("Call coverage.load first. Use coverage.get_source to view the hottest lines in context.",),
        related_actions=("coverage.load", "coverage.summary", "coverage.get_source"),
    ),
    handler=coverage_hotspots,
)
