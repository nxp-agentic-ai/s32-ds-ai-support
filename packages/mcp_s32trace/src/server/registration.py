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

from nxp.mcp.s32trace.tools.status import register_status_tool
from nxp.mcp.s32trace.tools import register_s32trace_search_tools
from nxp.mcp.s32trace.resources.info import register_info_resource
from nxp.mcp.s32trace.prompts.greet import register_s32trace_prompt
from nxp.mcp.s32trace.impl.discovery import discover_installs, select_install


def register_tools(server, config) -> None:
    yaml_install = (config.settings.installation_path or "").strip()
    discovered = discover_installs()
    selected, reason = select_install(yaml_install, discovered=discovered)
    install_ctx = {
        "selected": selected,
        "selection_reason": reason,
        "discovered": tuple(discovered),
    }
    register_status_tool(server, config, install_ctx)
    register_s32trace_search_tools(server, config, install_ctx)


def register_resources(server, config) -> None:
    register_info_resource(server, config)


def register_prompts(server, config) -> None:
    register_s32trace_prompt(server, config)
