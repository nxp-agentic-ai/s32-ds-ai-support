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
from nxp.mcp.s32trace.handlers.action_handlers import analysis_load_trace

ANALYSIS_LOAD_TRACE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="analysis.load_trace",
        description=(
            "Load and index a decoded S32Trace Trace-view CSV together with its companion ELF "
            "binary and optional project source tree.  Returns a 'trace_id' handle that all "
            "other analysis.* actions require.\n\n"
            "INPUTS\n"
            "- csv_path:   Absolute path to the Trace-view CSV exported by S32Trace / S32DS.\n"
            "- elf_path:   Absolute path to the ELF binary with DWARF debug info.\n"
            "- source_root (optional): Absolute path to the root of the user's project source.\n"
            "- extra_source_roots (optional): Additional source roots (SDK, shared libs, etc.).\n"
            "- label (optional): Human-friendly name for this session.\n"
            "- time_unit_ns (optional): Multiplier to convert raw timestamps to nanoseconds.\n"
            "- snippet_window (optional): Default context lines around a matched source line "
            "(default 3).\n\n"
            "RETURNS\n"
            "{\n"
            "  'trace_id': '<uuid>',\n"
            "  'label': '<label>',\n"
            "  'parent_event_count': 12345,\n"
            "  'total_detail_count': 98765,\n"
            "  'cores': ['R52_0_0'],\n"
            "  'time_range_raw': [0, 1234567],\n"
            "  'elf_arch': 'ARM',\n"
            "  'source': {'available': true, 'roots': [...], 'indexed_files': 42},\n"
            "  ...\n"
            "}\n\n"
            "WORKFLOW\n"
            "Call this action first.  Pass the returned trace_id to all subsequent "
            "analysis.summary / analysis.find_event / analysis.time_between / "
            "analysis.range_events / analysis.address_at / analysis.get_source calls."
        ),
        params=(
            ActionParameter(
                name="csv_path",
                required=True,
                schema={"type": "string", "description": "Absolute path to the decoded Trace-view CSV."},
            ),
            ActionParameter(
                name="elf_path",
                required=True,
                schema={"type": "string", "description": "Absolute path to the ELF binary with DWARF info."},
            ),
            ActionParameter(
                name="source_root",
                required=False,
                schema={"type": "string", "description": "Absolute path to the project source root (optional)."},
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
                name="time_unit_ns",
                required=False,
                schema={
                    "type": "number",
                    "description": "Multiply raw timestamp values by this to get nanoseconds.",
                },
            ),
            ActionParameter(
                name="snippet_window",
                required=False,
                schema={
                    "type": "integer",
                    "description": "Default source context lines above/below a match (default 3).",
                },
            ),
        ),
        category="analysis",
        workflow_hints=(
            "Always call analysis.load_trace before any other analysis.* action. "
            "Pass source_root when the user mentions a project directory.",
        ),
        related_actions=(
            "analysis.summary",
            "analysis.find_event",
            "analysis.time_between",
            "analysis.range_events",
            "analysis.address_at",
            "analysis.get_source",
        ),
    ),
    handler=analysis_load_trace,
)
