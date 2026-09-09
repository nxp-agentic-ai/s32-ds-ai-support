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

import logging

from nxp.mcp.s32debugger.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


def _s32debugger_prompts_index() -> str:
    return """# S32Debugger MCP Prompts Index

This server exposes MCP resources, reusable prompts, and skill documentation for standalone S32Debugger orchestration.
Use this index as a quick-reference entry point for the current prompt set, the current skill set, and the standardized MCP action protocol.

## Canonical MCP tools
The S32Debugger component exposes one standardized protocol through two tools only:

### 1. `search_actions(...)`
Use this first to discover the most relevant callable actions.
The response includes action descriptions and input schemas so the selected action can be called directly.

### 2. `execute_action(action=..., params={...})`
Use this to execute one standardized action.
Examples:
- `execute_action(action="control.set_installation_path", params={"installation_path": "C:/NXP/S32DBG.3.6.8_b2605041"})`
- `execute_action(action="control.adopt_session")`
- `execute_action(action="generate.config_from_template", params={...})`
- `execute_action(action="bridge.create_config", params={...})`
- `execute_action(action="control.start_gta")`
- `execute_action(action="control.start_gdb", params={...})`

## MCP resources
- `s32debugger://info`
- `s32debugger://prompts/index`

## Recommended agent usage order
1. `search_actions`
2. `execute_action`

Never guess parameter names or action semantics when `search_actions` has already returned the machine-readable input schema.

## Available prompt resources
- `analyze_s32debugger_request`
- `choose_s32debugger_solution_path`
- `resolve_s32debugger_gdb_variant`

## Available skills (current set)
- `adapt_existing_s32debugger_script`
- `connect_gdb_to_s32_debug_probe`
- `convert_ltb_cmm_to_s32debugger_python`
- `debug_from_flash`
- `discover_s32debugger_installation`
- `error_resolution`
- `flash_only_operations`
- `flash_programming`
- `generate_gdb_config_file`
- `generate_s32debugger_automation_script`
- `lookup_for_soc_init_sequence`
- `navigate_s32debugger_installation`
- `resolve_core_name_from_context`
- `resolve_s32debugger_gdb_variant`
- `start_multicore_standalone_live_debug_session`
- `start_singlecore_standalone_live_debug_session`
- `start_standalone_live_session`
"""



def register_info_resource(server, config) -> None:
    installation_path = (config.settings.installation_path or "").strip()
    default_gdb_variant = config.settings.default_gdb_variant

    @server.resource(uri="s32debugger://info")
    def info() -> str:
        _logger.debug("info resource requested")
        installation_path_configured = bool(installation_path)
        warning_text = ""
        if not installation_path_configured:
            warning_text = (
                "warning: In the config YAML used for this MCP server, `settings.installation_path` is not set.\n"
            )
        return (
            f"mcp_server: s32debugger\n"
            f"configured_installation_path: {installation_path or None}\n"
            f"installation_path_configured: {installation_path_configured}\n"
            f"{warning_text}"
            f"default_gdb_variant: {default_gdb_variant}\n"
            f"standard_tools: search_actions, execute_action"
        )

    @server.resource(uri="s32debugger://prompts/index")
    def prompts_index() -> str:
        _logger.debug("prompts index resource requested")
        return _s32debugger_prompts_index()
