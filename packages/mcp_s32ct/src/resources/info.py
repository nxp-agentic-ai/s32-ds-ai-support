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

"""S32 Configuration Tools MCP resources.

URI-scheme convention used by this server (aligned with the MCP draft spec
section Common URI Schemes):

* ``file://`` is used for resources that map to real filesystem artifacts of
  the S32 CT installation (the launcher's ``tools.ini``, the bundled HTML
  documentation directory, and the GTM use-case ``.mex`` templates).  The
  scheme advertises the filesystem-like nature of these resources to MCP
  clients, matching the spec's recommendation for filesystem resources.

* ``s32ct://`` is used only for synthetic resources that do *not* correspond
  to a single on-disk file - currently just the JSON snapshot of the server
  settings at ``s32ct://info``.

Note on the gateway namespace transform: FastMCP rewrites every resource URI
by inserting the mount namespace as the second path segment, so a server-side
URI ``file://files/tools.ini`` is exposed externally as
``file://nxp_s32ct/files/tools.ini``.  The transformed URI is still a valid
MCP identifier - the *server* interprets the path, not the OS filesystem
layer - so the spec-preferred ``file://`` scheme remains the right choice
even though the wire URI no longer dereferences directly on the host OS.

Resources exposed:

* ``s32ct://info``                                            (application/json)
* ``file://files/tools.ini``                                  (text/plain)
* ``file://files/documentation``                              (inode/directory)
* ``file://mcus/{mcu}/gtm/use-cases``                         (inode/directory)
* ``file://mcus/{mcu}/gtm/use-cases/{usecase}``               (application/xml)

All read handlers raise :class:`fastmcp.exceptions.ResourceError` on failure,
which FastMCP serializes as a JSON-RPC ``-32602`` error (``Invalid Params``)
as required by the MCP specification.
"""
import json
import logging
import re
from pathlib import Path

from fastmcp.exceptions import ResourceError

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import S32CTContext

_logger = logging.getLogger(MCP_SERVER_NAME)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Per RFC 3986 + MCP spec section "Security" ("Servers MUST sanitize file paths to prevent
# directory traversal attacks"), template parameters that become filesystem
# segments must be restricted to a safe character set.  This regex accepts only
# the characters used by real MCU / use-case names: ASCII letters, digits,
# underscore, hyphen, dot (but only as a separator, never leading), with a
# length cap to prevent DoS.
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]{0,127}$")


def _validate_segment(value: str, *, kind: str) -> str:
    """Reject any *value* that is unsafe to use as a filesystem path segment.

    Raises :class:`ResourceError` (mapped to JSON-RPC -32602 by FastMCP) if
    the segment contains path separators, parent-directory references, or
    characters outside the allow-list.  Returned unchanged when safe.
    """
    if not isinstance(value, str) or not _SAFE_SEGMENT.match(value):
        raise ResourceError(
            f"Invalid {kind} segment: {value!r}. "
            f"Must match ^[A-Za-z0-9_][A-Za-z0-9_.\\-]{{0,127}}$ "
            f"(no path separators, no '..', no leading '.')."
        )
    if ".." in value:
        # Belt-and-braces: regex already excludes '..' patterns, but make the
        # rejection explicit for auditability.
        raise ResourceError(f"Invalid {kind} segment: {value!r} (contains '..').")
    return value


def _gtm_usecases_dir(ctx: S32CTContext, mcu: str) -> Path:
    """Resolve the GTM ``use_cases_mexes`` directory for *mcu*.

    The exact PlatformSDK subfolder name is not fixed (e.g. ``PlatformSDK_S32ZE``
    for S32E/S32Z, ``PlatformSDK_S32K3`` for S32K3, ...), so we auto-detect any
    folder matching ``PlatformSDK_*`` under the MCU directory.
    """
    _validate_segment(mcu, kind="mcu")
    proc_dir = ctx.mcu_data_root / "processors" / mcu
    if not proc_dir.exists():
        raise ResourceError(
            f"MCU folder not found: {proc_dir}. "
            f"Check that '{mcu}' is installed under {ctx.mcu_data_root}/processors/."
        )
    platform_sdks = [p for p in proc_dir.iterdir() if p.is_dir() and p.name.startswith("PlatformSDK_")]
    if not platform_sdks:
        raise ResourceError(
            f"No PlatformSDK_* directory under {proc_dir}. "
            f"Found instead: {[p.name for p in proc_dir.iterdir() if p.is_dir()]}"
        )
    usecase_dir = platform_sdks[0] / "gtm" / "use_cases" / "use_cases_mexes"
    if not usecase_dir.exists():
        raise ResourceError(
            f"GTM use-cases directory not found: {usecase_dir}"
        )
    return usecase_dir


def _directory_listing(path: Path) -> str:
    """Build a plain-text ``ls -la``-like listing of *path* - one entry per line.

    Each line is ``<type>  <size>  <name>`` where ``<type>`` is ``DIR`` or
    ``FILE``. Used as the body of ``inode/directory`` resources.
    """
    if not path.exists():
        raise ResourceError(f"Directory not found: {path}")
    if not path.is_dir():
        raise ResourceError(f"Not a directory: {path}")
    lines = [f"# Directory listing: {path}", ""]
    for entry in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        kind = "DIR " if entry.is_dir() else "FILE"
        try:
            size = entry.stat().st_size if entry.is_file() else 0
        except OSError:
            size = -1
        lines.append(f"{kind}  {size:>12}  {entry.name}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_info_resource(server, config) -> None:
    """Register all s32ct MCP resources on *server*."""
    ctx = S32CTContext.from_settings(config.settings)

    # -- s32ct://info ------------------------------------------------------
    # Custom scheme: this is a synthetic JSON snapshot, not a real file.
    @server.resource(
        uri="s32ct://info",
        name="info",
        title="S32 Configuration Tools - server snapshot",
        description=(
            "JSON snapshot of the effective S32 CT MCP server settings: "
            "resolved installation_path, launcher, tools_ini, mcu_data_root, "
            "documentation_path, and timeout_s - each with an existence flag."
        ),
        mime_type="application/json",
    )
    def info() -> str:
        _logger.debug("s32ct://info requested")
        payload = {
            "mcp_server": "s32ct",
            "selection": {
                "distribution": ctx.distribution,
                "version": ctx.version_label,
                "reason": ctx.selection_reason,
            },
            "discovered_installs": [
                {
                    "path": str(i.path),
                    "distribution": i.distribution,
                    "version": i.version_label,
                }
                for i in ctx.discovered_installs
            ],
            "installation_path": {
                "path": str(ctx.install) if ctx.is_selected else "",
                "exists": ctx.is_selected and ctx.install.exists(),
            },
            "launcher": {
                "path": str(ctx.launcher) if ctx.is_selected else "",
                "exists": ctx.is_selected and ctx.launcher.exists(),
            },
            "tools_ini": {
                "path": str(ctx.tools_ini) if ctx.is_selected else "",
                "exists": ctx.is_selected and ctx.tools_ini.exists(),
            },
            "mcu_data_root": {
                "path": str(ctx.mcu_data_root) if ctx.mcu_data_root.parts else "",
                "exists": bool(ctx.mcu_data_root.parts) and ctx.mcu_data_root.exists(),
            },
            "documentation_path": {
                "path": str(ctx.documentation_path) if str(ctx.documentation_path) else None,
                "exists": (
                    ctx.documentation_path.exists()
                    if str(ctx.documentation_path)
                    else False
                ),
            },
            "timeout_s": ctx.timeout_s,
        }
        return json.dumps(payload, indent=2)

    # -- file://files/tools.ini -------------------------------------------
    # Real filesystem file; spec-recommended scheme for filesystem resources.
    @server.resource(
        uri="file://files/tools.ini",
        name="tools.ini",
        title="S32 Configuration Tools - tools.ini",
        description=(
            "Eclipse launcher configuration file for the S32 CT installation. "
            "Plain-text INI consumed by the headless CLI to locate the JVM, "
            "OSGi configuration, and bundle paths."
        ),
        mime_type="text/plain",
    )
    def tools_ini() -> str:
        _logger.debug("file://files/tools.ini requested")
        if not ctx.tools_ini.exists():
            raise ResourceError(f"tools.ini not found at {ctx.tools_ini}")
        try:
            return ctx.tools_ini.read_text(encoding="utf-8")
        except OSError as exc:
            raise ResourceError(f"Failed to read {ctx.tools_ini}: {exc}") from exc

    # -- file://files/documentation ---------------------------------------
    # Real filesystem directory; uses the spec's `inode/directory` MIME hint.
    @server.resource(
        uri="file://files/documentation",
        name="documentation",
        title="S32 Configuration Tools - bundled HTML documentation (directory)",
        description=(
            "Directory listing of the Eclipse-bundled HTML help pages shipped "
            "with the S32 CT installation. Individual files can be opened by "
            "the client directly via the filesystem."
        ),
        mime_type="inode/directory",
    )
    def documentation_dir() -> str:
        _logger.debug("file://files/documentation requested")
        if not str(ctx.documentation_path):
            raise ResourceError("documentation_path is not configured")
        return _directory_listing(ctx.documentation_path)

    # -- file://mcus/{mcu}/gtm/use-cases (template) -----------------------
    @server.resource(
        uri="file://mcus/{mcu}/gtm/use-cases",
        name="gtm-usecases",
        title="GTM use-cases folder for an MCU",
        description=(
            "Directory listing of the predefined GTM use-case .mex templates "
            "shipped under <mcu_data>/processors/<MCU>/PlatformSDK_*/gtm/"
            "use_cases/use_cases_mexes/. Use file://mcus/<mcu>/gtm/"
            "use-cases/<usecase> to read an individual use-case file."
        ),
        mime_type="inode/directory",
    )
    def gtm_usecases_listing(mcu: str) -> str:
        _logger.debug("file://mcus/%s/gtm/use-cases requested", mcu)
        usecase_dir = _gtm_usecases_dir(ctx, mcu)
        return _directory_listing(usecase_dir)

    # -- file://mcus/{mcu}/gtm/use-cases/{usecase} (template) -------------
    @server.resource(
        uri="file://mcus/{mcu}/gtm/use-cases/{usecase}",
        name="gtm-usecase-mex",
        title="GTM use-case .mex file",
        description=(
            "XML body of a predefined GTM use-case .mex template. The usecase "
            "parameter is the bare name without the '.mex' extension "
            "(e.g. 'atom_simple_pwm')."
        ),
        mime_type="application/xml",
    )
    def gtm_usecase_mex(mcu: str, usecase: str) -> str:
        _logger.debug("file://mcus/%s/gtm/use-cases/%s requested", mcu, usecase)
        # Reject path-separator / traversal / non-ASCII attacks before any I/O.
        _validate_segment(usecase, kind="usecase")
        usecase_dir = _gtm_usecases_dir(ctx, mcu)  # also validates `mcu`
        # Defensive: accept both with and without .mex suffix
        if usecase.endswith(".mex"):
            usecase_file = usecase_dir / usecase
        else:
            usecase_file = usecase_dir / f"{usecase}.mex"
        # Belt-and-braces path-confinement check: resolve the candidate and
        # confirm it really lives under the use-cases directory.
        try:
            resolved_file = usecase_file.resolve(strict=False)
            resolved_dir = usecase_dir.resolve(strict=False)
        except OSError as exc:
            raise ResourceError(f"Failed to resolve path {usecase_file}: {exc}") from exc
        if resolved_dir not in resolved_file.parents:
            raise ResourceError(
                f"Refusing to read {resolved_file}: outside use-cases directory "
                f"{resolved_dir}."
            )
        if not resolved_file.exists():
            available = sorted(p.stem for p in usecase_dir.glob("*.mex"))
            raise ResourceError(
                f"GTM use-case not found: {resolved_file}. "
                f"Available use-cases for {mcu}: {available}"
            )
        try:
            return resolved_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise ResourceError(f"Failed to read {resolved_file}: {exc}") from exc
