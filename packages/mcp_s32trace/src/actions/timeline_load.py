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
from nxp.mcp.s32trace.handlers.action_handlers import timeline_load

TIMELINE_LOAD_ACTION = ActionExecutable(
    contract=ActionContract(
        name="timeline.load",
        description=(
            "Load and index an S32DS Timeline view .timeline file together with an optional "
            "companion ELF binary and project source tree.  Returns a 'session_id' handle "
            "that all other timeline.* actions require.\n\n"
            "INPUTS\n"
            "- timeline_path: Absolute path to the .timeline file.\n"
            "- elf_path (optional): Absolute path to the ELF binary with DWARF debug info.\n"
            "  Required for source-annotated queries (timeline.source).\n"
            "- source_root (optional): Absolute path to the root of the project source tree.\n"
            "- extra_source_roots (optional): Additional source roots (SDK, etc.).\n"
            "- label (optional): Human-friendly name for this session.\n"
            "- snippet_window (optional): Default context lines for timeline.source (default 5).\n\n"
            "RETURNS\n"
            "{\n"
            "  'session_id': '<uuid>',\n"
            "  'sources': ['A53 0'],\n"
            "  'function_count': 87,\n"
            "  'data_row_count': 10399,\n"
            "  'timestamp_range': [0, 3007744],\n"
            "  'elf_arch': 'aarch64',\n"
            "  'source': {'available': true, 'indexed_files': 12}\n"
            "}\n\n"
            "WORKFLOW\n"
            "Call this action first.  Pass the returned session_id to all subsequent "
            "timeline.summary / timeline.hotspots / timeline.function / "
            "timeline.window / timeline.sequence / timeline.source calls."
        ),
        params=(
            ActionParameter(
                name="timeline_path",
                required=True,
                schema={"type": "string", "description": "Absolute path to the .timeline file."},
            ),
            ActionParameter(
                name="elf_path",
                required=False,
                schema={"type": "string", "description": "Absolute path to the ELF binary with DWARF info."},
            ),
            ActionParameter(
                name="source_root",
                required=False,
                schema={"type": "string", "description": "Absolute path to the project source root."},
            ),
            ActionParameter(
                name="extra_source_roots",
                required=False,
                schema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional source roots such as an SDK directory.",
                },
            ),
            ActionParameter(
                name="label",
                required=False,
                schema={"type": "string", "description": "Optional human-friendly session label."},
            ),
            ActionParameter(
                name="snippet_window",
                required=False,
                schema={
                    "type": "integer",
                    "description": "Default context lines for timeline.source (default 5).",
                },
            ),
        ),
        category="timeline",
        workflow_hints=(
            "Always call timeline.load before any other timeline.* action. "
            "Pass the returned session_id to all subsequent timeline calls.",
        ),
        related_actions=(
            "timeline.summary",
            "timeline.hotspots",
            "timeline.function",
            "timeline.window",
            "timeline.sequence",
            "timeline.source",
        ),
    ),
    handler=timeline_load,
)
