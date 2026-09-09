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
from nxp.mcp.s32trace.handlers.action_handlers import timeline_window

TIMELINE_WINDOW_ACTION = ActionExecutable(
    contract=ActionContract(
        name="timeline.window",
        description=(
            "Return function-level sample aggregates within a tick time window.  "
            "Use the timestamp_range from timeline.summary to pick start/end values.\n\n"
            "INPUTS\n"
            "- session_id: Session handle from timeline.load.\n"
            "- start_tick (optional): Inclusive lower bound (raw tick counter).\n"
            "- end_tick (optional): Inclusive upper bound (raw tick counter).\n"
            "- source_name (optional): Restrict to one trace source / core.\n"
            "- top_k (optional): Number of functions to return (default 20).\n\n"
            "RETURNS\n"
            "{\n"
            "  'start_tick': 1000,\n"
            "  'end_tick': 50000,\n"
            "  'total_samples_in_window': 3217,\n"
            "  'functions': [{name, total_samples, pct}, ...]\n"
            "}"
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session handle from timeline.load."},
            ),
            ActionParameter(
                name="start_tick",
                required=False,
                schema={"type": "integer", "description": "Start tick (inclusive). Omit for beginning of trace."},
            ),
            ActionParameter(
                name="end_tick",
                required=False,
                schema={"type": "integer", "description": "End tick (inclusive). Omit for end of trace."},
            ),
            ActionParameter(
                name="source_name",
                required=False,
                schema={"type": "string", "description": "Restrict to one trace source (core) name."},
            ),
            ActionParameter(
                name="top_k",
                required=False,
                schema={"type": "integer", "description": "Number of functions to return (default 20)."},
            ),
        ),
        category="timeline",
        workflow_hints=(
            "Use start_tick / end_tick from timeline.summary timestamp_range to zoom into a region. "
            "Useful for comparing function activity during different execution phases.",
        ),
        related_actions=("timeline.load", "timeline.summary", "timeline.hotspots"),
    ),
    handler=timeline_window,
)
