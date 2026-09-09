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

from importlib import import_module

from nxp.mcp.shared.models.server import McpServerModule


def load_mcp_server_module(module_path: str) -> McpServerModule:
    module = import_module(module_path)
    if not isinstance(module, McpServerModule):
        raise TypeError(
            f"Module '{module_path}' does not satisfy the McpServerModule protocol. "
            f"Ensure it exports: MCP_SERVER_NAME, build_mcp_server_config, "
            f"create_mcp_server, run_stdio"
        )
    return module
