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

"""``list_installs`` tool - report every S32CT install discovered on the host.

Read-only: re-runs :func:`nxp.mcp.s32ct.tools.launcher.discover_installs` and
returns the results plus the install the server itself selected at startup.
Useful for agents / humans to see which distributions are available without
having to parse the ``s32ct://info`` resource.
"""
import logging

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import (
    S32CTContext,
    discover_installs,
)

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_list_installs_tool(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    @server.tool(
        name="list_installs",
        description=(
            "List every S32 Configuration Tools install discovered on this host. "
            "Returns both the desktop (standalone) variant and the "
            "S32DS-integrated variant where present, with their version, "
            "launcher path, and MCU data root. Also reports which install the "
            "server selected at startup and why."
        ),
    )
    def list_installs() -> dict:
        _logger.debug("list_installs tool called")
        # Re-scan so the result reflects whatever is installed *now*, not just
        # what was on disk at server start. The selected install still comes
        # from startup state - changing it requires a server restart.
        discovered = discover_installs()
        return {
            "selected": {
                "distribution": ctx.distribution,
                "version": ctx.version_label,
                "path": str(ctx.install),
                "launcher": str(ctx.launcher),
                "reason": ctx.selection_reason,
            },
            "discovered": [
                {
                    "distribution": i.distribution,
                    "version": i.version_label,
                    "path": str(i.path),
                    "launcher": str(i.launcher),
                    "launcher_ini": str(i.launcher_ini),
                    "mcu_data_root": str(i.mcu_data_root),
                    "mcu_data_root_exists": i.mcu_data_root.exists(),
                }
                for i in discovered
            ],
        }
