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
from nxp.mcp.s32trace.handlers.action_handlers import timeline_function

TIMELINE_FUNCTION_ACTION = ActionExecutable(
    contract=ActionContract(
        name="timeline.function",
        description=(
            "Return detailed timeline statistics for a named function: total sample count, "
            "per-address sample breakdown, and optional DWARF source location.\n\n"
            "Handles inlined copies: searching for 'clamp_i32' will match both "
            "'clamp_i32' and 'clamp_i32_0x33d83d24' instances.\n\n"
            "INPUTS\n"
            "- session_id: Session handle from timeline.load.\n"
            "- name: Function name (exact or prefix before _0x...).\n"
            "- source_name (optional): Restrict to one trace source / core.\n"
            "- include_source (optional): Attach DWARF source location and snippet (default true).\n\n"
            "RETURNS\n"
            "{\n"
            "  'found': true,\n"
            "  'name': 'slow_top',\n"
            "  'instances': [{name, address, size, total_samples, per_address, source_file, ...}]\n"
            "}"
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session handle from timeline.load."},
            ),
            ActionParameter(
                name="name",
                required=True,
                schema={"type": "string", "description": "Function name to look up."},
            ),
            ActionParameter(
                name="source_name",
                required=False,
                schema={"type": "string", "description": "Restrict to one trace source (core) name."},
            ),
            ActionParameter(
                name="include_source",
                required=False,
                schema={
                    "type": "boolean",
                    "description": "Include DWARF source file/line and snippet (default true).",
                },
            ),
        ),
        category="timeline",
        workflow_hints=("Use after timeline.hotspots to drill into a specific function.",),
        related_actions=("timeline.load", "timeline.hotspots", "timeline.source"),
    ),
    handler=timeline_function,
)
