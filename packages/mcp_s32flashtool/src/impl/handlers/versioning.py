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

"""Version utils for the S32 Flash Tool MCP server.

This module is the single authoritative source for the version numbers the
server reports about itself and the tool it targets:

  * ``mcp_server_version``  - the Python package version (server binary/code).
  * ``target_tool_version`` - the S32 Flash Tool release this MCP was built and
                              validated against.

The manifest also carries a best-effort detection of the LOCALLY INSTALLED
S32 Flash Tool version. When that installed version differs from
``target_tool_version`` the caller is expected to log a warning and to prefer
serving documentation from the installed tool's local docs directory.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from packaging.version import InvalidVersion, Version

from nxp.mcp.s32flashtool.metadata.server import (
    MCP_SERVER_NAME,
    MCP_SERVER_VERSION,
)
from nxp.mcp.s32flashtool.impl.version_probe import s32flashtool_get_version_impl


__all__ = ["VersionManifest", "build_version_manifest"]

_logger = logging.getLogger(MCP_SERVER_NAME)

# The S32 Flash Tool release this MCP server was built and validated against.
# Bump this constant when the server is re-validated against a new tool release.
TARGET_TOOL_VERSION = "2.4.3"

# Validate TARGET_TOOL_VERSION at import time so a malformed constant fails fast
# rather than silently degrading every comparison to UNKNOWN at runtime.
try:
    _TARGET_TOOL_VERSION_PARSED = Version(TARGET_TOOL_VERSION)
except InvalidVersion as exc:
    raise ValueError(
        f"TARGET_TOOL_VERSION {TARGET_TOOL_VERSION!r} is not a valid PEP 440 version: {exc}"
    ) from exc


class VersionStatus(str, Enum):
    """How an installed version compares to the expected one.

    Subclasses ``str`` so instances are JSON-serializable and compare equal to
    their short string value (e.g. ``VersionStatus.MATCHES == "matches"``).
    Use these members everywhere instead of bare string literals so the
    comparison functions and their callers stay in sync.
    """

    MATCHES = "matches"
    NEWER = "newer"
    OLDER = "older"
    UNKNOWN = "unknown"


# Human-readable messages keyed by status. Kept separate from the status codes
# so the manifest carries a stable machine-readable value while logs stay
# descriptive.

_FT_MESSAGES = {
    VersionStatus.NEWER: "the installed tool is newer than expected",
    VersionStatus.OLDER: "the installed tool is older than expected",
    VersionStatus.MATCHES: "matches",
    VersionStatus.UNKNOWN: "unknown",
}


def _compare_tool_versions(expected: str, installed: Optional[str]) -> VersionStatus:
    """Classify the installed S32 Flash Tool version against the expected one.

    Returns one of VersionStatus.MATCHES, .NEWER, .OLDER or .UNKNOWN.

    Tool versions are dotted strings (e.g. ``"1.6.0"``, ``"2.4.3"``). They are
    parsed with :class:`packaging.version.Version`, which orders components
    numerically (so ``"2.3.1" < "10.1.2"``), treats trailing zeros as equal
    (so ``"1.6" == "1.6.0"``), and correctly handles pre-release / build
    suffixes such as ``"1.3.a4"``. When the installed value is not a valid
    version string the comparison falls back to plain string equality. The
    expected value is always valid because it is checked at import time.
    """
    if not installed:
        return VersionStatus.UNKNOWN

    try:
        ins_v = Version(installed)
        exp_v = Version(expected)  # Should be always valid due to the import-time check above.
    except InvalidVersion:
        # Installed version is not parseable; fall back to string equality.
        return VersionStatus.MATCHES if installed == expected else VersionStatus.UNKNOWN
    
    if ins_v == exp_v:
        return VersionStatus.MATCHES
    return VersionStatus.NEWER if ins_v > exp_v else VersionStatus.OLDER


# Regex to pull a dotted version out of an S32 Flash Tool banner line, e.g.
# "S32 Flash Tool v1.6.0" or "S32FlashTool 1.5.2 (build ...)".
_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)")


def parse_tool_version(banner: str) -> Optional[str]:
    """Extract a dotted version string from an S32 Flash Tool banner line like
    `S32 Flash Tool 2.4.3. Build 260724. Copyright 2019 - 2026 NXP`.

    Returns the first dotted version token found (e.g. "1.6.0"), or ``None``
    when the banner is empty or contains no recognizable version.
    """
    if not banner:
        return None
    match = _VERSION_RE.search(banner)
    return match.group(1) if match else None


@dataclass(slots=True)
class InstalledToolInfo:
    """Best-effort description of the locally installed S32 Flash Tool."""

    detected: bool = False
    version: Optional[str] = None
    installation_path: Optional[str] = None
    docs_path: Optional[str] = None
    # Machine-readable status code (enum value, e.g. "matches"/"newer"/"older").
    # Consumers (including AI agents) should branch on this stable value.
    tool_status: Optional[VersionStatus] = None
    # Human-readable explanation derived from tool_status via _FT_MESSAGES.
    # Never set this independently; use set_tool_status() so the two stay in sync.
    tool_status_message: Optional[str] = None
    banner: Optional[str] = None

    def set_tool_status(self, status: VersionStatus) -> None:
        """Set the status code and derive its human-readable message together.

        Single source of truth: the message is always ``_FT_MESSAGES[status]``
        so ``tool_status`` and ``tool_status_message`` can never drift apart.
        """
        self.tool_status = status
        self.tool_status_message = _FT_MESSAGES[status]



@dataclass(slots=True)
class VersionManifest:
    """The structured version manifest reported by ``get_runtime_info``."""

    mcp_server_name: str = MCP_SERVER_NAME
    mcp_server_version: str = MCP_SERVER_VERSION
    target_tool_version: str = TARGET_TOOL_VERSION
    installed_tool: InstalledToolInfo = field(default_factory=InstalledToolInfo)

    def to_dict(self) -> dict[str, Any]:
        """Return the manifest as a plain JSON-serializable dict."""
        return asdict(self)


def resolve_installed_docs_dir(installation_path: Optional[str]) -> Optional[Path]:
    """Return the installed S32 Flash Tool local docs directory if it exists.

    The S32 Flash Tool ships its documentation under ``<install>/doc``. The
    docs path is normalized with a non-strict resolve() and then checked to be
    lexically under the resolved installation root. NOTE: because resolve() is
    non-strict here, this check does NOT follow symlink targets for a doc
    directory that is itself a symlink, so it is a best-effort normalization
    rather than a hard symlink-escape guarantee. (Contrast api_client_launcher
    .launch_gui, which uses strict=True to actually resolve symlink targets
    before its containment check.)
    """
    if not installation_path:
        return None
    try:
        base = Path(installation_path).resolve(strict=False)
        docs = (base / "doc").resolve(strict=False)
        # Lexical containment check under base. This is best-effort only:
        # with strict=False, resolve() does not follow a symlinked doc target,
        # so this does not fully guard against symlink escapes (see docstring).
        docs.relative_to(base)
    except (ValueError, OSError):
        return None
    return docs if docs.is_dir() else None


async def detect_installed_tool(installation_path: Optional[str]) -> InstalledToolInfo:
    """Detect the locally installed S32 Flash Tool version (best effort).

    Runs ``S32FlashTool CLI executable`` with minimal arguments (its version-banner mode) via
    the existing implementation helper and parses the banner. Never raises -
    on any failure it returns ``InstalledToolInfo(detected=False)``.
    """
    info = InstalledToolInfo(installation_path=installation_path or None)
    if not installation_path:
        return info

    docs_dir = resolve_installed_docs_dir(installation_path)
    info.docs_path = str(docs_dir) if docs_dir is not None else None

    try:
        # Returns something like:
        #   S32 Flash Tool 2.4.3. Build 260724. Copyright 2019 - 2026 NXP
        result = await s32flashtool_get_version_impl(installation_path)
        banner = ""
        if isinstance(result, dict):
            banner = str(result.get("data") or "")
        info.banner = banner or None
        version = parse_tool_version(banner)
        if version:
            info.detected = True
            info.version = version
            info.set_tool_status(_compare_tool_versions(TARGET_TOOL_VERSION, version))

    except Exception:
        # Detection is best-effort: log and return an empty info rather than
        # propagating. This path is covered by a dedicated test.
        _logger.debug(
            "Installed S32 Flash Tool version detection failed for path %r "
            "(this is expected when no installation is present)",
            installation_path,
            exc_info=True,
        )

    return info


async def build_version_manifest(
    installation_path: Optional[str] = None,
) -> VersionManifest:
    """Assemble the full :class:`VersionManifest`.

    When ``installation_path`` is provided, the installed tool version is
    detected and, if it differs from ``target_tool_version``, a warning is
    logged. Callers that serve documentation should prefer the installed
    tool's local docs directory in that case (see
    :func:`resolve_installed_docs_dir`).
    """
    manifest = VersionManifest(
        installed_tool=await detect_installed_tool(installation_path),
    )

    installed = manifest.installed_tool
    if installed.detected and installed.tool_status != VersionStatus.MATCHES:

        _logger.warning(
            "Installed S32 Flash Tool version %s differs from target_tool_version %s. "
            "Preferring documentation from the installed tool docs directory: %s",
            installed.version,
            manifest.target_tool_version,
            installed.docs_path or "<not found>",
        )

    return manifest
