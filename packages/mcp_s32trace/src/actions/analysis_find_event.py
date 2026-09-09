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
from nxp.mcp.s32trace.handlers.action_handlers import analysis_find_event

ANALYSIS_FIND_EVENT_ACTION = ActionExecutable(
    contract=ActionContract(
        name="analysis.find_event",
        description=(
            "Filter trace events by any combination of: symbol (regex), PC/address range, "
            "source file:line, event type, core, timestamp range, or instruction mnemonic "
            "regex.  Returns enriched rows with ELF-resolved symbol@offset, file:line, and "
            "optional source snippets.\n\n"
            "SELECTOR fields (all optional, combined with AND):\n"
            "- symbol:            Regex matched against ELF symbol or Description.\n"
            "- pc_range:          [lo, hi] as hex strings or integers.\n"
            "- event_type:        'Linear', 'Info', 'Software Context', etc.\n"
            "- core:              Core name, e.g. 'R52_0_0'.\n"
            "- time_range:        [t_start, t_end] in raw timestamp units.\n"
            "- instruction_regex: Regex matched against the disassembly text in detail rows.\n\n"
            "USE CASES\n"
            "- 'Where did function main execute?' -> selector={symbol:'main'}\n"
            "- 'Find all branch instructions'     -> selector={instruction_regex:'^b'}\n"
            "- 'Show events between t=100 and t=200' -> selector={time_range:[100,200]}"
        ),
        params=(
            ActionParameter(
                name="trace_id",
                required=True,
                schema={"type": "string", "description": "Session handle from analysis.load_trace."},
            ),
            ActionParameter(
                name="selector",
                required=True,
                schema={
                    "type": "object",
                    "description": (
                        "Filter dict with any of: symbol, pc_range, event_type, core, "
                        "time_range, instruction_regex."
                    ),
                },
            ),
            ActionParameter(
                name="limit",
                required=False,
                schema={"type": "integer", "description": "Max rows to return (default 100, max 5000)."},
            ),
            ActionParameter(
                name="include_source",
                required=False,
                schema={"type": "boolean", "description": "Include source snippets in results (default true)."},
            ),
            ActionParameter(
                name="include_details",
                required=False,
                schema={
                    "type": "boolean",
                    "description": "Include child disassembly rows for each matched event (default false).",
                },
            ),
            ActionParameter(
                name="snippet_window",
                required=False,
                schema={"type": "integer", "description": "Context lines above/below matched source line."},
            ),
        ),
        category="analysis",
        workflow_hints=(
            "Use analysis.summary first to find hot functions, then call this with "
            "selector={symbol:'<name>'} to inspect specific events.",
        ),
        related_actions=(
            "analysis.load_trace",
            "analysis.summary",
            "analysis.address_at",
            "analysis.get_source",
        ),
    ),
    handler=analysis_find_event,
)
