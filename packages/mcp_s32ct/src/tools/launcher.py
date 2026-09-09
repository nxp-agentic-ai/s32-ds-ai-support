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

"""Shared S32 Configuration Tools headless-CLI plumbing.

This module hosts the implementation functions (``*_impl``) and the helpers
that build / execute the S32 CT launcher command-line. Every tool module in
this package ultimately delegates here so that the launcher prefix, argument
ordering, GetValue parsing, retry-on-missing-workspace logic, and existence
checks are implemented exactly once.

Per-call CLI arguments (``s32ct_launcher`` / ``launcher_ini``) still win
over the per-server defaults supplied by the ``S32CTSettings`` dataclass.

S32 Configuration Tools is delivered in two distributions that share the
same headless CLI grammar (same ``-application
com.nxp.swtools.framework.application``, same ``-HeadlessTool``, same
export verbs):

* ``desktop``           - standalone install; launcher pair
  ``toolsc.exe``, launcher .ini ``tools.ini``, MCU data at
  ``<install>/mcu_data``. (S32CT does not ship a separate console-
  twin executable -- the product doc uses plain ``toolsc.exe`` with
  ``--launcher.ini`` to get headless console behavior; see
  ``resources/support/help/en/topics/command_line_execution.html``
  inside ``com.nxp.swtools.doc.uct_*.jar``.)

* ``integrated_s32ds``  - shipped as an Eclipse plugin set inside an S32
  Design Studio install. Launcher binary is ``s32dsc.exe``,
  launcher .ini ``s32ds.ini``, MCU data bundled at
  ``<S32DS_install>/eclipse/mcu_data``.

The server auto-discovers whichever installs are present at startup and
selects one when the YAML config does not pin a specific
``installation_path``.
"""
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME

logger = logging.getLogger(MCP_SERVER_NAME)


# ---------------------------------------------------------------------------
# Distribution discovery
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class InstallInfo:
    """One discovered S32CT install on the host filesystem."""

    path: Path
    distribution: str               # "desktop" | "integrated_s32ds"
    launcher: Path
    launcher_ini: Path
    mcu_data_root: Path
    version_tuple: tuple[int, ...]
    version_label: str


def _default_scan_roots() -> list[Path]:
    """Default scan roots, in order. Non-existent entries are skipped."""
    roots: list[Path] = [Path(r"C:\NXP")]
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        val = os.environ.get(env_var)
        if val:
            roots.append(Path(val) / "NXP")
    roots.append(Path("/opt/nxp"))  # Linux conventional location
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        roots.append(Path(home) / "NXP")
    return roots


_DESKTOP_VERSION_RE = re.compile(
    r"^S32ConfigTools\.(?P<year>\d{4})\.R(?P<release>\d+)(?:\.(?P<patch>\d+))?$",
    re.IGNORECASE,
)
_S32DS_VERSION_RE = re.compile(
    r"^S32DS\.(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?$",
    re.IGNORECASE,
)


def _parse_desktop_version(dirname: str) -> tuple[tuple[int, ...], str]:
    m = _DESKTOP_VERSION_RE.match(dirname)
    if not m:
        return (), ""
    year = int(m["year"])
    release = int(m["release"])
    patch = int(m["patch"] or 0)
    label = f"{year}.R{release}" + (f".{patch}" if patch else "")
    return (year, release, patch), label


def _parse_s32ds_version(dirname: str) -> tuple[tuple[int, ...], str]:
    m = _S32DS_VERSION_RE.match(dirname)
    if not m:
        return (), ""
    major = int(m["major"])
    minor = int(m["minor"])
    patch = int(m["patch"] or 0)
    label = f"{major}.{minor}" + (f".{patch}" if patch else "")
    return (major, minor, patch), label

def discover_installs(roots: Optional[Iterable[Path]] = None) -> list[InstallInfo]:
    """Probe the filesystem and return every S32CT install found.

    The scan is shallow (one directory level under each root) and read-only:
    each candidate must have both the launcher binary and the .ini file on
    disk before it is reported. Non-existent roots are silently skipped.
    Results are sorted by distribution, then newest version first.
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

            # Desktop variant: <root>/S32ConfigTools.<ver>/{toolsc.exe,tools.ini}
            # Per the product doc (com.nxp.swtools.doc.uct_*.jar,
            # resources/support/help/en/topics/command_line_execution.html)
            # the launcher is plain ``toolsc.exe`` and the MCU data root is
            # <install>/mcu_data -- not %ProgramData%/NXP/mcu_data_*, which
            # is a separate / parallel install data tree from older versions.
            vt, vl = _parse_desktop_version(entry.name)
            if vt:
                launcher = entry / "toolsc.exe"
                launcher_ini = entry / "tools.ini"
                if launcher.is_file() and launcher_ini.is_file():
                    results.append(InstallInfo(
                        path=entry,
                        distribution="desktop",
                        launcher=launcher,
                        launcher_ini=launcher_ini,
                        mcu_data_root=entry / "mcu_data",
                        version_tuple=vt,
                        version_label=vl,
                    ))
                continue

            # Integrated variant: <root>/S32DS.<ver>/eclipse/{s32dsc.exe,s32ds.ini}.
            # The PDF documents s32dsc.exe as the canonical launcher; the
            # console-twin s32dsc.exe is only mentioned in a CI recipe
            # (`copy /Y s32dsc.exe s32dsc.exe`) and is not a discovery target.
            vt, vl = _parse_s32ds_version(entry.name)
            if vt:
                eclipse = entry / "eclipse"
                launcher = eclipse / "s32dsc.exe"
                launcher_ini = eclipse / "s32ds.ini"
                if launcher.is_file() and launcher_ini.is_file():
                    results.append(InstallInfo(
                        path=eclipse,
                        distribution="integrated_s32ds",
                        launcher=launcher,
                        launcher_ini=launcher_ini,
                        mcu_data_root=eclipse / "mcu_data",
                        version_tuple=vt,
                        version_label=vl,
                    ))

    results.sort(key=lambda i: (i.distribution, tuple(-v for v in i.version_tuple)))
    return results


def _explicit_install_info(install: Path) -> Optional[InstallInfo]:
    """Build an :class:`InstallInfo` for an explicitly configured path.

    Accepts three shapes the user might reasonably type into the YAML:

    1. A desktop install, e.g. ``C:\\NXP\\S32ConfigTools.2026.R1.9``
       (contains ``toolsc.exe`` + ``tools.ini`` directly).
    2. An S32DS install root, e.g. ``C:\\NXP\\S32DS.3.6.5`` (the path the
       user sees in the installer / in their filesystem) -- we descend into
       ``./eclipse`` to find the launcher pair.
    3. The ``eclipse`` subfolder of an S32DS install, e.g.
       ``C:\\NXP\\S32DS.3.6.5\\eclipse`` (the actual launcher folder;
       useful for advanced users or custom layouts).

    Returns ``None`` if none of the three shapes is recognized. Used to
    honour the YAML override even when the path doesn't sit under a
    standard scan root.
    """
    install = Path(install)

    # Shape 1: desktop install -- <install>/toolsc.exe + <install>/tools.ini.
    tools_exe = install / "toolsc.exe"
    tools_ini = install / "tools.ini"
    if tools_exe.is_file() and tools_ini.is_file():
        vt, vl = _parse_desktop_version(install.name)
        return InstallInfo(
            path=install,
            distribution="desktop",
            launcher=tools_exe,
            launcher_ini=tools_ini,
            mcu_data_root=install / "mcu_data",
            version_tuple=vt,
            version_label=vl,
        )

    # Shape 3: integrated_s32ds, eclipse folder -- <install>/s32dsc.exe +
    # <install>/s32ds.ini. The version label is read from the *parent*
    # directory name (i.e. ``S32DS.3.6.5``).
    s32ds_exe = install / "s32dsc.exe"
    s32ds_ini = install / "s32ds.ini"
    if s32ds_exe.is_file() and s32ds_ini.is_file():
        vt, vl = _parse_s32ds_version(install.parent.name)
        # Fallback: if the parent doesn't carry the version (custom layout),
        # try the eclipse folder's own name.
        if not vt:
            vt, vl = _parse_s32ds_version(install.name)
        return InstallInfo(
            path=install,
            distribution="integrated_s32ds",
            launcher=s32ds_exe,
            launcher_ini=s32ds_ini,
            mcu_data_root=install / "mcu_data",
            version_tuple=vt,
            version_label=vl,
        )

    # Shape 2: S32DS install root -- the user-friendly path the installer
    # advertises. Descend into ./eclipse and re-check the integrated layout.
    eclipse = install / "eclipse"
    s32ds_exe = eclipse / "s32dsc.exe"
    s32ds_ini = eclipse / "s32ds.ini"
    if s32ds_exe.is_file() and s32ds_ini.is_file():
        vt, vl = _parse_s32ds_version(install.name)
        return InstallInfo(
            path=eclipse,
            distribution="integrated_s32ds",
            launcher=s32ds_exe,
            launcher_ini=s32ds_ini,
            mcu_data_root=eclipse / "mcu_data",
            version_tuple=vt,
            version_label=vl,
        )

    return None


def select_install(
    yaml_install: str,
    *,
    discovered: Optional[list[InstallInfo]] = None,
) -> tuple[Optional[InstallInfo], str]:
    """Choose which install the server should use this session.

    Precedence:
      1. Explicit ``yaml_install`` path (whatever the user set in YAML).
      2. Newest discovered ``desktop`` install.
      3. Newest discovered ``integrated_s32ds`` install.

    Returns ``(install_info, reason)``. ``install_info`` is ``None`` when no
    install is available; the server still starts and individual tool calls
    fail with an actionable error.
    """
    if yaml_install:
        info = _explicit_install_info(Path(yaml_install))
        if info is not None:
            return info, "yaml_override"
        # YAML pointed at something that does not look like a real install.
        # Do not silently auto-discover -- that would mask a config error.
        return None, "yaml_override_invalid"

    if discovered is None:
        discovered = discover_installs()

    desktops = [i for i in discovered if i.distribution == "desktop"]
    if desktops:
        desktops.sort(key=lambda i: i.version_tuple, reverse=True)
        return desktops[0], "auto_desktop_newest"

    integrated = [i for i in discovered if i.distribution == "integrated_s32ds"]
    if integrated:
        integrated.sort(key=lambda i: i.version_tuple, reverse=True)
        return integrated[0], "auto_integrated_newest"

    return None, "none_found"

# Eclipse application id of the S32 Configuration Tools framework.
S32CT_APPLICATION = "com.nxp.swtools.framework.application"

# NOTE: DCA (Device Configuration Area) and DCF (Device Configuration Format)
# are NOT separate headless tools. The S32CT DCD plugin registers a single
# headless tool id="DCD" (see com.nxp.swtools.dcd/plugin.xml, product id=DCD,
# commandline_app=com.nxp.swtools.dcd.CmdApplication). That one CmdApplication
# drives DCD, DCF and DCA; the active variant is chosen automatically from the
# selected processor (DCDUtils.getActiveToolAndController ->
# isDCDProcessorSelected / isDCFProcessorSelected / isDCAProcessorSelected).
# So DCA/DCF are reached with -HeadlessTool DCD and are intentionally absent
# from this set.
ALLOWED_TOOLS: set[str] = {
    "Pins", "Clocks", "Peripherals", "DCD", "IVT", "eFUSE", "GTM", "QuadSPI", "FFC",
}

ALLOWED_EXPORTS: set[str] = {
    "ExportAll", "ExportSrc", "ExportHTML", "ExportCSV", "ExportRegisters", "ExportMEX",
    # IVT / DCD / QuadSPI binary-style exports
    "ExportBin", "ExportC", "ExportBlob", "ExportAB", "ExportPointers", "ExportDDRC", "ExportFssFw",
    # eFUSE

    "ExportConfig", "ExportELF",
    # FFC
    "ExportARXML", "ExportJSON",
}
ALLOWED_FFC_FILE_TYPES: set[str] = {"all", "Fss_Rem_Pm", "Fss_Btm"}
ALLOWED_IVT_UPDATE_FILEPATHS: set[str] = {"relativeToCurrentMex", "absolute", "keepExisting"}
ALLOWED_IVT_FILTERS: set[str] = {"UnresolvedCustomPointers", "All"}


# ---------------------------------------------------------------------------
# Server-config bridge
# ---------------------------------------------------------------------------
class S32CTContext:
    """Snapshot of the effective S32 CT defaults derived from server settings.

    Built once at server startup; captured in every tool-function closure.
    Values flow into every call as fallbacks; explicit per-call arguments
    (``s32ct_launcher`` / ``launcher_ini`` / ``timeout_s``) still take
    precedence.

    ``launcher`` and ``tools_ini`` are derived from the install selected at
    startup. When the YAML config does not pin an ``installation_path`` the
    selection is made by :func:`select_install` on the host's auto-discovered
    installs; otherwise the YAML path wins. The selected install's
    distribution (``"desktop"`` vs ``"integrated_s32ds"``) is captured on
    the context so resources / tools can surface it.

    ``documentation_path`` is informational only - surfaced through the
    ``status`` tool and the ``s32ct://info`` resource so an integrator can
    wire it into one of ``mcp_knowledge``'s ``corpora[].dirs`` lists. It is never
    consumed by the S32 CT launcher itself.
    """

    __slots__ = (
        "install", "launcher", "tools_ini", "mcu_data_root",
        "documentation_path", "timeout_s",
        "distribution", "version_label",
        "selection_reason", "discovered_installs",
        "is_selected",
    )

    def __init__(
        self,
        install: Path,
        launcher: Path,
        tools_ini: Path,
        mcu_data_root: Path,
        documentation_path: Path,
        timeout_s: int,
        *,
        distribution: str = "unknown",
        version_label: str = "",
        selection_reason: str = "yaml_override",
        discovered_installs: tuple[InstallInfo, ...] = (),
        is_selected: bool = True,
    ) -> None:
        self.install = install
        self.launcher = launcher
        self.tools_ini = tools_ini
        self.mcu_data_root = mcu_data_root
        self.documentation_path = documentation_path
        self.timeout_s = timeout_s
        self.distribution = distribution
        self.version_label = version_label
        self.selection_reason = selection_reason
        self.discovered_installs = discovered_installs
        self.is_selected = is_selected

    @classmethod
    def from_settings(cls, settings) -> "S32CTContext":
        # Discover once at startup; cache the list on the context so
        # downstream resources and tools can surface it without re-scanning.
        discovered = discover_installs()
        selected, reason = select_install(settings.installation_path or "", discovered=discovered)

        if selected is not None:
            install = selected.path
            launcher = selected.launcher
            tools_ini = selected.launcher_ini
            distribution = selected.distribution
            version_label = selected.version_label
            # Explicit YAML mcu_data_root wins; otherwise use whatever the
            # selected install advertises.
            mcu_data_root = (
                Path(settings.mcu_data_root)
                if settings.mcu_data_root
                else selected.mcu_data_root
            )
        else:
            # No install resolved. Keep paths as sentinel empty Path("")
            # values; `is_selected=False` flags this state so resources /
            # tools can report it without calling .exists() on phantom paths.
            install = Path("")
            launcher = Path("")
            tools_ini = Path("")
            distribution = "unknown"
            version_label = ""
            mcu_data_root = Path(settings.mcu_data_root) if settings.mcu_data_root else Path("")
            logger.warning(
                "No S32 Configuration Tools install resolved (reason=%s). "
                "Set s32ct.settings.installation_path in the YAML, or install "
                "S32CT under one of the standard scan roots.",
                reason,
            )

        documentation_path = (
            Path(settings.documentation_path) if settings.documentation_path else Path("")
        )
        timeout_s = int(settings.timeout_s or 600)
        return cls(
            install,
            launcher,
            tools_ini,
            mcu_data_root,
            documentation_path,
            timeout_s,
            distribution=distribution,
            version_label=version_label,
            selection_reason=reason,
            discovered_installs=tuple(discovered),
            is_selected=(selected is not None),
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _resolve_launcher(
    ctx: S32CTContext,
    launcher: Optional[str],
    tools_ini: Optional[str],
) -> tuple[Path, Path, str]:
    """Resolve effective launcher + ini, and report which distribution they
    belong to so :func:`_build_prefix` can emit the right CLI form.

    Per-call overrides (``launcher`` / ``tools_ini``) still win over the
    server defaults captured on ``ctx``. When the caller supplies either
    override, we infer the distribution from the launcher binary's name
    (``toolsc.exe`` -> desktop, ``s32dsc.exe`` -> integrated_s32ds,
    otherwise fall back to whatever ``ctx`` reports).
    """
    lp = Path(launcher) if launcher else ctx.launcher
    ip = Path(tools_ini) if tools_ini else ctx.tools_ini
    if not lp.exists():
        raise FileNotFoundError(f"S32CT launcher not found: {lp}")
    if not ip.exists():
        raise FileNotFoundError(f"S32CT tools.ini not found: {ip}")

    if launcher or tools_ini:
        # Per-call override -- pick distribution by launcher name.
        name = lp.name.lower()
        if name == "toolsc.exe":
            distribution = "desktop"
        elif name == "s32dsc.exe":
            distribution = "integrated_s32ds"
        else:
            distribution = ctx.distribution or "unknown"
    else:
        distribution = ctx.distribution or "unknown"

    return lp, ip, distribution


def _session_workspace() -> Path:
    """Per-process workspace directory used as the default ``-data`` value
    on the integrated_s32ds variant.

    The S32 Configuration Tools docs explicitly require ``-data
    <workspace_location>`` on the S32DS-integrated variant (otherwise the
    Eclipse launcher blocks on the interactive workspace-selection dialog).
    Callers can still override per call via ``-data`` in ``extra_args`` or
    by passing an explicit workspace argument upstream.

    We pin the workspace under ``%LOCALAPPDATA%\\S32CT-MCP\\workspace``
    (Windows) or ``$HOME/.cache/s32ct-mcp/workspace`` (POSIX) so it
    survives across calls and the Eclipse data folders are not recreated
    every invocation. Created on first use; never cleaned up automatically.
    """
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("HOME") or tempfile.gettempdir()
    base = Path(local)
    if os.name == "nt":
        ws = base / "S32CT-MCP" / "workspace"
    else:
        ws = base / ".cache" / "s32ct-mcp" / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def _build_prefix(launcher: Path, tools_ini: Path, distribution: str = "desktop") -> list[str]:
    """Build the launcher prefix in the form documented for S32 Configuration
    Tools (``com.nxp.swtools.doc.uct_*.jar`` -> ``command_line_execution.html``).

    Both supported distributions share the same prefix skeleton; only the
    launcher binary, the ``launcher.ini`` path, and the presence of
    ``-data <workspace>`` differ.

    Desktop (standalone S32CT):

        toolsc.exe -noSplash \
                  --launcher.ini <tools.ini> \
                  -application com.nxp.swtools.framework.application \
                  -consoleLog \
                  <tool commands>

    Integrated (S32CT bundled in S32 Design Studio):

        s32dsc.exe -noSplash \
                  --launcher.ini <s32ds.ini> \
                  -application com.nxp.swtools.framework.application \
                  -consoleLog \
                  -data <workspace> \
                  <tool commands>

    ``-consoleLog`` is always included so stdout flows back to the caller --
    this matches the product doc's recommended form for headless usage.

    ``-data <workspace>`` is injected only for the integrated variant. The
    Eclipse launcher otherwise blocks on the interactive workspace-selection
    dialog (verified empirically). The standalone product manages its own
    workspace internally. The workspace path is the stable per-host directory
    returned by :func:`_session_workspace`; callers can override per call by
    passing ``data_dir`` to the upstream tool wrapper.
    """
    cmd = [
        str(launcher),
        "-noSplash",
        "--launcher.ini", str(tools_ini),
        "-application", S32CT_APPLICATION,
        "-consoleLog",
    ]
    if distribution == "integrated_s32ds":
        cmd += ["-data", str(_session_workspace())]
    return cmd

def _run(cmd: list[str], timeout_s: int = 600) -> tuple[int, str, str]:
    logger.info("S32CT cmd: %s", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    return cp.returncode, cp.stdout or "", cp.stderr or ""


def _truncate(s: str, n: int = 1500) -> str:
    s = s.strip()
    return s if len(s) <= n else s[:n] + " ...(truncated)"


def _resolve_platform_sdk_dir(mcu_dir: Path, override: Optional[str]) -> Path:
    """Return the SDK folder under ``mcu_dir`` that hosts the GTM use-cases.

    Resolution order:

    1. ``override`` (explicit caller request) - used as-is if it exists.
    2. The single ``PlatformSDK_*`` subfolder, if exactly one is present.
    3. The single ``amp_sdk1_*`` subfolder (AMP SDK), if present.
    4. Any subfolder that contains ``gtm/use_cases/use_cases_mexes``.

    Raises ``FileNotFoundError`` (or ``RuntimeError`` for ambiguous cases)
    listing the sibling folders that *were* found, so the caller can
    disambiguate via the ``platform_sdk_dir`` argument.
    """
    if override:
        candidate = mcu_dir / override
        if not candidate.exists():
            raise FileNotFoundError(f"platform_sdk_dir not found: {candidate}")
        return candidate

    platform = sorted(p for p in mcu_dir.glob("PlatformSDK_*") if p.is_dir())
    if len(platform) == 1:
        return platform[0]
    if len(platform) > 1:
        names = ", ".join(p.name for p in platform)
        raise RuntimeError(
            f"Multiple PlatformSDK_* folders under {mcu_dir}: [{names}]. "
            f"Specify platform_sdk_dir explicitly."
        )

    amp = sorted(p for p in mcu_dir.glob("amp_sdk1_*") if p.is_dir())
    if len(amp) == 1:
        return amp[0]
    if len(amp) > 1:
        names = ", ".join(p.name for p in amp)
        raise RuntimeError(
            f"Multiple amp_sdk1_* folders under {mcu_dir}: [{names}]. "
            f"Specify platform_sdk_dir explicitly."
        )

    gtm_hosts = sorted(
        p for p in mcu_dir.glob("*")
        if p.is_dir() and (p / "gtm" / "use_cases" / "use_cases_mexes").exists()
    )
    if len(gtm_hosts) == 1:
        return gtm_hosts[0]
    if len(gtm_hosts) > 1:
        names = ", ".join(p.name for p in gtm_hosts)
        raise RuntimeError(
            f"Multiple SDK folders under {mcu_dir} contain GTM use-cases: "
            f"[{names}]. Specify platform_sdk_dir explicitly."
        )

    siblings = sorted(p.name for p in mcu_dir.glob("*") if p.is_dir())
    raise FileNotFoundError(
        f"No SDK folder with GTM use-cases under {mcu_dir}. "
        f"Found subfolders: {siblings}"
    )


def _parse_get_value_table(stdout: str, ids: list[str]) -> dict[str, str]:
    """Best-effort parsing of the launcher's ``-GetValue`` output.

    Supports several formats observed across S32CT versions:

    1. Bordered table::

         | id   | value |

    2. Pipe-separated without leading/trailing pipes::

         id | value

    3. ``key = value`` / ``key : value`` lines.

    4. Whitespace-aligned table (``id   value``).
    """
    if not ids:
        return {}
    found: dict[str, str] = {}
    id_set = set(ids)

    def _maybe(k: str, v: str) -> None:
        k = k.strip()
        v = v.strip()
        if k in id_set and k not in found and v:
            found[k] = v

    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "|" in line:
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]
            if len(cells) == 2:
                _maybe(cells[0], cells[1])
                if cells[0] in found:
                    continue
            elif len(cells) >= 3:
                if cells[0] in id_set:
                    _maybe(cells[0], cells[1])
                if cells[0] in found:
                    continue
        for sep in (" = ", "=", " : ", ":"):
            if sep in line:
                k, _, v = line.partition(sep)
                _maybe(k, v)
                if k.strip() in found:
                    break
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0] in id_set and parts[0] not in found:
            _maybe(parts[0], parts[1])
    return found


# ---------------------------------------------------------------------------
# Implementations (importable + testable)
# ---------------------------------------------------------------------------
def get_version_impl(
    ctx: S32CTContext,
    installation_path: Optional[str] = None,
    s32ct_launcher: Optional[str] = None,
) -> str:
    install = Path(installation_path) if installation_path else ctx.install
    # Default to the launcher already resolved on the context: that is the
    # right binary for whichever distribution was selected at startup
    # (``toolsc.exe`` for desktop, ``s32dsc.exe`` for integrated_s32ds).
    # Fall back to ``toolsc.exe`` only when the caller passes an explicit
    # ``installation_path`` without an accompanying launcher override.
    if s32ct_launcher:
        launcher = Path(s32ct_launcher)
    elif installation_path:
        launcher = install / "toolsc.exe"
    else:
        launcher = ctx.launcher

    if not install.exists():
        return f"S32 Configuration Tools not found at the configured path '{install}'"

    version: Optional[str] = None
    name = "S32 Configuration Tools"

    # 1) .eclipseproduct (key=value file with name/version/id)
    eclipseproduct = install / ".eclipseproduct"
    if eclipseproduct.exists():
        try:
            for line in eclipseproduct.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip().lower(), v.strip()
                    if k == "version" and v:
                        version = v
                    elif k == "name" and v:
                        name = v
        except Exception:
            logger.exception("read .eclipseproduct failed")

    # 2) Install-dir name fallback (e.g. S32ConfigTools.2026.R1.9)
    if not version:
        m = re.search(r"(\d{4}\.[A-Za-z0-9.]+)$", install.name)
        if m:
            version = m.group(1)

    # 3) Release-notes first line
    if not version:
        rn = install / "ReleaseNotes.txt"
        if rn.exists():
            try:
                first = rn.read_text(encoding="utf-8", errors="ignore").splitlines()[0].strip()
                if first:
                    version = first
            except Exception:
                pass

    version = version or "unknown"
    launcher_note = f" (launcher: {launcher.name})" if launcher.exists() else " (launcher missing)"
    return f"{name} {version} at {install}{launcher_note}"


def generate_code_impl(
    ctx: S32CTContext,
    project_path: str,
    tool_name: str,
    output_dir: str,
    export_kind: str = "ExportAll",
    enable_if_disabled: bool = True,
    sdk_version: Optional[str] = None,
    s32ct_launcher: Optional[str] = None,
    launcher_ini: Optional[str] = None,
    timeout_s: Optional[int] = None,
) -> str:
    if tool_name not in ALLOWED_TOOLS:
        return f"Invalid tool_name '{tool_name}'. Allowed: {sorted(ALLOWED_TOOLS)}"
    if export_kind not in ALLOWED_EXPORTS:
        return f"Invalid export_kind '{export_kind}'. Allowed: {sorted(ALLOWED_EXPORTS)}"

    proj = Path(project_path)
    if not proj.exists() or proj.suffix.lower() != ".mex":
        return f"project_path must be an existing .mex file. Got: {proj}"

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    launcher, tools_ini, distribution = _resolve_launcher(ctx, s32ct_launcher, launcher_ini)
    cmd = _build_prefix(launcher, tools_ini, distribution)
    cmd += ["-Load", str(proj)]
    if sdk_version:
        cmd += ["-SDKVersion", sdk_version]
    cmd += ["-HeadlessTool", tool_name]
    if enable_if_disabled:
        cmd += ["-Enable"]
    cmd += [f"-{export_kind}", str(out)]

    effective_timeout = int(timeout_s) if timeout_s is not None else ctx.timeout_s
    try:
        rc, so, se = _run(cmd, timeout_s=effective_timeout)
    except subprocess.TimeoutExpired:
        return f"Code generation timed out after {effective_timeout}s for tool '{tool_name}'"

    if rc == 0:
        return (
            f"Code generation succeeded for tool '{tool_name}' "
            f"({export_kind} -> {out})."
        )
    msg = (
        f"Code generation failed for tool '{tool_name}' (exit code {rc}).\n"
        f"stderr: {_truncate(se)}\n"
        f"stdout: {_truncate(so, 500)}"
    )
    if "instance data location has not been specified" in (se + so).lower():
        msg += "\nHint: try adding `-data <workspace>` to the launcher arguments."
    return msg


def gtm_create_from_usecase_impl(
    ctx: S32CTContext,
    mcu: str,
    sdk_version: str,
    usecase: str,
    output_dir: str,
    mcu_data_root: Optional[str] = None,
    platform_sdk_dir: Optional[str] = None,
    usecase_mex_path: Optional[str] = None,
    export_kind: str = "ExportAll",
    gtm_codegen: bool = True,
    config_name: Optional[str] = None,
    s32ct_launcher: Optional[str] = None,
    launcher_ini: Optional[str] = None,
    timeout_s: Optional[int] = None,
) -> str:
    if export_kind not in ALLOWED_EXPORTS:
        return f"Invalid export_kind '{export_kind}'. Allowed: {sorted(ALLOWED_EXPORTS)}"

    # 1) Resolve use-case .mex
    if usecase_mex_path:
        uc_mex = Path(usecase_mex_path)
    else:
        root = Path(mcu_data_root) if mcu_data_root else ctx.mcu_data_root
        mcu_dir = root / "processors" / mcu
        if not mcu_dir.exists():
            available = sorted(p.name for p in (root / "processors").glob("*") if p.is_dir())
            tail = "..." if len(available) > 25 else ""
            return (
                f"MCU '{mcu}' not found under {root / 'processors'}. "
                f"Available: {available[:25]}{tail}"
            )
        try:
            sdk_dir = _resolve_platform_sdk_dir(mcu_dir, platform_sdk_dir)
        except (FileNotFoundError, RuntimeError) as e:
            return str(e)
        uc_dir = sdk_dir / "gtm" / "use_cases" / "use_cases_mexes"
        uc_mex = uc_dir / f"{usecase}.mex"

    if not uc_mex.exists():
        siblings: list[str] = []
        if uc_mex.parent.exists():
            siblings = sorted(p.stem for p in uc_mex.parent.glob("*.mex"))
        return (
            f"Use-case file not found: {uc_mex}\n"
            f"Available use-cases in {uc_mex.parent}: {siblings}"
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    launcher, tools_ini, distribution = _resolve_launcher(ctx, s32ct_launcher, launcher_ini)
    cmd = _build_prefix(launcher, tools_ini, distribution)
    cmd += [
        "-EmptyConfig",
        "-MCU", mcu,
        "-SDKVersion", sdk_version,
    ]
    if config_name:
        cmd += ["-ConfigName", config_name]
    cmd += [
        "-HeadlessTool", "GTM",
        "-Enable",
        "-ApplyUseCase", str(uc_mex),
    ]
    if gtm_codegen:
        cmd += ["-SetValue", "gtm_codegen=true"]
    cmd += [f"-{export_kind}", str(out)]

    effective_timeout = int(timeout_s) if timeout_s is not None else ctx.timeout_s
    try:
        rc, so, se = _run(cmd, timeout_s=effective_timeout)
    except subprocess.TimeoutExpired:
        return f"GTM use-case run timed out after {effective_timeout}s"

    if rc == 0:
        return (
            f"GTM use-case '{usecase}' applied for {mcu} ({sdk_version}). "
            f"{export_kind} -> {out} (use-case mex: {uc_mex})"
        )
    msg = (
        f"GTM headless run failed (exit code {rc}) for use-case '{usecase}' on {mcu}.\n"
        f"Use-case mex: {uc_mex}\n"
        f"stderr: {_truncate(se)}\n"
        f"stdout: {_truncate(so, 500)}"
    )
    if "instance data location has not been specified" in (se + so).lower():
        msg += "\nHint: try adding `-data <workspace>` to the launcher arguments."
    return msg


def cli_impl(
    ctx: S32CTContext,
    # Mode (mutually exclusive)
    project_path: Optional[str] = None,
    empty_config: bool = False,
    mcu: Optional[str] = None,
    sdk_version: Optional[str] = None,
    config_name: Optional[str] = None,
    # Tool selection
    tool_name: Optional[str] = None,
    enable_tool: Optional[bool] = None,
    # Generic edits / queries
    apply_use_case: Optional[str] = None,
    set_values: Optional[list[str]] = None,
    get_values: Optional[list[str]] = None,
    # Pins / Peripherals: import .c files into config
    import_c: Optional[list[str]] = None,
    # Peripherals-specific
    import_project: Optional[str] = None,
    sdk_path: Optional[str] = None,
    overwrite_with_sdk_sources: bool = False,
    migrate_to_toolchain_version: bool = False,
    migrate_to_highest_version: bool = False,
    # Code-generation framework options
    custom_copyright: Optional[str] = None,
    output_path_overrides: Optional[str] = None,
    # DCD / IVT / QuadSPI binary import
    import_bin: Optional[str] = None,
    # IVT-specific imports
    import_blob: Optional[str] = None,
    import_ab: Optional[str] = None,
    import_ddrc: Optional[str] = None,
    # IVT / boot-image export-control parameters
    auto_align: Optional[str] = None,
    custom_pointers_addrs: Optional[str] = None,
    start_pointer_addr: Optional[str] = None,
    entry_pointer_addr: Optional[str] = None,
    raw_binary: Optional[str] = None,
    clock_config_data: Optional[str] = None,
    mini_paco_structure: Optional[str] = None,
    pre_defined_data: Optional[str] = None,
    boot_device_id: Optional[str] = None,
    ivt_start_addr: Optional[str] = None,
    update_filepaths: Optional[str] = None,
    ivt_filter: Optional[str] = None,
    include_marker: bool = False,
    # eFUSE
    include_serial_boot_header: bool = False,
    # FFC
    import_arxml: Optional[list[str]] = None,
    import_json: Optional[str] = None,
    file_type: Optional[str] = None,
    default_containers: bool = False,
    # Validate
    validate: bool = False,
    # Export
    export_kind: Optional[str] = None,
    output_dir: Optional[str] = None,
    # Launcher
    data_dir: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
    s32ct_launcher: Optional[str] = None,
    launcher_ini: Optional[str] = None,
    timeout_s: Optional[int] = None,
) -> dict:
    """Generic S32CT headless CLI builder & runner.

    Covers the full documented CLI surface across all 9 tools. See the
    skill file ``skills/s32ct/s32ct-cli`` for the parameter
    semantics.
    """
    # ----- Mutually-exclusive mode -----
    if bool(project_path) == bool(empty_config):
        return {
            "exit_code": -1,
            "summary": (
                "Provide exactly one of `project_path` or `empty_config=true` "
                "(mutually exclusive)."
            ),
        }
    if empty_config and (not mcu or not sdk_version):
        return {
            "exit_code": -1,
            "summary": "`empty_config=true` requires both `mcu` and `sdk_version`.",
        }
    if project_path:
        proj = Path(project_path)
        if not proj.exists() or proj.suffix.lower() != ".mex":
            return {
                "exit_code": -1,
                "summary": f"project_path must be an existing .mex file. Got: {proj}",
            }

    # ----- Tool / export validation -----
    if tool_name is not None and tool_name not in ALLOWED_TOOLS:
        return {
            "exit_code": -1,
            "summary": f"Invalid tool_name '{tool_name}'. Allowed: {sorted(ALLOWED_TOOLS)}",
        }
    if export_kind is not None and export_kind not in ALLOWED_EXPORTS:
        return {
            "exit_code": -1,
            "summary": f"Invalid export_kind '{export_kind}'. Allowed: {sorted(ALLOWED_EXPORTS)}",
        }
    if export_kind and not output_dir:
        return {
            "exit_code": -1,
            "summary": "`output_dir` is required when `export_kind` is set.",
        }

    # ----- "Requires -HeadlessTool" framework rule -----
    # Per the S32CT headless CLI help
    # (topics/command_line_execution.html), the following framework-level
    # options are only legal inside a tool block, i.e. they require
    # `-HeadlessTool <tool>`:
    #
    #   -EmptyConfig, -SDKVersion, -ConfigName,
    #   -ExportMEX, -ExportAll,
    #   -CustomCopyright, -OutputPathOverrides
    #
    # If the caller asked for any of these without selecting a tool, fail
    # fast with a single, clear error listing every offending flag rather
    # than letting the launcher silently produce a half-bound .mex
    # (empty <processor>/<mcu_data>, schema fallbacks, etc.).
    _REQUIRES_HEADLESS_TOOL: list[tuple[str, bool]] = [
        ("-EmptyConfig",         bool(empty_config)),
        ("-MCU",                 bool(mcu)),
        ("-SDKVersion",          bool(sdk_version)),
        ("-ConfigName",          bool(config_name)),
        ("-CustomCopyright",     bool(custom_copyright)),
        ("-OutputPathOverrides", bool(output_path_overrides)),
        ("-ExportMEX",           export_kind == "ExportMEX"),
        ("-ExportAll",           export_kind == "ExportAll"),
    ]
    if not tool_name:
        offenders = [flag for flag, used in _REQUIRES_HEADLESS_TOOL if used]
        if offenders:
            return {
                "exit_code": -1,
                "summary": (
                    "The following S32CT option(s) require `-HeadlessTool` "
                    "(set `tool_name=` to one of "
                    f"{sorted(ALLOWED_TOOLS)}): {', '.join(offenders)}."
                ),
            }


    # ----- Optional-enum validation -----
    if file_type is not None and file_type not in ALLOWED_FFC_FILE_TYPES:
        return {
            "exit_code": -1,
            "summary": f"Invalid file_type '{file_type}'. Allowed: {sorted(ALLOWED_FFC_FILE_TYPES)}",
        }
    if update_filepaths is not None and update_filepaths not in ALLOWED_IVT_UPDATE_FILEPATHS:
        return {
            "exit_code": -1,
            "summary": (
                f"Invalid update_filepaths '{update_filepaths}'. "
                f"Allowed: {sorted(ALLOWED_IVT_UPDATE_FILEPATHS)}"
            ),
        }
    if ivt_filter is not None and ivt_filter not in ALLOWED_IVT_FILTERS:
        return {
            "exit_code": -1,
            "summary": f"Invalid ivt_filter '{ivt_filter}'. Allowed: {sorted(ALLOWED_IVT_FILTERS)}",
        }

    # ----- Existence checks for file inputs -----
    def _check_exists(path_str: Optional[str], label: str, ext: Optional[str] = None) -> Optional[dict]:
        if not path_str:
            return None
        p = Path(path_str)
        if not p.exists():
            return {"exit_code": -1, "summary": f"{label} not found: {p}"}
        if ext and p.suffix.lower() != ext.lower():
            return {"exit_code": -1, "summary": f"{label} must end in '{ext}'. Got: {p}"}
        return None

    for err in (
        _check_exists(apply_use_case, "apply_use_case", ".mex"),
        _check_exists(import_project, "import_project"),
        _check_exists(sdk_path, "sdk_path"),
        _check_exists(custom_copyright, "custom_copyright"),
        _check_exists(output_path_overrides, "output_path_overrides"),
        _check_exists(import_bin, "import_bin"),
        _check_exists(import_blob, "import_blob"),
        _check_exists(import_ab, "import_ab"),
        _check_exists(import_ddrc, "import_ddrc"),
        _check_exists(raw_binary, "raw_binary"),
        _check_exists(clock_config_data, "clock_config_data"),
        _check_exists(mini_paco_structure, "mini_paco_structure"),
        _check_exists(pre_defined_data, "pre_defined_data"),
        _check_exists(import_json, "import_json"),
    ):
        if err is not None:
            return err

    if import_arxml:
        for p in import_arxml:
            err = _check_exists(p, "import_arxml entry")
            if err is not None:
                return err

    if export_kind and output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    if tool_name and enable_tool is None:
        enable_tool = True

    # ----- Launcher resolution -----
    try:
        launcher, tools_ini, distribution = _resolve_launcher(ctx, s32ct_launcher, launcher_ini)
    except FileNotFoundError as e:
        return {"exit_code": -1, "summary": str(e)}

    effective_timeout = int(timeout_s) if timeout_s is not None else ctx.timeout_s

    # ----- Build CLI -----
    def build_cmd(_data_dir: Optional[str]) -> list[str]:
        cmd = _build_prefix(launcher, tools_ini, distribution)
        if _data_dir:
            cmd += ["-data", _data_dir]

        # Mode
        if project_path:
            cmd += ["-Load", str(Path(project_path))]
        else:
            cmd += ["-EmptyConfig", "-MCU", str(mcu), "-SDKVersion", str(sdk_version)]
        if config_name:
            cmd += ["-ConfigName", config_name]

        # Framework-level code-generation options
        if custom_copyright:
            cmd += ["-CustomCopyright", str(Path(custom_copyright))]
        if output_path_overrides:
            cmd += ["-OutputPathOverrides", str(Path(output_path_overrides))]

        # Tool block
        if tool_name:
            cmd += ["-HeadlessTool", tool_name]
            if enable_tool:
                cmd += ["-Enable"]

        # Imports (must be after -HeadlessTool / -Load, before exports)
        if import_c:
            cmd += ["-ImportC", *list(import_c)]
        if import_project:
            cmd += ["-importProject", str(Path(import_project))]
            if sdk_path:
                cmd += ["-sdkPath", str(Path(sdk_path))]
            if overwrite_with_sdk_sources:
                cmd += ["-overwriteWithSdkSources"]
        if migrate_to_toolchain_version:
            cmd += ["-MigrateComponentsToToolchainVersion"]
        if migrate_to_highest_version:
            cmd += ["-MigrateComponentsToHighestVersion"]
        if import_bin:
            cmd += ["-ImportBin", str(Path(import_bin))]
        if import_blob:
            cmd += ["-ImportBlob", str(Path(import_blob))]
            if ivt_start_addr:
                cmd += ["-IvtStartAddr", ivt_start_addr]
            if boot_device_id:
                cmd += ["-bootDeviceId", boot_device_id]
        if import_ab:
            cmd += ["-ImportAB", str(Path(import_ab))]
        if import_ddrc:
            cmd += ["-ImportDDRC", str(Path(import_ddrc))]
        if import_arxml:
            cmd += ["-ImportARXML", *[str(Path(p)) for p in import_arxml]]
        if import_json:
            cmd += ["-ImportJSON", str(Path(import_json))]

        # Apply use-case (GTM)
        if apply_use_case:
            cmd += ["-ApplyUseCase", str(Path(apply_use_case))]

        # Set / Get values (any tool that supports them)
        if set_values:
            cmd += ["-SetValue", *list(set_values)]
        if get_values:
            cmd += ["-GetValue", *list(get_values)]

        # Validation verb. The documented headless flag is
        # ``-ValidateConfiguration`` (see command_line_execution_-_dcd_tool /
        # _-_ivt_tool / _ffc_tool.html, and DCD CmdApplication's
        # VALIDATE_CONFIGURATION_ARG). ``-Validate`` is NOT a real verb.
        if validate:
            cmd += ["-ValidateConfiguration"]

        # IVT alignment / pointers / boot-image arguments
        if auto_align is not None:
            cmd += ["-AutoAlign"]
            if auto_align:
                cmd += [auto_align]
        if custom_pointers_addrs:
            cmd += ["-CustomPointersAddrs", custom_pointers_addrs]
        if start_pointer_addr:
            cmd += ["-start_pointer_addr", start_pointer_addr]
        if entry_pointer_addr:
            cmd += ["-entry_pointer_addr", entry_pointer_addr]
        if raw_binary:
            cmd += ["-raw_binary", str(Path(raw_binary))]
        if clock_config_data:
            cmd += ["-clockConfigData", str(Path(clock_config_data))]
        if mini_paco_structure:
            cmd += ["-miniPacoStructure", str(Path(mini_paco_structure))]
        if pre_defined_data:
            cmd += ["-pre_defined_data", str(Path(pre_defined_data))]
        if update_filepaths:
            cmd += ["-UpdateFilepaths", update_filepaths]
        if ivt_filter:
            cmd += ["-filter", ivt_filter]
        if include_marker:
            cmd += ["-includeMarker"]

        # eFUSE flags
        if include_serial_boot_header:
            cmd += ["-IncludeSerialBootHeader"]

        # FFC flags
        if file_type:
            cmd += ["-FileType", file_type]
        if default_containers:
            cmd += ["-defaultContainers"]

        # Export verb (single)
        if export_kind and output_dir:
            cmd += [f"-{export_kind}", str(Path(output_dir))]

        # Escape hatch (always last)
        if extra_args:
            cmd += list(extra_args)
        return cmd

    cmd = build_cmd(data_dir)
    rendered_cmd = " ".join(f'"{c}"' if " " in c else c for c in cmd)

    def do_run(_cmd: list[str]) -> tuple[int, str, str]:
        try:
            return _run(_cmd, timeout_s=effective_timeout)
        except subprocess.TimeoutExpired:
            return -2, "", f"S32CT CLI timed out after {effective_timeout}s"

    rc, so, se = do_run(cmd)
    if (
        rc != 0
        and not data_dir
        and "instance data location has not been specified" in (so + se).lower()
    ):
        tmpdata = tempfile.mkdtemp(prefix="s32ct_data_")
        logger.info("Retrying S32CT CLI with -data %s", tmpdata)
        cmd2 = build_cmd(tmpdata)
        rendered_cmd = " ".join(f'"{c}"' if " " in c else c for c in cmd2)
        rc, so, se = do_run(cmd2)

    values = _parse_get_value_table(so, list(get_values or []))

    if rc == 0:
        bits: list[str] = []
        if export_kind and output_dir:
            bits.append(f"{export_kind} -> {output_dir}")
        if set_values:
            bits.append(f"{len(set_values)} value(s) set")
        if get_values:
            bits.append(f"{len(values)}/{len(get_values)} value(s) read")
        if apply_use_case:
            bits.append("use-case applied")
        if validate:
            bits.append("validate ok")
        if import_project:
            bits.append("project imported")
        if any([import_bin, import_blob, import_ab, import_ddrc, import_arxml, import_json]):
            bits.append("binary/data imported")
        summary = "S32CT CLI succeeded" + (": " + "; ".join(bits) if bits else "")
    else:
        summary = (
            f"S32CT CLI failed (exit code {rc}). "
            f"stderr: {_truncate(se, 800)}"
        )

    return {
        "exit_code": rc,
        "command": rendered_cmd,
        "stdout_tail": _truncate(so, 2000),
        "stderr_tail": _truncate(se, 2000),
        "values": values,
        "summary": summary,
    }
