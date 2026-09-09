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

"""``env`` - unified environment / installation probe for S32 Configuration Tools.

Folds three previously-separate read-only metadata tools into one
``query``-discriminated surface:

* ``query="status"`` -- was ``status``: smoke-test that returns the effective
  configuration (distribution, version, paths, timeout) with ``_exists`` flags.
* ``query="version"`` -- was ``get_version``: invokes the active launcher to
  return the installed S32CT name + version string.
* ``query="installs"`` -- was ``list_installs``: re-scans the host for every
  S32CT install discovered (both desktop and S32DS-integrated variants) and
  reports which one the server selected at startup and why.

Why one tool: all three are **read-only environment introspection** answering
"what's the toolchain situation?" They share no parameters except optional
launcher overrides, and they're typically called once at session start. One
tool with three queries removes two slots from the system prompt.
"""
import logging
from typing import Literal, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import (
    S32CTContext,
    discover_installs,
    get_version_impl,
)

_logger = logging.getLogger(MCP_SERVER_NAME)


def _status_payload(ctx: S32CTContext) -> dict:
    return {
        "mcp_server": "s32ct",
        "distribution": ctx.distribution,
        "version": ctx.version_label,
        "selection_reason": ctx.selection_reason,
        "discovered_install_count": len(ctx.discovered_installs),
        "installation_path": str(ctx.install) if ctx.is_selected else "",
        "installation_path_exists": (
            ctx.is_selected and ctx.install.exists()
        ),
        "launcher": str(ctx.launcher) if ctx.is_selected else "",
        "launcher_exists": ctx.is_selected and ctx.launcher.exists(),
        "tools_ini": str(ctx.tools_ini) if ctx.is_selected else "",
        "tools_ini_exists": ctx.is_selected and ctx.tools_ini.exists(),
        "mcu_data_root": (
            str(ctx.mcu_data_root) if ctx.mcu_data_root.parts else ""
        ),
        "mcu_data_root_exists": (
            bool(ctx.mcu_data_root.parts) and ctx.mcu_data_root.exists()
        ),
        "documentation_path": (
            str(ctx.documentation_path)
            if str(ctx.documentation_path)
            else ""
        ),
        "documentation_path_exists": (
            ctx.documentation_path.exists()
            if str(ctx.documentation_path)
            else False
        ),
        "timeout_s": ctx.timeout_s,
    }


def _installs_payload(ctx: S32CTContext) -> dict:
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


def register_env_tool(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    @server.tool(
        name="env",
        description=(
            "Unified environment / installation probe for S32 Configuration "
            "Tools. Folds the former `status`, `get_version`, and "
            "`list_installs` tools into one `query`-routed surface. All "
            "queries are read-only.\n\n"
            "Queries:\n"
            "  - `status` (default) -- smoke-test the active S32CT config. "
            "Returns `distribution` (`desktop` for standalone S32CT, "
            "`integrated_s32ds` for the variant bundled in S32 Design "
            "Studio), `version`, `selection_reason`, `installation_path`, "
            "derived `launcher` + `tools_ini`, `mcu_data_root`, "
            "`documentation_path`, and `timeout_s`, each with an `_exists` "
            "flag. Use this to verify the YAML config end-to-end before "
            "issuing a real headless invocation.\n"
            "  - `version` -- invoke the active launcher to return the "
            "installed S32CT name and version string. Optional "
            "`installation_path` / `s32ct_launcher` overrides target a "
            "specific install.\n"
            "  - `installs` -- list every S32CT install discovered on this "
            "host (re-scans on every call). Returns both the desktop and "
            "S32DS-integrated variants where present, with their version, "
            "launcher path, and MCU data root, plus which install the "
            "server selected at startup and why."
        ),
    )
    def env(
        query: Literal["status", "version", "installs"] = "status",
        installation_path: Optional[str] = None,
        s32ct_launcher: Optional[str] = None,
    ):
        if query == "status":
            _logger.debug("env(query=status)")
            return _status_payload(ctx)

        if query == "installs":
            _logger.debug("env(query=installs)")
            return _installs_payload(ctx)

        if query == "version":
            try:
                return get_version_impl(
                    ctx, installation_path, s32ct_launcher,
                )
            except Exception as e:
                _logger.exception("env(query=version) failed")
                return f"env(query=version) error: {e}"

        return {"error": f"Unknown env query: {query!r}"}
