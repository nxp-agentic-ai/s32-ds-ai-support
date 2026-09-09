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

from nxp.mcp.s32sdaf.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_s32sdaf_prompt(server, config) -> None:
    installation_path = config.settings.installation_path or "(auto-discover)"

    @server.prompt(name="greeting")
    def s32sdaf_greeting() -> str:
        _logger.debug("s32sdaf_greeting prompt requested")
        return (
            f"You are interacting with the S32SDAF MCP server.\n"
            f"This server wraps the Volkano smart-card toolchain for the "
            f"NXP S32 Secure Debug Authorization Framework (SDAF).\n"
            f"Configured installation path: {installation_path}\n"
            f"Available skills: s32sdaf-auth-device, s32sdaf-register-key, s32sdaf-wrap-and-register"
        )
