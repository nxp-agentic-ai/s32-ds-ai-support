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
class S32TraceSettings:
    # Path to the S32Trace installation root (e.g. S32DS install that contains
    # the S32Trace feature)
    installation_path: str = ""
    # Reserved for future S32Trace GUI control tools.
    rest_host: str = "localhost"
    rest_port: int = 0


@dataclass(slots=True)
class S32TraceMcpServerConfig(BaseMcpServerConfig):
    """Full configuration for the S32Trace MCP server (logging + settings)."""

    settings: S32TraceSettings = field(default_factory=S32TraceSettings)
