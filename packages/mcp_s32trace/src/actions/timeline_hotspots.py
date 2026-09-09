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
from nxp.mcp.s32trace.handlers.action_handlers import timeline_hotspots

TIMELINE_HOTSPOTS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="timeline.hotspots",
        description=(
            "Return the top-k hottest functions from a timeline session, "
            "ranked by sample count or accumulated timestamp value.\n\n"
            "INPUTS\n"
            "- session_id: Session handle from timeline.load.\n"
            "- sort_by (optional): 'samples' (default) or 'time'.\n"
            "- top_k (optional): Number of results (default 10).\n"
            "- source_name (optional): Restrict to one trace source / core.\n\n"
            "RETURNS\n"
            "{\n"
            "  'sort_by': 'samples',\n"
            "  'total_samples': 45321,\n"
            "  'hotspots': [{name, total_samples, total_time, pct, size}, ...]\n"
            "}"
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session handle from timeline.load."},
            ),
            ActionParameter(
                name="sort_by",
                required=False,
                schema={
                    "type": "string",
                    "enum": ["samples", "time"],
                    "description": "Ranking criterion: 'samples' (default) or 'time'.",
                },
            ),
            ActionParameter(
                name="top_k",
                required=False,
                schema={"type": "integer", "description": "Number of hotspot functions to return (default 10)."},
            ),
            ActionParameter(
                name="source_name",
                required=False,
                schema={"type": "string", "description": "Restrict to one trace source (core) name."},
            ),
        ),
        category="timeline",
        workflow_hints=("Use to identify performance bottlenecks after timeline.load.",),
        related_actions=("timeline.load", "timeline.summary", "timeline.function"),
    ),
    handler=timeline_hotspots,
)
