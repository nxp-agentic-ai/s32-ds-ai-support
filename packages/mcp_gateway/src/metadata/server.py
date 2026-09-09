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

from pathlib import Path

from nxp.mcp.shared.metadata import resolve_mcp_server_metadata

_PROJECT_ROOT = Path(__file__).parent.parent.parent

MCP_SERVER_NAME, MCP_SERVER_VERSION, MCP_SERVER_DESCRIPTION = (
    resolve_mcp_server_metadata("nxp-mcp-gateway", _PROJECT_ROOT)
)
