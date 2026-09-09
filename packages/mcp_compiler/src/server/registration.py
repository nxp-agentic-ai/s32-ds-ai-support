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
from nxp.mcp.compiler.metadata.server import MCP_SERVER_NAME
from nxp.mcp.compiler.resources.info import register_info_resource
from nxp.mcp.compiler.prompts import register_all_prompts
from nxp.mcp.compiler.impl.launcher import resolve_install

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_tools(server, install) -> dict:
    """Register the compiler search_actions and execute_action tools.

    This server hosts the external compiler toolchains: GCC (ARM32/ARM64),
    LAX (NXP vector DSP), LAX Simulator, and SPT3.8 (NXP Signal Processing Toolbox).

    The two public MCP tools (search_actions, execute_action) are always
    registered. The active action catalog is built from the per-family action
    tuples for whichever toolchain folders are present on the current host.

    Returns:
        dict with keys ``gcc``, ``lax``, ``lax_simulator`` and ``spt``, True if the
        respective tool group was successfully registered.
    """
    flags = {"gcc": False, "lax": False, "lax_simulator": False, "spt": False}

    if not install:
        _logger.warning("No S32DS compiler install found - compiler tools unavailable")
        # Register the two-tool surface even with an empty catalog so the MCP
        # server starts cleanly and search_actions returns a clear empty result.
        try:
            from nxp.mcp.compiler.tools.compiler_search_tools import register_compiler_search_tools
            register_compiler_search_tools(server, install=None)
        except Exception as e:
            _logger.warning("Failed to register compiler search tools: %s", e, exc_info=True)
        return flags

    _logger.info("Using compiler install: %s (version=%s)", install.path, install.version_label)

    # Detect which toolchain families are present on this host.
    gcc_present = any(
        c.is_dir() for c in install.gcc_toolchain.glob(install.gcc_version_glob)
    )
    lax_present = any(
        c.is_dir() for c in install.lax_toolchain.glob(install.lax_version_glob)
    )
    # LAX Simulator is independent of the LAX compiler - check its own folder.
    lax_sim_present = install.lax_simulator.is_dir()
    spt_present = any(
        c.is_dir() for c in install.spt_toolchain.glob(install.spt_version_glob)
    )

    if not gcc_present:
        _logger.warning("GCC toolchain not found - GCC actions excluded from catalog")
    if not lax_present:
        _logger.warning("LAX toolchain not found - LAX actions excluded from catalog")
    if not lax_sim_present:
        _logger.warning("LAX simulator not found - LAX simulator actions excluded from catalog")
    if not spt_present:
        _logger.warning("SPT toolchain not found - SPT actions excluded from catalog")

    try:
        from nxp.mcp.compiler.tools.compiler_search_tools import register_compiler_search_tools
        register_compiler_search_tools(
            server,
            install=install,
            gcc_present=gcc_present,
            lax_present=lax_present,
            lax_simulator_present=lax_sim_present,
            spt_present=spt_present,
        )
        flags["gcc"] = gcc_present
        flags["lax"] = lax_present
        flags["lax_simulator"] = lax_sim_present
        flags["spt"] = spt_present
    except Exception as e:
        _logger.warning("Failed to register compiler search tools: %s", e, exc_info=True)

    return flags


def register_resources(server, config, install, tool_flags: dict) -> None:
    register_info_resource(server, config, install, tool_flags)


def register_prompts(server, config) -> None:
    register_all_prompts(server, config)


def register_all(server, config) -> None:
    install = resolve_install(config.settings)
    tool_flags = register_tools(server, install)
    register_resources(server, config, install, tool_flags)
    register_prompts(server, config)
