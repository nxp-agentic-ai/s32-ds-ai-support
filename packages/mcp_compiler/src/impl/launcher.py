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

"""Compiler toolchain discovery"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from nxp.mcp.compiler.metadata.server import MCP_SERVER_NAME

# Glob defaults — implementation detail, not exposed in config
GCC_VERSION_GLOB = "gcc_v*"
GCC_BIN_GLOB = "**/bin/"
LAX_VERSION_GLOB = "LAX"
LAX_BIN_GLOB = "**/bin/"
LAX_SIMULATOR_SUBDIR = "LAX_Simulator"  # under <S32DS root>/S32DS/tools/
SPT_VERSION_GLOB = "SPT3.8"
SPT_BIN_GLOB = "**/bin/"
COMPILE_OUTPUT_DIR = Path.cwd() / ".tmp" / "compiler" / "output"

logger = logging.getLogger(MCP_SERVER_NAME)

@dataclass(frozen=True)
class CompilerInstallInfo:
    path: Path
    gcc_toolchain: Path
    gcc_version_glob: str
    gcc_bin_glob: str
    lax_toolchain: Path
    lax_version_glob: str
    lax_bin_glob: str
    lax_simulator: Path
    spt_toolchain: Path
    spt_version_glob: str
    spt_bin_glob: str
    version_label: str
    base_dir: Path
    compile_output_dir: Path



def _candidate_roots() -> list[Path]:
    candidates: list[Path] = []

    search_parents = [Path("C:/NXP")]
    userprofile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    if userprofile:
        search_parents.append(Path(userprofile))

    for parent in search_parents:
        if parent.is_dir():
            candidates.extend(sorted(parent.glob("S32DS*")))

    return candidates


def _build_install_info(
    s32ds_root: Path,
    gcc_version_glob: str = GCC_VERSION_GLOB,
    gcc_bin_glob: str = GCC_BIN_GLOB,
    lax_version_glob: str = LAX_VERSION_GLOB,
    lax_bin_glob: str = LAX_BIN_GLOB,
    spt_version_glob: str = SPT_VERSION_GLOB,
    spt_bin_glob: str = SPT_BIN_GLOB,
) -> CompilerInstallInfo | None:

    inner = s32ds_root / "S32DS"
    build_tools = inner / "build_tools"
    lax_simulator = inner / "tools" / LAX_SIMULATOR_SUBDIR

    if not build_tools.is_dir():
        logger.debug("Skipping %s: no S32DS/build_tools folder", s32ds_root)
        return None

    # An install is valid as long as the S32DS/build_tools structure exists.
    # The presence of the GCC toolchain is checked separately at
    # tool-registration time, so an install that ships only some of the
    # external toolchains is still a valid, usable install.

    # Ensure output directory exists at startup
    COMPILE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.debug("Compile output directory: %s", COMPILE_OUTPUT_DIR)

    return CompilerInstallInfo(
        path=s32ds_root,
        gcc_toolchain=build_tools,
        gcc_version_glob=gcc_version_glob,
        gcc_bin_glob=gcc_bin_glob,
        lax_toolchain=build_tools,
        lax_version_glob=lax_version_glob,
        lax_bin_glob=lax_bin_glob,
        lax_simulator=lax_simulator,
        spt_toolchain=build_tools,
        spt_version_glob=spt_version_glob,
        spt_bin_glob=spt_bin_glob,
        version_label=s32ds_root.name,
        base_dir=Path.cwd(),
        compile_output_dir=COMPILE_OUTPUT_DIR,
    )


def discover_installs(
    roots: Optional[list[Path]] = None,
    gcc_version_glob: str = GCC_VERSION_GLOB,
    gcc_bin_glob: str = GCC_BIN_GLOB,
) -> list[CompilerInstallInfo]:
    """Check S32DS install locations and return valid installs.

    Each root is treated as a candidate s32ds_root directly — i.e.
    C:/NXP/S32DS or C:/Users/<user>/S32DS.

    Non-existent paths are silently skipped.
    """
    if roots is None:
        roots = _candidate_roots()

    results: list[CompilerInstallInfo] = []

    for root in roots:
        root = Path(root)
        logger.debug("Checking candidate root: %s (exists=%s)", root, root.is_dir())
        if not root.is_dir():
            continue
        info = _build_install_info(root, gcc_version_glob, gcc_bin_glob)
        if info:
            logger.debug("Found S32DS compiler install at %s", root)
            results.append(info)

    return results


def resolve_install(settings) -> CompilerInstallInfo | None:
    """Resolve the install to use based on settings.

    Priority:
      1. If toolchain_path is set in config — validate and use it directly.
      2. Otherwise auto-discover from the two well-known locations.
      3. If nothing found — warn the user to set toolchain_path in config yaml.
    """
    if settings.toolchain_path:
        build_tools = Path(settings.toolchain_path)
        if not build_tools.is_dir():
            logger.warning(
                "Configured toolchain_path '%s' does not exist",
                settings.toolchain_path,
            )
            return None

        s32ds_root = build_tools.parent.parent  # build_tools -> S32DS -> <root>
        info = _build_install_info(s32ds_root)
        if info:
            logger.info("Using configured compiler install at '%s'", s32ds_root)
            return info

        logger.warning(
            "toolchain_path '%s' does not match expected S32DS structure",
            settings.toolchain_path,
        )
        return None

    installs = discover_installs()

    if not installs:
        logger.warning(
            "No S32DS compiler install found at C:/NXP/S32DS or %s/S32DS. "
            "Set 'toolchain_path' in the config yaml to the build_tools folder. "
            "e.g. toolchain_path: 'C:/custom/path/S32DS/S32DS/build_tools'",
            os.environ.get("USERPROFILE") or os.environ.get("HOME") or "~",
        )
        return None

    selected = installs[0]
    logger.info("Auto-selected compiler install at '%s'", selected.path)
    return selected
