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
from nxp.mcp.s32trace.handlers.action_handlers import timeline_summary

TIMELINE_SUMMARY_ACTION = ActionExecutable(
    contract=ActionContract(
        name="timeline.summary",
        description=(
            "Return an overview of a loaded timeline session: total sample count, "
            "timestamp range, and the top-k functions by sample count.\n\n"
            "INPUTS\n"
            "- session_id: Session handle from timeline.load.\n"
            "- source_name (optional): Filter to a specific trace source / core name.\n"
            "- top_k (optional): Number of top functions to return (default 10).\n\n"
            "RETURNS\n"
            "{\n"
            "  'sources': ['A53 0'],\n"
            "  'function_count': 87,\n"
            "  'total_samples': 45321,\n"
            "  'timestamp_range': [0, 3007744],\n"
            "  'top_functions_by_samples': [{name, total_samples, pct, ...}, ...]\n"
            "}"
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session handle from timeline.load."},
            ),
            ActionParameter(
                name="source_name",
                required=False,
                schema={"type": "string", "description": "Filter to a specific trace source (core) name."},
            ),
            ActionParameter(
                name="top_k",
                required=False,
                schema={"type": "integer", "description": "Number of top functions to return (default 10)."},
            ),
        ),
        category="timeline",
        workflow_hints=("Call after timeline.load. Use as the default first query after loading.",),
        related_actions=("timeline.load", "timeline.hotspots", "timeline.function"),
    ),
    handler=timeline_summary,
)
