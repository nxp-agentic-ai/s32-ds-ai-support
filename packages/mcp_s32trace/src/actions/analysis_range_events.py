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
from nxp.mcp.s32trace.handlers.action_handlers import analysis_range_events

ANALYSIS_RANGE_EVENTS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="analysis.range_events",
        description=(
            "Return a rolled-up breakdown of all events inside a time window.  Accepts either "
            "an explicit [t_start, t_end] pair or two event selectors that act as boundaries.\n\n"
            "Returns per-symbol counts, per-file counts, and per-event-type counts.  "
            "Set include_raw_rows=true to also receive the individual event rows.\n\n"
            "USE CASES\n"
            "- 'What functions ran between timestamps 100 and 5000?'\n"
            "- 'Show me all events between ISR_Enter and ISR_Exit'\n"
            "- 'Which file dominates the ISR?' -> read top_files from the response"
        ),
        params=(
            ActionParameter(
                name="trace_id",
                required=True,
                schema={"type": "string", "description": "Session handle from analysis.load_trace."},
            ),
            ActionParameter(
                name="time_range",
                required=False,
                schema={
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[t_start, t_end] in raw timestamp units.",
                },
            ),
            ActionParameter(
                name="from_selector",
                required=False,
                schema={
                    "type": "object",
                    "description": "Start-boundary event selector (alternative to time_range).",
                },
            ),
            ActionParameter(
                name="to_selector",
                required=False,
                schema={
                    "type": "object",
                    "description": "End-boundary event selector (alternative to time_range).",
                },
            ),
            ActionParameter(
                name="include_raw_rows",
                required=False,
                schema={
                    "type": "boolean",
                    "description": "Include individual event rows (default false).",
                },
            ),
            ActionParameter(
                name="limit",
                required=False,
                schema={
                    "type": "integer",
                    "description": "Max raw rows to return when include_raw_rows=true (default 100).",
                },
            ),
        ),
        category="analysis",
        workflow_hints=(
            "Use after analysis.time_between to drill into what ran in a specific interval. "
            "top_symbols and top_files are the primary outputs for AI reasoning.",
        ),
        related_actions=(
            "analysis.load_trace",
            "analysis.time_between",
            "analysis.find_event",
        ),
    ),
    handler=analysis_range_events,
)
