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

"""``status`` tool — quick smoke-test that reports the resolved S32CT paths.

Mirrors the convention used by ``mcp_freemaster.tools.status``: a single
zero-input tool that returns the effective configuration the server will pass
to every other S32CT tool. Useful to verify the YAML config end-to-end before
issuing a real headless invocation.
"""
import logging

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import S32CTContext

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_status_tool(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    @server.tool(
        name="status",
        description=(
            "S32 Configuration Tools server smoke test. Returns the active "
            "`distribution` (`desktop` for standalone S32CT, `integrated_s32ds` "
            "for the variant bundled in S32 Design Studio), `version`, "
            "`selection_reason`, `installation_path`, derived `launcher` + "
            "`tools_ini`, `mcu_data_root`, `documentation_path`, and "
            "`timeout_s`, each with an `_exists` flag. Use this to verify the "
            "YAML config end-to-end before issuing a real headless invocation, "
            "and to confirm the advertised `documentation_path` matches what "
            "`mcp_knowledge` indexes. See the `s32ct-distributions` skill for "
            "what the two distributions are and how they differ."
        ),
    )
    def status() -> dict:
        _logger.debug("status tool called")
        return {
            "mcp_server": "s32ct",
            "distribution": ctx.distribution,
            "version": ctx.version_label,
            "selection_reason": ctx.selection_reason,
            "discovered_install_count": len(ctx.discovered_installs),
            "installation_path": str(ctx.install) if ctx.is_selected else "",
            "installation_path_exists": ctx.is_selected and ctx.install.exists(),
            "launcher": str(ctx.launcher) if ctx.is_selected else "",
            "launcher_exists": ctx.is_selected and ctx.launcher.exists(),
            "tools_ini": str(ctx.tools_ini) if ctx.is_selected else "",
            "tools_ini_exists": ctx.is_selected and ctx.tools_ini.exists(),
            "mcu_data_root": str(ctx.mcu_data_root) if ctx.mcu_data_root.parts else "",
            "mcu_data_root_exists": bool(ctx.mcu_data_root.parts) and ctx.mcu_data_root.exists(),
            "documentation_path": str(ctx.documentation_path) if str(ctx.documentation_path) else "",
            "documentation_path_exists": (
                ctx.documentation_path.exists() if str(ctx.documentation_path) else False
            ),
            "timeout_s": ctx.timeout_s,
        }
