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

from fastmcp import FastMCP


def register_debugger_prompt(mcp: FastMCP, config=None) -> None:
    """Register reusable MCP prompts for S32Debugger orchestration."""

    @mcp.prompt(
        name="analyze_s32debugger_request",
        description="Analyze and normalize an S32Debugger-related request before execution, script generation, troubleshooting, or routing.",
    )
    def analyze_s32debugger_request(user_request: str):
        return [
            {
                "role": "user",
                "content": (
                    "Analyze and normalize the following S32Debugger-related request before taking action.\n\n"
                    "Goals:\n"
                    "- determine the primary request type\n"
                    "- identify secondary goals\n"
                    "- extract target/core/probe/ELF/config/init/deliverable constraints\n"
                    "- detect whether the request is standalone S32Debugger or CCS/TCL\n"
                    "- detect whether the request is about startup, flash programming, config generation, automation/script authoring, init-sequence lookup/adaptation, or troubleshooting\n"
                    "- distinguish flash-only from debug-from-flash intent when relevant\n"
                    "- distinguish generation-only from execution intent when relevant\n"
                    "- identify blocking missing information\n"
                    "- recommend the next S32Debugger skill/tool path\n\n"
                    "Prefer a normalized summary with fields such as:\n"
                    "- Request type\n"
                    "- Primary goal\n"
                    "- Secondary goals\n"
                    "- Target family / SoC / core / lockstep\n"
                    "- Probe / transport\n"
                    "- Inputs (ELF/config/init/script/template)\n"
                    "- Deliverables\n"
                    "- Execution constraints\n"
                    "- Init requirement\n"
                    "- Flash intent\n"
                    "- Startup vs config-generation vs troubleshooting classification\n"
                    "- Missing information\n"
                    "- Assumptions\n"
                    "- Recommended next skill(s)\n\n"
                    "Route toward the narrowest correct next path. If the request is ambiguous, say what is missing and do not execute anything yet.\n\n"
                    f"Request to analyze:\n{user_request}"
                ),
            }
        ]

    @mcp.prompt(
        name="choose_s32debugger_solution_path",
        description="Choose the correct S32Debugger solution path for a normalized request.",
    )
    def choose_s32debugger_solution_path(normalized_request: str):
        return [
            {
                "role": "user",
                "content": (
                    "Choose the correct S32Debugger solution path for the normalized request below.\n\n"
                    "Route to the narrowest correct path. Consider these main routes:\n"
                    "- standalone live debug session\n"
                    "- flash programming workflow\n"
                    "- standalone automation/script generation\n"
                    "- existing-script adaptation\n"
                    "- init-sequence lookup / init-sequence-first workflow\n"
                    "- config generation workflow\n"
                    "- troubleshooting-first workflow\n"
                    "- CCS TCL generation\n\n"
                    "For any route that involves an init sequence, config generation, or passing a "
                    "core_name to a tool, ALWAYS apply the resolve_core_name_from_context skill "
                    "first to read _CORE_NAME and _SOC_NAME verbatim from <family>_context.py "
                    "before proceeding. Do not guess these values from the SoC part number.\n\n"
                    "Recommend:\n"
                    "- the primary route\n"
                    "- any secondary supporting routes\n"
                    "- which S32Debugger skills/resources should be used next\n"
                    "- whether the request should go through startup, flash programming, automation, adaptation, init lookup, config generation, or troubleshooting first\n"
                    "- whether resolve_core_name_from_context is required as a prerequisite step\n\n"
                    "Respect explicit constraints such as:\n"
                    "- do not run yet\n"
                    "- keep session open\n"
                    "- no TCL\n"
                    "- reuse known working flow\n"
                    "- generation only\n\n"
                    f"Normalized request:\n{normalized_request}"
                ),
            }
        ]

    @mcp.prompt(
        name="resolve_s32debugger_gdb_variant",
        description="Resolve the correct S32Debugger GDB variant for a given core and explain the mapping.",
    )
    def resolve_s32debugger_gdb_variant(core_name: str):
        return [
            {
                "role": "user",
                "content": (
                    "Resolve the correct S32Debugger GDB variant for the given core.\n\n"
                    "Use these rules:\n"
                    "- M-class and R-class ARM cores -> arm32\n"
                    "- A-class ARM cores -> arm64\n\n"
                    "Normalize away instance suffixes when needed (for example M7_0 -> M7).\n"
                    "If the mapping is uncertain, say so explicitly.\n\n"
                    "Return:\n"
                    "- normalized core type\n"
                    "- chosen GDB variant\n"
                    "- short justification\n\n"
                    f"Core name:\n{core_name}"
                ),
            }
        ]
