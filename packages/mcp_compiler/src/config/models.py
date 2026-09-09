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
class CompilerSettings:
    toolchain_path: str = ""


@dataclass(slots=True)
class CompilerMcpServerConfig(BaseMcpServerConfig):
    """Full configuration for the Compiler MCP server (logging + settings)."""

    settings: CompilerSettings = field(default_factory=CompilerSettings)
