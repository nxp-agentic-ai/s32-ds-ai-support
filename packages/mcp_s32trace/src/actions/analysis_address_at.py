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
from nxp.mcp.s32trace.handlers.action_handlers import analysis_address_at

ANALYSIS_ADDRESS_AT_ACTION = ActionExecutable(
    contract=ActionContract(
        name="analysis.address_at",
        description=(
            "Pure ELF lookup: given an address ('pc') or a symbol name, return the resolved "
            "symbol@offset, source file:line (from DWARF), and an optional source snippet.\n\n"
            "Does NOT require a loaded CSV - accepts 'trace_id' (recommended) or a bare "
            "'elf_path'.\n\n"
            "USE CASES\n"
            "- 'What symbol is at 0x321008ca?' -> pc='0x321008ca'\n"
            "- 'Where is function TaskA defined?'  -> symbol='TaskA'\n"
            "- 'Show me the code at this address'  -> pc='0x...', snippet_window=10"
        ),
        params=(
            ActionParameter(
                name="trace_id",
                required=False,
                schema={"type": "string", "description": "Session handle from analysis.load_trace."},
            ),
            ActionParameter(
                name="elf_path",
                required=False,
                schema={
                    "type": "string",
                    "description": "Absolute path to ELF binary. Use when no trace_id is available.",
                },
            ),
            ActionParameter(
                name="pc",
                required=False,
                schema={
                    "type": "string",
                    "description": "Hex address to look up, e.g. '0x321008ca'.",
                },
            ),
            ActionParameter(
                name="symbol",
                required=False,
                schema={"type": "string", "description": "Exact symbol name to look up."},
            ),
            ActionParameter(
                name="snippet_window",
                required=False,
                schema={"type": "integer", "description": "Context lines around the resolved source line."},
            ),
        ),
        category="analysis",
        workflow_hints=(
            "Provide at least one of 'pc' or 'symbol'.  "
            "Prefer passing 'trace_id' over 'elf_path' so the source index is available.",
        ),
        related_actions=(
            "analysis.load_trace",
            "analysis.find_event",
            "analysis.get_source",
        ),
    ),
    handler=analysis_address_at,
)
