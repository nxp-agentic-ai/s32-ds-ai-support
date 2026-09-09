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
from nxp.mcp.s32trace.handlers.action_handlers import analysis_get_source

ANALYSIS_GET_SOURCE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="analysis.get_source",
        description=(
            "Fetch a source code snippet from the project source tree, by file:line or by "
            "symbol name.  Use this to retrieve more code context on demand after a query "
            "has identified an interesting location.\n\n"
            "When 'symbol' is provided the ELF DWARF info is used to find the symbol's "
            "definition address, which is then mapped to a source file and line.\n\n"
            "Requires that source_root was passed to analysis.load_trace.\n\n"
            "USE CASES\n"
            "- 'Show me the code for function TaskA'      -> symbol='TaskA'\n"
            "- 'Show me main.c around line 80'            -> file_hint='main.c', line=80\n"
            "- 'Give me more context, show 20 lines around that function' -> snippet_window=20"
        ),
        params=(
            ActionParameter(
                name="trace_id",
                required=True,
                schema={"type": "string", "description": "Session handle from analysis.load_trace."},
            ),
            ActionParameter(
                name="symbol",
                required=False,
                schema={"type": "string", "description": "Exact symbol name to locate."},
            ),
            ActionParameter(
                name="file_hint",
                required=False,
                schema={
                    "type": "string",
                    "description": "File name or partial path (basename is sufficient).",
                },
            ),
            ActionParameter(
                name="line",
                required=False,
                schema={"type": "integer", "description": "1-based line number."},
            ),
            ActionParameter(
                name="snippet_window",
                required=False,
                schema={
                    "type": "integer",
                    "description": "Lines above and below the target (default uses session default).",
                },
            ),
        ),
        category="analysis",
        workflow_hints=(
            "Use after analysis.find_event or analysis.summary to fetch source context "
            "for a specific symbol or line.  Increase snippet_window for broader context.",
        ),
        related_actions=(
            "analysis.load_trace",
            "analysis.find_event",
            "analysis.address_at",
        ),
    ),
    handler=analysis_get_source,
)
