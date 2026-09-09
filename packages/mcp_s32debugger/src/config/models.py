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

from dataclasses import dataclass, field

from nxp.mcp.shared.config.models import BaseMcpServerConfig


@dataclass(slots=True)
class DebuggerSettings:
    installation_path: str = ""
    default_gdb_variant: str = "arm32"


@dataclass(slots=True)
class DebuggerMcpServerConfig(BaseMcpServerConfig):
    """Full configuration for the Debugger MCP server (logging + settings)."""

    settings: DebuggerSettings = field(default_factory=DebuggerSettings)
