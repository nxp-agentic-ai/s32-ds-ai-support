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

"""S32 Configuration Tools - MCP tool modules.

Each module registers one or more ``@server.tool`` callables onto the FastMCP
instance. The shared CLI plumbing (subprocess execution, launcher resolution,
GetValue table parsing, CLI builder) lives in :mod:`nxp.mcp.s32ct.tools.launcher`.
"""
