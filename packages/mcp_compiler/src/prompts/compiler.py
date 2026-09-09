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

from nxp.mcp.compiler.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_compiler_prompt(server, config) -> None:

    @server.prompt(
        name="list_available_tools",
        description="List all available external compiler tools on this server.",
    )
    def list_available_tools():
        _logger.debug("list_available_tools prompt requested")
        return (
            "Discover all available compiler tools on this server by calling every "
            "list_*_compiler_tools() tool that is registered, then present "
            "the results to the user in a clear summary. The available tools depend on what toolchains "
            "are installed - call them all and report what is found."
        )
