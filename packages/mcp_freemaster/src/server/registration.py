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

from fastmcp import FastMCP

from nxp.mcp.shared.action import StandardizingServer

from nxp.mcp.freemaster.config import FreeMASTERMcpServerConfig
from nxp.mcp.freemaster.metadata import MCP_SERVER_NAME
from nxp.mcp.freemaster.tools import register_freemaster_tools

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_tools(server: FastMCP, config: FreeMASTERMcpServerConfig) -> None:
    """Register the FreeMASTER tools with the standardized response envelope.

    Registering through ``StandardizingServer`` adds the shared ``success`` flag
    and a structured ``error`` object on failure, on top of whatever payload the
    tools already return, so failures are uniformly detectable across the MCP.
    """

    standardized = StandardizingServer(server, component_logger=_logger)
    register_freemaster_tools(standardized, config)
