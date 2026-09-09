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

"""S32Trace S32DS installation discovery.

Mirrors the approach used by nxp.mcp.s32ct.tools.launcher, scoped to what
S32Trace needs: finding S32 Design Studio install roots that ship the
S32Trace configurator plugin.  S32Trace is only distributed as part of
S32 Design Studio -- there is no separate standalone variant -- so only the
S32DS directory shape is probed.

Precedence in select_install():
  1. Explicit yaml_install path (YAML override).
  2. Newest auto-discovered S32DS install (highest version_tuple).
  3. None found.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from nxp.mcp.s32trace.metadata.server import MCP_SERVER_NAME

logger = logging.getLogger(MCP_SERVER_NAME)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class InstallInfo:
    """One discovered S32DS install on the host filesystem."""

    path: Path               # S32DS install root
    configurator_dir: Path   # eclipse/plugins/<trace-configurator-plugin>
    version_tuple: tuple[int, ...]
    version_label: str


# ---------------------------------------------------------------------------
# Version parsing
# ---------------------------------------------------------------------------

_S32DS_VERSION_RE = re.compile(
    r"^S32DS\.(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?$",
    re.IGNORECASE,
)


def _parse_s32ds_version(dirname: str) -> tuple[tuple[int, ...], str]:
    """Return (version_tuple, label) for a folder name like 'S32DS.3.6.9'."""
    m = _S32DS_VERSION_RE.match(dirname)
    if not m:
        return (), ""
    major = int(m["major"])
    minor = int(m["minor"])
    patch = int(m["patch"] or 0)
    label = f"{major}.{minor}" + (f".{patch}" if patch else "")
    return (major, minor, patch), label


# ---------------------------------------------------------------------------
# Candidate validation
# ---------------------------------------------------------------------------

# Glob pattern for the data plugin that ships the S32Trace configurator
# templates.  Must stay in sync with configurator._PLUGIN_GLOB.
_PLUGIN_GLOB = "com.nxp.s32ds.sa.data.common_*"


def _find_configurator_dir(install: Path) -> Optional[Path]:
    """Return the S32Trace configurator plugin dir under <install>/eclipse/plugins.

    Matches the data plugin that ships the configurator templates
    (com.nxp.s32ds.sa.data.common_*).  Returns None when the plugins folder
    does not exist or no matching plugin is found.
    """
    plugins = install / "eclipse" / "plugins"
    if not plugins.is_dir():
        return None
    matches = sorted(plugins.glob(_PLUGIN_GLOB))
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _default_scan_roots() -> list[Path]:
    """Scan roots searched by default, in priority order.

    Matches the same set used by nxp.mcp.s32ct.tools.launcher so that both
    servers discover the same S32DS installs.  Non-existent entries are
    silently skipped by discover_installs().
    """
    roots: list[Path] = [Path(r"C:\NXP")]
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        val = os.environ.get(env_var)
        if val:
            roots.append(Path(val) / "NXP")
    roots.append(Path("/opt/nxp"))
    roots.append(Path("/usr/local/NXP"))
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        roots.append(Path(home) / "NXP")
    return roots


def discover_installs(roots: Optional[Iterable[Path]] = None) -> list[InstallInfo]:
    """Probe the filesystem and return every S32DS install with an S32Trace configurator.

    The scan is shallow (one directory level under each root) and read-only.
    Non-existent roots are silently skipped.  Results are sorted newest-first
    by version_tuple.
    """
    if roots is None:
        roots = _default_scan_roots()

    results: list[InstallInfo] = []

    for root in roots:
        if not root.is_dir():
            continue
        try:
            entries = list(root.iterdir())
        except OSError as exc:
            logger.debug("Cannot list %s: %s", root, exc)
            continue

        for entry in entries:
            if not entry.is_dir():
                continue
            vt, vl = _parse_s32ds_version(entry.name)
            if not vt:
                continue
            configurator = _find_configurator_dir(entry)
            if configurator is None:
                logger.debug(
                    "Skipping %s: no S32Trace configurator plugin found", entry
                )
                continue
            results.append(
                InstallInfo(
                    path=entry,
                    configurator_dir=configurator,
                    version_tuple=vt,
                    version_label=vl,
                )
            )

    results.sort(key=lambda i: i.version_tuple, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Explicit-path handling (YAML override)
# ---------------------------------------------------------------------------

def _explicit_install_info(install: Path) -> Optional[InstallInfo]:
    """Build an InstallInfo for a path explicitly set in the YAML config.

    Accepts two shapes the user might reasonably type:

    1. S32DS install root  -- e.g. ``C:\\NXP\\S32DS.3.6.9``
       (contains ``eclipse/plugins`` tree directly).
    2. eclipse subfolder   -- e.g. ``C:\\NXP\\S32DS.3.6.9\\eclipse``
       (the install root is the parent directory).

    Returns None when the path does not look like a valid S32DS install that
    ships the S32Trace configurator plugin.
    """
    install = Path(install)

    # Shape 1: user provided the S32DS root directly.
    configurator = _find_configurator_dir(install)
    if configurator is not None:
        vt, vl = _parse_s32ds_version(install.name)
        return InstallInfo(
            path=install,
            configurator_dir=configurator,
            version_tuple=vt,
            version_label=vl,
        )

    # Shape 2: user provided the eclipse subfolder.
    if install.name.lower() == "eclipse":
        parent = install.parent
        configurator = _find_configurator_dir(parent)
        if configurator is not None:
            vt, vl = _parse_s32ds_version(parent.name)
            return InstallInfo(
                path=parent,
                configurator_dir=configurator,
                version_tuple=vt,
                version_label=vl,
            )

    return None


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def select_install(
    yaml_install: str,
    *,
    discovered: Optional[list[InstallInfo]] = None,
) -> tuple[Optional[InstallInfo], str]:
    """Choose which install the server should use this session.

    Precedence:
      1. Explicit yaml_install path (whatever the user set in YAML).
         - If the path resolves to a valid install: reason = 'yaml_override'.
         - If the path does not resolve: reason = 'yaml_override_invalid'.
           The server does NOT silently fall back to auto-discovery in this
           case -- that would mask a configuration error.
      2. Newest auto-discovered install (highest version_tuple):
         reason = 'auto_newest'.
      3. Nothing found: reason = 'none_found'.

    Returns (InstallInfo | None, reason_string).
    """
    if yaml_install:
        info = _explicit_install_info(Path(yaml_install))
        if info is not None:
            return info, "yaml_override"
        return None, "yaml_override_invalid"

    if discovered is None:
        discovered = discover_installs()

    if discovered:
        return discovered[0], "auto_newest"

    return None, "none_found"
