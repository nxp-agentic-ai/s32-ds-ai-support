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

from nxp.mcp.s32ds.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_info_resource(server, config) -> None:
	port = config.settings.s32ds_rest_port

	@server.resource(uri="s32ds://info")
	def info() -> str:
		_logger.debug("info resource requested")
		return f"mcp_server: s32ds\nrest_port: {port}"
