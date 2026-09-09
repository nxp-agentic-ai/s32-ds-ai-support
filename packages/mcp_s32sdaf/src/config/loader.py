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

from nxp.mcp.shared.config.loader import load_mcp_server_config

from .models import S32SDAFMcpServerConfig, S32SDAFSettings


def load_standalone_config(path: str | None = None) -> S32SDAFMcpServerConfig:
    return load_mcp_server_config(path, S32SDAFSettings, S32SDAFMcpServerConfig)
