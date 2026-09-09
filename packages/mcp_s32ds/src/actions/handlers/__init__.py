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

"""Handlers for the S32DS MCP server's static actions.

This package holds the underlying implementations (and their OpenRPC-shaped
parameter declarations) for actions that are served locally by the MCP server
rather than forwarded to the live S32DS IDE. Each handler is adapted into a
shared ``ActionExecutable`` by the matching module in
``nxp.mcp.s32ds.actions``.
"""
