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
from nxp.mcp.s32trace.handlers.action_handlers import performance_load

PERFORMANCE_LOAD_ACTION = ActionExecutable(
    contract=ActionContract(
        name="performance.load",
        description=(
            "Load and index an S32DS Performance View .perf export together with its "
            "companion ELF binary and the project source tree.  Returns a 'session_id' "
            "handle that all other performance.* actions require.\n\n"
            "INPUTS\n"
            "- perf_path:    Absolute path to the .perf file.\n"
            "- elf_path:     Absolute path to the ELF binary with DWARF debug info.\n"
            "- source_root:  Absolute path to the project source root.\n"
            "- extra_source_roots (optional): Additional source roots.\n"
            "- label (optional):  Human-friendly session name.\n"
            "- snippet_window (optional): Context lines for performance.get_source (default 5).\n\n"
            "RETURNS\n"
            "{\n"
            "  'session_id': '<uuid>',\n"
            "  'label': '<label>',\n"
            "  'cores': ['A53_0'],\n"
            "  'function_count': 13,\n"
            "  'elf': '<elf_path>',\n"
            "  'source': {'available': true, 'indexed_files': 12}\n"
            "}\n\n"
            "WORKFLOW\n"
            "Call this action first.  Pass the returned session_id to all subsequent "
            "performance.summary / performance.function / performance.hotspots / "
            "performance.callgraph / performance.get_source calls."
        ),
        params=(
            ActionParameter(
                name="perf_path",
                required=True,
                schema={"type": "string", "description": "Absolute path to the .perf file."},
            ),
            ActionParameter(
                name="elf_path",
                required=True,
                schema={"type": "string", "description": "Absolute path to the ELF binary with DWARF info."},
            ),
            ActionParameter(
                name="source_root",
                required=True,
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
                    "description": "Default context lines for performance.get_source (default 5).",
                },
            ),
        ),
        category="performance",
        workflow_hints=(
            "Always call performance.load before any other performance.* action. "
            "Pass the returned session_id to all subsequent performance calls.",
        ),
        related_actions=(
            "performance.summary",
            "performance.function",
            "performance.hotspots",
            "performance.callgraph",
            "performance.get_source",
        ),
    ),
    handler=performance_load,
)
