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
from nxp.mcp.s32trace.handlers.action_handlers import performance_get_source

PERFORMANCE_GET_SOURCE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="performance.get_source",
        description=(
            "Return a source snippet for a function or file location, annotated with the "
            "function's performance context (inclusive/exclusive time, call count).\n\n"
            "Source resolution uses the ELF DWARF index to map a symbol to its file and "
            "line number, then reads the local source file via the source index.\n\n"
            "INPUTS\n"
            "- session_id:              ID returned by performance.load.\n"
            "- symbol (optional):       Function name -- preferred; used for DWARF lookup.\n"
            "- file_hint (optional):    Fallback file path or basename when symbol is absent.\n"
            "- line (optional):         Anchor line; defaults to function entry point.\n"
            "- core (optional):         Restrict symbol lookup to a single core.\n"
            "- snippet_window (optional): Context lines around anchor (default from load).\n\n"
            "Provide at least one of 'symbol' or 'file_hint'."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from performance.load."},
            ),
            ActionParameter(
                name="symbol",
                required=False,
                schema={"type": "string", "description": "Function/symbol name for DWARF lookup."},
            ),
            ActionParameter(
                name="file_hint",
                required=False,
                schema={"type": "string", "description": "File path or basename fallback."},
            ),
            ActionParameter(
                name="line",
                required=False,
                schema={"type": "integer", "description": "Anchor line number."},
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
            ActionParameter(
                name="snippet_window",
                required=False,
                schema={"type": "integer", "description": "Context lines around anchor."},
            ),
        ),
        category="performance",
        workflow_hints=("Call performance.load first. ELF must be provided for symbol->file resolution.",),
        related_actions=("performance.load", "performance.function", "performance.hotspots"),
    ),
    handler=performance_get_source,
)
