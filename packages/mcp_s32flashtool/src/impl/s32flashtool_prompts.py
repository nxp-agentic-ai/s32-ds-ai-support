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
from nxp.mcp.s32flashtool.config.models import S32FlashToolMcpServerConfig


__all__ = ["register_s32flashtool_prompts"]


def register_s32flashtool_prompts(
    mcp: FastMCP, config: S32FlashToolMcpServerConfig
) -> None:
    # No prompts are currently registered for the S32FlashTool MCP server.
    return None
