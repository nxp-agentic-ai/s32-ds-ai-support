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
from nxp.mcp.s32trace.handlers.action_handlers import timeline_source

TIMELINE_SOURCE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="timeline.source",
        description=(
            "Return a source snippet annotated with per-line sample counts from the timeline. "
            "Requires elf_path and source_root to have been provided to timeline.load.\n\n"
            "INPUTS\n"
            "- session_id: Session handle from timeline.load.\n"
            "- symbol (optional): Function name; resolves file/line via DWARF.\n"
            "- file_hint (optional): Partial or full source file name.\n"
            "- line (optional): Center line for the snippet.\n"
            "- source_name (optional): Restrict sample aggregation to one core.\n"
            "- snippet_window (optional): Context lines above/below center (default from load).\n\n"
            "RETURNS\n"
            "{\n"
            "  'file': '/path/to/workloads.c',\n"
            "  'center_line': 42,\n"
            "  'lines': [{line_no, text, samples}, ...]\n"
            "}"
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session handle from timeline.load."},
            ),
            ActionParameter(
                name="symbol",
                required=False,
                schema={"type": "string", "description": "Function name to resolve to a source location."},
            ),
            ActionParameter(
                name="file_hint",
                required=False,
                schema={"type": "string", "description": "Partial or full source file name."},
            ),
            ActionParameter(
                name="line",
                required=False,
                schema={"type": "integer", "description": "Center line for the snippet."},
            ),
            ActionParameter(
                name="source_name",
                required=False,
                schema={"type": "string", "description": "Restrict sample aggregation to one trace source."},
            ),
            ActionParameter(
                name="snippet_window",
                required=False,
                schema={"type": "integer", "description": "Lines of context above/below center (default from load)."},
            ),
        ),
        category="timeline",
        workflow_hints=(
            "Requires elf_path and source_root to have been passed to timeline.load. "
            "Call after timeline.function to see the hot lines inside the function.",
        ),
        related_actions=("timeline.load", "timeline.function", "timeline.hotspots"),
    ),
    handler=timeline_source,
)
