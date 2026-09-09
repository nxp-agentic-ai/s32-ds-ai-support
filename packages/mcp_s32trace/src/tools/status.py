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

from nxp.mcp.s32trace.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_status_tool(server, config, install_ctx: dict) -> None:

    @server.tool(
        name="status",
        description=(
            "S32Trace MCP server smoke test. Returns the server name, the resolved "
            "S32DS installation path, selection reason, and discovered install count "
            "so you can verify the server is reachable and that its YAML config was "
            "loaded correctly."
        ),
    )
    def status() -> dict:
        _logger.debug("status tool called")

        selected = install_ctx.get("selected")
        reason = install_ctx.get("selection_reason", "unknown")
        discovered = install_ctx.get("discovered", ())

        installation_path = str(selected.path) if selected is not None else None
        version_label = selected.version_label if selected is not None else None

        result: dict = {
            "mcp_server": "s32trace",
            "status": "ok",
            "installation_path": installation_path,
            "installation_path_configured": bool(
                (config.settings.installation_path or "").strip()
            ),
            "version_label": version_label,
            "selection_reason": reason,
            "discovered_install_count": len(discovered),
            "discovered_installs": [
                {
                    "path": str(i.path),
                    "version_label": i.version_label,
                }
                for i in discovered
            ],
        }

        if installation_path is None:
            result["warning"] = (
                "No S32DS install with S32Trace configurator found. "
                "Set s32trace.settings.installation_path in the YAML, or install "
                "S32DS under one of the standard scan roots (e.g. C:/NXP/S32DS.x.y.z)."
            )

        return result
