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
from nxp.mcp.s32trace.handlers.action_handlers import analysis_summary

ANALYSIS_SUMMARY_ACTION = ActionExecutable(
    contract=ActionContract(
        name="analysis.summary",
        description=(
            "Return coarse statistics for a loaded trace session: total duration, per-core "
            "event counts, top-N hottest functions by event count and by instruction count, "
            "and a list of DWARF source paths that could not be resolved locally.\n\n"
            "Use this action first after analysis.load_trace to get an overview before "
            "diving into specific queries.\n\n"
            "RETURNS\n"
            "{\n"
            "  'parent_event_count': 12345,\n"
            "  'cores': ['R52_0_0'],\n"
            "  'duration_raw': 9876543,\n"
            "  'duration_ns': 9876543.0,  // null when time_unit_ns not set\n"
            "  'top_functions_by_events': [{'symbol': 'foo', 'event_count': 500}, ...],\n"
            "  'top_functions_by_instructions': [{'symbol': 'foo', 'instruction_count': 4000}, ...],\n"
            "  'unresolved_source_files': [...]  // empty when source_root covers all paths\n"
            "}"
        ),
        params=(
            ActionParameter(
                name="trace_id",
                required=True,
                schema={"type": "string", "description": "Session handle returned by analysis.load_trace."},
            ),
            ActionParameter(
                name="top_n",
                required=False,
                schema={"type": "integer", "description": "How many top functions to return (default 10)."},
            ),
        ),
        category="analysis",
        workflow_hints=(
            "Call after analysis.load_trace.  Use the hot-function list to guide "
            "follow-up analysis.find_event or analysis.get_source queries.",
        ),
        related_actions=(
            "analysis.load_trace",
            "analysis.find_event",
            "analysis.get_source",
        ),
    ),
    handler=analysis_summary,
)
