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


def register_info_resource(server, config) -> None:
    installation_path = config.settings.installation_path
    rest_host = config.settings.rest_host
    rest_port = config.settings.rest_port

    @server.resource(uri="info://status")
    def info() -> str:
        _logger.debug("info resource requested")
        return (
            f"mcp_server: s32trace\n"
            f"status: ok\n"
            f"installation_path: {installation_path or '(not configured)'}\n"
            f"rest_endpoint: {rest_host}:{rest_port}"
        )
