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

"""``get_version`` - read-only version & path probe."""
import logging
from typing import Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import S32CTContext, get_version_impl

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_get_version_tool(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    @server.tool(
        name="get_version",
        description=(
            "Return the installed S32 Configuration Tools name, version, and "
            "install path. Works against both supported distributions (standalone "
            "`desktop` via `toolsc.exe`/`tools.ini`, and `integrated_s32ds` via "
            "`s32dsc.exe`/`s32ds.ini`); the right launcher is picked from the "
            "active server context. Read-only. See the `s32ct-distributions` skill "
            "for background."
        ),
    )
    def get_version(
        installation_path: Optional[str] = None,
        s32ct_launcher: Optional[str] = None,
    ) -> str:
        try:
            return get_version_impl(ctx, installation_path, s32ct_launcher)
        except Exception as e:
            _logger.exception("get_version failed")
            return f"get_version error: {e}"
