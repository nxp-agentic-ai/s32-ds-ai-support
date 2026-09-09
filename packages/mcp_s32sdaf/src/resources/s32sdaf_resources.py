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

from nxp.mcp.s32sdaf.metadata.server import MCP_SERVER_NAME, MCP_SERVER_VERSION, MCP_SERVER_DESCRIPTION

_logger = logging.getLogger(MCP_SERVER_NAME)

def register_s32sdaf_resources(server, config) -> None:
    installation_path = config.settings.installation_path or "(auto-discover)"

    @server.resource(uri="s32sdaf://info")
    def info() -> str:
        _logger.debug("info resource requested")
        return (
            f"mcp_server: s32sdaf\n"
            f"version: {MCP_SERVER_VERSION}\n"
            f"description: {MCP_SERVER_DESCRIPTION}\n"
            f"installation_path: {installation_path}\n"
        )

    @server.resource(
        uri="s32sdaf://docs/capabilities",
        name="S32SDAF MCP capabilities",
        mime_type="text/plain",
    )
    def capabilities() -> str:
        _logger.debug("capabilities resource requested")
        return """# S32SDAF MCP Server Capabilities

                The S32SDAF MCP server wraps the Volkano smart-card toolchain for the
                NXP S32 Secure Debug Authorization Framework (SDAF).

                ## What this server does
                - Discovers Volkano installations on the host machine
                - Inspects registered UIDs and keys on a Volkano smart card
                - Registers plain ADKP keys for device UIDs
                - Exports the smart card's public wrapping key
                - Wraps plain key material using the exported public key
                - Registers wrapped keys (KUID and ODAK-class) for device UIDs
                - Performs challenge-response authentication for registered UIDs
                - Deletes UID records from the smart card (irreversible, requires confirmation)

                ## Supported key types
                - ADKP (plain, registered directly)
                - KUID (wrapped, registered via wrap-then-register workflow)
                - KUID_RF (wrapped, requires applet v1.4+)
                - KUID_PRE_FA (wrapped, requires applet v1.4+)
                - ODAK (wrapped, requires applet v1.5+ and 16-byte UID)

                ## Installation auto-discovery
                When no explicit installation path is provided, the server searches:
                - C:/NXP/SDAF*   (S32 SDAF standalone installations)
                - C:/NXP/S32DS*  (S32 Design Studio installations)
                - C:/NXP/S32DBG*   (S32 Debugger standalone installations)


                The newest version found is used automatically.

                ## Skills available
                - s32sdaf-auth-device       — challenge-response authentication
                - s32sdaf-register-key      — plain ADKP and wrapped-key registration
                - s32sdaf-wrap-and-register — wrap a plain key then register it
                """