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

from nxp.mcp.s32trace.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_s32trace_prompt(server, config) -> None:
    installation_path = config.settings.installation_path

    @server.prompt(name="greeting")
    def s32trace_greeting() -> str:
        _logger.debug("s32trace_greeting prompt requested")
        configured = f"Installation path: {installation_path}" if installation_path else "No installation path configured."
        return (
            "You are interacting with the S32Trace MCP server. "
            "This server exposes tools for configuring and controlling S32Trace "
            "(the tracing and analysis feature of NXP S32 Design Studio). "
            f"{configured}"
        )
