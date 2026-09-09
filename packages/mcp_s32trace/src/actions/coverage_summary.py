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
from nxp.mcp.s32trace.handlers.action_handlers import coverage_summary

COVERAGE_SUMMARY_ACTION = ActionExecutable(
    contract=ActionContract(
        name="coverage.summary",
        description=(
            "Return overall coverage statistics for a loaded session: overall ASM and source-line "
            "coverage percentages, function counts by coverage state, and the top-K hotspots by "
            "execution time and the top-K uncovered functions by code size.\n\n"
            "The '_No source info' bucket (libc / runtime / startup code with no DWARF file) is "
            "excluded from all aggregates by default.  Set include_no_source_info=true to include it.\n\n"
            "INPUTS\n"
            "- session_id:             ID returned by coverage.load.\n"
            "- core (optional):        Restrict to a single core (e.g. 'A53_0'). Omit to aggregate all cores.\n"
            "- top_k (optional):       How many entries to return in the ranked lists (default 10).\n"
            "- include_no_source_info: Include libc/runtime functions with no source info (default false).\n\n"
            "RETURNS\n"
            "Overall coverage percentages, per-state function counts, top_by_time list, "
            "top_uncovered_by_size list."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from coverage.load."},
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
            ActionParameter(
                name="top_k",
                required=False,
                schema={"type": "integer", "description": "Entries per ranked list (default 10)."},
            ),
            ActionParameter(
                name="include_no_source_info",
                required=False,
                schema={"type": "boolean", "description": "Include libc/runtime symbols (default false)."},
            ),
        ),
        category="coverage",
        workflow_hints=("Call coverage.load first to obtain a session_id.",),
        related_actions=("coverage.load", "coverage.uncovered", "coverage.hotspots"),
    ),
    handler=coverage_summary,
)
