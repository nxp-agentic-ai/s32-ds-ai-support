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

from nxp.mcp.s32flashtool.impl.s32flashtool_search_tools import register_s32flashtool_search_tools
from nxp.mcp.s32flashtool.impl.s32flashtool_resources import register_s32flashtool_resources
from nxp.mcp.s32flashtool.impl.s32flashtool_prompts import register_s32flashtool_prompts


def register_tools(server, config) -> None:
    register_s32flashtool_search_tools(server, config)


def register_resources(server, config) -> None:
    register_s32flashtool_resources(server, config)


def register_prompts(server, config) -> None:
    register_s32flashtool_prompts(server, config)
