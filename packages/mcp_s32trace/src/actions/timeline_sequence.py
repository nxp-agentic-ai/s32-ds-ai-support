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
from nxp.mcp.s32trace.handlers.action_handlers import timeline_sequence

TIMELINE_SEQUENCE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="timeline.sequence",
        description=(
            "Return an ordered list of function transitions (PC changes over time) from "
            "the timeline data.  Each entry represents a point where the sampled PC "
            "moved to a different function.\n\n"
            "INPUTS\n"
            "- session_id: Session handle from timeline.load.\n"
            "- source_name (optional): Restrict to one trace source / core.\n"
            "- limit (optional): Maximum number of transitions to return (default 100).\n\n"
            "RETURNS\n"
            "{\n"
            "  'limit': 100,\n"
            "  'transitions': [\n"
            "    {timestamp, address, function, samples},\n"
            "    ...\n"
            "  ]\n"
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
                schema={"type": "string", "description": "Restrict to one trace source (core) name."},
            ),
            ActionParameter(
                name="limit",
                required=False,
                schema={"type": "integer", "description": "Maximum number of transitions to return (default 100)."},
            ),
        ),
        category="timeline",
        workflow_hints=(
            "Use to understand the call order and execution flow across the entire trace. "
            "Increase limit only when needed; each entry is one function change.",
        ),
        related_actions=("timeline.load", "timeline.summary", "timeline.function"),
    ),
    handler=timeline_sequence,
)
