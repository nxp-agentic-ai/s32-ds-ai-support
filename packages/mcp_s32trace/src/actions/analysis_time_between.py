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
from nxp.mcp.s32trace.handlers.action_handlers import analysis_time_between

ANALYSIS_TIME_BETWEEN_ACTION = ActionExecutable(
    contract=ActionContract(
        name="analysis.time_between",
        description=(
            "Measure the time delta between two matched trace events.  Both 'from' and 'to' "
            "are selector dicts (same schema as analysis.find_event selector).\n\n"
            "Returns the delta in raw units and (when time_unit_ns is set) nanoseconds, plus "
            "a compact summary of intermediate symbols so the AI can explain why the gap is "
            "large.\n\n"
            "occurrence values:\n"
            "  'first' (default) - use the first match for each selector.\n"
            "  'last'            - use the last match for each selector.\n"
            "  'all'             - return every consecutive from->to pair.\n\n"
            "USE CASES\n"
            "- 'How long between TaskStart and TaskEnd?' -> "
            "from={symbol:'TaskStart'}, to={symbol:'TaskEnd'}\n"
            "- 'How long from main.c:42 to main.c:80?'  -> "
            "from={file:'main.c', line:42}, to={file:'main.c', line:80}\n"
            "- 'How many times did foo->bar happen and how long each time?' -> occurrence='all'"
        ),
        params=(
            ActionParameter(
                name="trace_id",
                required=True,
                schema={"type": "string", "description": "Session handle from analysis.load_trace."},
            ),
            ActionParameter(
                name="from_selector",
                required=True,
                schema={
                    "type": "object",
                    "description": "Selector for the start event (same schema as analysis.find_event selector).",
                },
            ),
            ActionParameter(
                name="to_selector",
                required=True,
                schema={
                    "type": "object",
                    "description": "Selector for the end event.",
                },
            ),
            ActionParameter(
                name="occurrence",
                required=False,
                schema={
                    "type": "string",
                    "enum": ["first", "last", "all"],
                    "description": "Which occurrences to measure (default 'first').",
                },
            ),
            ActionParameter(
                name="max_intermediate_symbols",
                required=False,
                schema={
                    "type": "integer",
                    "description": "Top-N intermediate symbols to return (default 10).",
                },
            ),
        ),
        category="analysis",
        workflow_hints=(
            "Use occurrence='all' to detect variance across multiple invocations. "
            "Check top_intermediate_symbols to understand what runs in the measured interval.",
        ),
        related_actions=(
            "analysis.load_trace",
            "analysis.find_event",
            "analysis.range_events",
        ),
    ),
    handler=analysis_time_between,
)
