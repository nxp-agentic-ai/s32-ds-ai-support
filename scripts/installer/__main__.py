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

"""S32DS Agentic AI - Self-extracting Python installer
Usage:
    python s32ds-agentic-ai-installer-<version>.pyz
    python s32ds-agentic-ai-installer-<version>.pyz --dest /path/to/install
    python s32ds-agentic-ai-installer-<version>.pyz --yes
    python s32ds-agentic-ai-installer-<version>.pyz --dest /path/to/install --no-venv

By default the installer creates an isolated .venv inside the destination and
installs the wheels into it. This is required on PEP 668 "externally-managed" Linux
distributions (Ubuntu 24.04, Debian 12+, Fedora, ...) where system-wide pip
installs are blocked. Pass --no-venv to install into the system Python instead.
"""


import argparse
import functools
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


BANNER = """
+-----------------------------------------------------------+
|           S32DS AGENTIC AI - Installer                    |
|                 Version {version:<34}|
+-----------------------------------------------------------+
"""

# Try to import extended manifest first; fall back to standard if not present.
# This way the installer works with whichever variant was bundled into the .pyz
# without needing any variant marker or conditional logic.  Both manifests
# expose the same shared helpers (normalize, whl_dist_name, required_whl_names).
try:
    import _manifest_extended as manifest
except ImportError:
    import _manifest as manifest

VERSION = manifest.VERSION
WHL_DIR = manifest.WHL_DIR
COMPONENTS = manifest.COMPONENTS
DEFAULT_COMPONENT = manifest.DEFAULT_COMPONENT


# --- Default install destination --------------------------------------------

# Directory name appended to the platform-specific install root.
INSTALL_DIR_NAME = "s32ds-agentic-ai"

# POSIX default install root. Writing here normally requires root.
POSIX_INSTALL_ROOT = Path("/usr/local/NXP")


@functools.lru_cache(maxsize=1)
def _safe_system_drive() -> str:
    """Return a validated Windows system drive designator such as 'C:'.

    SystemDrive comes from the environment and is therefore untrusted: a
    malformed or hostile value (a UNC prefix such as \\\\server\\share, a
    path with separators, or anything other than a single drive letter)
    must not be able to steer the installer to an unintended location.
    Only a bare '<letter>:' is accepted; anything else falls back to 'C:'
    and reports the substitution instead of failing silently.

    The result is cached, which also means the fallback notice is printed at
    most once even though this helper is consulted several times per run.
    """
    drive = os.environ.get("SystemDrive", "C:")
    if not re.fullmatch(r"[A-Za-z]:", drive):
        print(
            f"NOTE: The SystemDrive environment variable has an unexpected "
            f"value ({drive!r}); using 'C:' for the default install path.",
            file=sys.stderr,
        )
        return "C:"
    return drive.upper()


def running_as_root() -> bool:
    """Return True when the current POSIX process has effective UID 0."""
    geteuid = getattr(os, "geteuid", None)
    return geteuid is not None and geteuid() == 0


def default_install_dest() -> Path:
    """Return the platform-specific default installation directory.

    Windows:      <SystemDrive>\\NXP\\s32ds-agentic-ai
                  (typically C:\\NXP\\s32ds-agentic-ai; SystemDrive is
                  validated by _safe_system_drive and falls back to 'C:')
    Linux/macOS:  /usr/local/NXP/s32ds-agentic-ai

    The returned path is resolved so it is directly comparable with a
    user-supplied --dest (which is also resolved). On POSIX, /usr/local
    normally requires elevated privileges to write; the interactive prompt
    and --dest let the user pick any path they can write to, for example a
    location under their home directory.
    """
    if os.name == "nt":
        base = Path(f"{_safe_system_drive()}\\") / "NXP"
    else:
        base = POSIX_INSTALL_ROOT
    return (base / INSTALL_DIR_NAME).resolve()


def _default_dest_help() -> str:
    """Return --dest help text naming the default for the current system.

    Generated at run time so the text always reflects the real default
    (including the actual SystemDrive on Windows) rather than a hardcoded
    'C:' that would mislead users whose Windows lives on another drive.
    """
    return (
        "Installation destination directory "
        f"(default on this system: {default_install_dest()})"
    )


# Directories the installer must never extract into. A destination equal to
# one of these, or nested inside one, would mean writing files (and creating a
# .venv) inside a system-critical tree. POSIX and Windows lists are kept
# separate because the dangerous roots differ per platform.
FORBIDDEN_POSIX_ROOTS = (
    Path("/"),
    Path("/bin"),
    Path("/boot"),
    Path("/dev"),
    Path("/etc"),
    Path("/lib"),
    Path("/lib64"),
    Path("/proc"),
    Path("/run"),
    Path("/sbin"),
    Path("/sys"),
    Path("/usr/bin"),
    Path("/usr/lib"),
    Path("/usr/sbin"),
    Path("/var/lib"),
    Path("/var/run"),
)

# Windows equivalents, given as paths relative to a drive root. They are
# combined with the drive of the *destination* (not the system drive) so an
# attempt to install into D:\Windows\System32 is caught as well.
FORBIDDEN_WINDOWS_SUBDIRS = (
    "Windows",
    "Program Files\\WindowsApps",
    "ProgramData",
)


def validate_dest(dest: Path) -> None:
    """Raise ValueError when `dest` points at a system-critical location.

    `dest` is expected to be an already-resolved absolute path. Resolving a
    user-supplied string normalises away `..` segments but does not make the
    result safe: an input such as `../../../../etc` still resolves to a real
    system directory. This check is the guard that turns a dangerous
    destination into a refusal instead of an extraction that overwrites
    operating-system files.

    Forbidden roots are themselves resolved before comparison so a symlinked
    system directory (for example /usr/lib -> /lib on merged-usr distros)
    cannot be used to slip past the check.

    Only obviously destructive targets are rejected; ordinary user-chosen
    locations (home directory, /opt, D:\\tools, ...) are left alone.
    """
    if not dest.is_absolute():
        raise ValueError(f"Destination must be an absolute path: {dest}")

    if os.name == "nt":
        # Refuse a bare drive root such as "C:\" as well as the OS trees.
        if dest.parent == dest:
            raise ValueError(
                f"Refusing to install directly into a drive root: {dest}"
            )
        # Anchor the forbidden list on the destination's own drive; using the
        # system drive here would let D:\Windows\System32 pass unnoticed.
        drive_root = Path(dest.anchor)
        forbidden = [drive_root / sub for sub in FORBIDDEN_WINDOWS_SUBDIRS]
    else:
        forbidden = list(FORBIDDEN_POSIX_ROOTS)

    for root in forbidden:
        try:
            resolved_root = root.resolve()
        except OSError:
            # A forbidden root that cannot be resolved (missing, permission
            # denied, ...) cannot be the destination either; skip it rather
            # than aborting the whole validation.
            continue
        if dest == resolved_root or dest.is_relative_to(resolved_root):
            raise ValueError(
                f"Refusing to install into system directory {root}: {dest}"
            )


def prompt_dest(default_dest: Path, max_attempts: int = 3) -> Path:
    """Prompt for an install destination, validating each answer.

    Re-prompts on a rejected path (up to `max_attempts`) so a typo does not
    abort the whole run, and exits non-zero rather than proceeding with an
    unsafe destination when the user keeps supplying one. The default is
    validated too: accepting it with a bare ENTER must not bypass the check.
    """
    for _ in range(max_attempts):
        try:
            dest_input = input(f"Install destination [{default_dest}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nInstallation cancelled.")
            sys.exit(0)

        dest = Path(dest_input).expanduser().resolve() if dest_input else default_dest
        try:
            validate_dest(dest)
            return dest
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            print("       Please choose a different destination.", file=sys.stderr)

    print(
        "ERROR: Too many invalid destinations; aborting installation.",
        file=sys.stderr,
    )
    sys.exit(1)


def assert_dest_safe_at_write_time(dest: Path) -> None:
    """Re-validate `dest` immediately before anything is written into it.

    validate_dest runs before the directory is created, which leaves a small
    time-of-check/time-of-use window: between validation and extraction the
    path could be replaced by a symlink aimed at a system directory. Calling
    this right before extraction closes that window by re-resolving the real
    path and rejecting it if it moved or is now forbidden.
    """
    real = dest.resolve()
    validate_dest(real)
    if real != dest:
        raise ValueError(
            f"Destination {dest} now resolves to {real}; refusing to continue "
            "(possible symlink redirection)."
        )


# --- Pre-flight checks -------------------------------------------------------

def check_python_version():
    if sys.version_info < (3, 11):
        print(f"ERROR: Python 3.11 or newer is required. Found {sys.version}")
        sys.exit(1)


def check_pip():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("ERROR: pip is not available. Please install pip first.")
        sys.exit(1)


# --- Virtual environment -----------------------------------------------------

def venv_python(venv_dir: Path) -> Path:
    """Return the path to the python interpreter inside a venv (cross-platform)."""
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def create_venv(dest: Path) -> Path:
    """Create a .venv inside dest and return its python interpreter path.

    On PEP 668 "externally-managed" distributions (Ubuntu 24.04, Debian 12+,
    Fedora, ...) installing packages into the system Python via pip is blocked.
    Creating an isolated virtual environment sidesteps that restriction and is
    the recommended layout: the run-mcp.sh / run-mcp.bat wrappers already
    auto-activate a .venv located next to them, so a venv at <dest>/.venv is
    picked up transparently at run time.
    """
    venv_dir = dest / ".venv"
    print(f"\n[venv] Creating virtual environment at {venv_dir} ...")

    result = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True, text=True,
    )
    py = venv_python(venv_dir)
    if result.returncode != 0 or not py.is_file():
        print("ERROR: Failed to create the virtual environment.")
        if result.stderr:
            print(result.stderr.strip())
        if os.name == "posix":
            print(
                "\n  Hint: the 'venv' module may be missing. On Debian/Ubuntu run:\n"
                "        sudo apt install python3-venv\n"
                "        (match the version, e.g. python3.12-venv)"
            )
        sys.exit(1)

    # Upgrade pip inside the fresh venv so wheel installs are reliable.
    subprocess.run(
        [str(py), "-m", "pip", "install", "--upgrade", "pip"],
        capture_output=True, text=True,
    )
    return py



# --- Archive helpers ---------------------------------------------------------

def get_this_zip() -> zipfile.ZipFile:
    """Open the current .pyz file as a ZipFile."""
    candidate = Path(__file__)
    while candidate != candidate.parent:
        if candidate.suffix in (".pyz", ".zip") and candidate.is_file():
            return zipfile.ZipFile(candidate, "r")
        candidate = candidate.parent
    argv0 = Path(sys.argv[0])
    if argv0.is_file() and argv0.suffix in (".pyz", ".zip"):
        return zipfile.ZipFile(argv0, "r")
    raise RuntimeError(
        f"Cannot locate the installer archive. "
        f"__file__={__file__!r}, sys.argv[0]={sys.argv[0]!r}"
    )


def list_whl_entries(zf: zipfile.ZipFile) -> list[str]:
    """Return all whl/<name>.whl paths inside the archive."""
    return [
        name for name in zf.namelist()
        if name.startswith(f"{WHL_DIR}/") and name.endswith(".whl")
    ]


def _copy_zip_entry(zf: zipfile.ZipFile, entry: str, target: Path) -> None:
    """Copy a single archive entry to target, creating parent directories."""
    if entry.endswith("/"):
        target.mkdir(parents=True, exist_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(entry) as src, open(target, "wb") as dst:
        shutil.copyfileobj(src, dst)
    # On POSIX, shell scripts are copied byte-for-byte and land with default
    # (non-executable) permissions. Restore the execute bit so wrappers like
    # run-mcp.sh can be launched directly (./run-mcp.sh) on Linux/macOS.
    if os.name == "posix" and target.suffix == ".sh":
        mode = os.stat(target).st_mode
        os.chmod(target, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _stage_whls(zf: zipfile.ZipFile, tmp_whl_dir: Path, whl_entries) -> None:
    """Copy the given wheel entries from the archive into tmp_whl_dir."""
    for entry in whl_entries:
        _copy_zip_entry(zf, entry, tmp_whl_dir / Path(entry).name)


# --- Component discovery -----------------------------------------------------

def discover_components() -> dict[str, dict]:
    """Return the user-selectable components from the manifest.

    Filters out the reserved DEFAULT_COMPONENT which holds shared assets that
    are always installed.
    """
    return {
        name: comp for name, comp in COMPONENTS.items()
        if name != DEFAULT_COMPONENT
    }


# --- Package selection UI ----------------------------------------------------

def select_components(
    components: dict[str, dict],
    yes: bool,
    preselect: list[str] | None
) -> set[str]:
    """Interactive checklist for selecting which components to install.

    Returns a set of component names to install.
    """
    component_names = sorted(components.keys())

    # Start with everything selected
    selected: set[str] = set(component_names)

    # If --packages was given, validate and apply
    if preselect is not None:
        normalised_pre = {manifest.normalize(p) for p in preselect}
        # Expand short names: "compiler" -> match against component names
        expanded: set[str] = set()
        for p in normalised_pre:
            # Direct match
            if p in component_names:
                expanded.add(p)
            # Try with nxp-mcp- prefix removed
            elif p.startswith("nxp-mcp-"):
                short = p[8:]  # remove "nxp-mcp-"
                if short in component_names:
                    expanded.add(short)
            # Try matching component names
            else:
                for comp in component_names:
                    if comp == p or comp.endswith(f"-{p}") or p in comp:
                        expanded.add(comp)

        unknown = normalised_pre - {manifest.normalize(c) for c in expanded}
        if unknown:
            print(f"WARNING: Unknown packages ignored: {', '.join(sorted(unknown))}")
        selected = expanded & set(component_names)
        return selected

    # --yes: install all without prompting
    if yes:
        return selected

    # Interactive mode
    display: list[tuple[str, bool]] = []
    for comp in component_names:
        display.append((comp, True))  # all pre-checked

    # Detect ANSI support
    _ansi = (
        sys.stdout.isatty()
        and (
            os.name != "nt"
            or os.environ.get("WT_SESSION")
            or os.environ.get("TERM_PROGRAM")
            or os.environ.get("TERM")
        )
    )
    _prev_lines: list[int] = [0]

    def _render(items: list[tuple[str, bool]]) -> None:
        lines = [
            "",
            "  Select components to install:",
            "  (all pre-selected; enter number(s) to toggle, ENTER to confirm)",
            "",
        ]
        for i, (name, sel) in enumerate(items, 1):
            mark = "x" if sel else " "
            lines.append(f"    {i:2}. [{mark}] {name}")
        lines.append("")
        text = "\n".join(lines) + "\n"
        if _ansi and _prev_lines[0]:
            sys.stdout.write(f"\x1b[{_prev_lines[0]}A\x1b[0J")
        sys.stdout.write(text)
        sys.stdout.flush()
        _prev_lines[0] = len(lines)

    while True:
        _render(display)
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nInstallation cancelled.")
            sys.exit(0)

        if raw == "":
            break

        tokens = raw.split()
        invalid: list[str] = []
        for tok in tokens:
            try:
                idx = int(tok) - 1
                if 0 <= idx < len(display):
                    name, sel = display[idx]
                    display[idx] = (name, not sel)
                else:
                    invalid.append(tok)
            except ValueError:
                invalid.append(tok)
        if invalid:
            print(f"  Invalid input ignored: {', '.join(invalid)}")

    return {name for name, sel in display if sel}


# --- Extraction --------------------------------------------------------------

def extract_assets(
    zf: zipfile.ZipFile,
    dest: Path,
    tmp_whl_dir: Path,
    selected_components: set[str],
) -> None:
    """Extract selected component assets and stage their WHL files."""
    print("\n[1/3] Extracting bundled assets...")
    BAR_WIDTH = 30

    def _progress(label: str, current: int, total: int, done: bool = False) -> None:
        filled = int(BAR_WIDTH * current / total) if total else BAR_WIDTH
        bar = "#" * filled + "-" * (BAR_WIDTH - filled)
        end = "\n" if done else ""
        print(f"\r      {label:<22} [{bar}] {current}/{total}", end=end, flush=True)

    # Always extract the shared DEFAULT_COMPONENT assets.
    components_to_extract = {DEFAULT_COMPONENT} | selected_components

    # Track what we've extracted to avoid duplicates.
    extracted_paths: set[str] = set()
    staged_whls: set[str] = set()

    archive_entries = set(zf.namelist())

    for comp_name in sorted(components_to_extract):
        comp_def = COMPONENTS.get(comp_name)
        if comp_def is None:
            continue

        # Build the full extraction work-list for this component up front so a
        # single progress bar can cover all of its file and folder assets.
        entries: list[str] = []

        for _src_rel, dest_rel in comp_def.get("files", []):
            if dest_rel not in extracted_paths and dest_rel in archive_entries:
                extracted_paths.add(dest_rel)
                entries.append(dest_rel)

        # A folder entry is (source, dest) or (source, dest, [excludes]).
        # Excludes are honoured at build time (create_deploy_package.py), so
        # the archive already omits them; here we only need the dest prefix and
        # must tolerate the optional third element.
        for folder_entry in comp_def.get("folders", []):
            folder_dest = folder_entry[1]
            for entry in zf.namelist():
                if entry.startswith(f"{folder_dest}/") and entry not in extracted_paths:
                    extracted_paths.add(entry)
                    entries.append(entry)

        if comp_name == DEFAULT_COMPONENT:
            # Shared/common files are extracted as a silent background step.
            for entry in entries:
                _copy_zip_entry(zf, entry, dest / entry)
        else:
            # One progress bar per component; skip components with no assets.
            total = len(entries)
            if total:
                for count, entry in enumerate(entries, 1):
                    _copy_zip_entry(zf, entry, dest / entry)
                    _progress(comp_name, count, total, done=(count == total))

        # Stage WHL files for this component (silent background step, no bar).
        for whl_name in comp_def.get("whl", []):
            norm_name = manifest.normalize(whl_name)
            if norm_name in staged_whls:
                continue
            staged_whls.add(norm_name)
            matching = [
                e for e in list_whl_entries(zf)
                if manifest.whl_dist_name(e) == norm_name
            ]
            _stage_whls(zf, tmp_whl_dir, matching)


# --- Installation ------------------------------------------------------------

def install_wheels(
    tmp_whl_dir: Path,
    selected_components: set[str],
    python_exe: str | None = None,
) -> None:
    """Install WHL files for selected components (plus shared defaults).

    Uninstalls *every* suite wheel first, then installs only the wheels
    required by the current selection. This guarantees that packages
    deselected in a re-install are removed even though the current run
    would not otherwise touch them - fixing the case where a prior wider
    install leaves stale packages behind.

    ``python_exe`` selects the interpreter whose pip performs the install.
    It is normally the venv interpreter (the default install path) so wheels
    land inside <dest>/.venv instead of the (possibly PEP 668-locked) system
    Python. It falls back to the current interpreter (system Python) when the
    installer was run with --no-venv.
    """

    py = python_exe or sys.executable
    print("\n[2/3] Installing MCP packages via pip...")


    # Wheels we WANT installed after this run (selection + shared defaults).
    to_install_defs = {
        name: COMPONENTS[name]
        for name in ({DEFAULT_COMPONENT} | selected_components)
        if name in COMPONENTS
    }
    whl_names_to_install = manifest.required_whl_names(to_install_defs)

    # Every wheel the installer manages, across all components. This is what
    # we uninstall to guarantee a clean slate regardless of what a previous
    # install may have left behind.
    all_suite_whl_names = manifest.required_whl_names(COMPONENTS)

    # Find matching WHL files in tmp directory.
    all_whl_files = sorted(tmp_whl_dir.glob("*.whl"))
    if not all_whl_files:
        print("ERROR: No .whl files found to install.")
        sys.exit(1)

    whl_map: dict[str, Path] = {
        manifest.whl_dist_name(w): w for w in all_whl_files
    }

    whls_to_install = [
        whl_map[name] for name in sorted(whl_names_to_install) if name in whl_map
    ]

    # Clean-slate uninstall of every known suite wheel. pip tolerates names
    # that are not installed; capture_output suppresses the "not installed"
    # noise. Runs even when the selection is empty so "deselect everything"
    # actually performs a full uninstall.
    if all_suite_whl_names:
        subprocess.run(
            [py, "-m", "pip", "uninstall", "-y"]
            + sorted(all_suite_whl_names),
            capture_output=True,
        )


    if not whls_to_install:
        print("      (nothing selected to install)")
        return

    # Install all selected WHLs in a single pip call so the resolver can satisfy
    # shared dependencies from the local find-links directory.
    print(f"\n      pip install {' '.join(w.name for w in whls_to_install)}")
    result = subprocess.run(
        [
            py, "-m", "pip", "install",
            "--find-links", str(tmp_whl_dir),
        ] + [str(w) for w in whls_to_install],
    )

    if result.returncode != 0:
        print("\nERROR: pip install failed.")
        sys.exit(1)


def _disable_unselected_servers(
    dest: Path,
    selected_components: set[str],
) -> None:
    """Flip ``disabled: true`` for gateway servers the user did not select.

    The bundled ``configs/gateway.stdio.yaml`` (and ``.http.yaml``) ship with
    every server enabled so the canonical config in the repository stays
    authoritative. After a selective install we reconcile the extracted
    config against the user's choices so the gateway does not try to mount
    wheels that were never installed.

    The edit is performed with a regex on raw text (no PyYAML dependency)
    because this code runs on the user's system Python before any suite
    wheels are installed. The bundled YAML shape is known and stable, so
    the substitution is safe.
    """

    # Component names map 1:1 to server keys in the gateway YAML.
    installable = set(COMPONENTS.keys()) - {DEFAULT_COMPONENT}
    to_disable = installable - selected_components
    if not to_disable:
        return

    yaml_files = [
        dest / "configs" / "gateway.stdio.yaml",
        dest / "configs" / "gateway.http.yaml",
    ]

    for yaml_path in yaml_files:
        if not yaml_path.is_file():
            continue
        text = yaml_path.read_text(encoding="utf-8")
        original = text
        for name in sorted(to_disable):
            # Match:  "  <name>:\n    disabled: false"
            # with any indentation, so a future reformat does not break us.
            pattern = re.compile(
                r"(^(?P<indent>[ \t]+)"
                + re.escape(name)
                + r":\s*\n(?:(?P=indent)[ \t]+.*\n)*?"
                + r"(?P=indent)[ \t]+disabled:\s*)false\b",
                re.MULTILINE,
            )
            text = pattern.sub(r"\1true", text, count=1)
        if text != original:
            yaml_path.write_text(text, encoding="utf-8")
            print(
                f"      Disabled unselected servers in {yaml_path.name}: "
                f"{', '.join(sorted(to_disable))}"
            )


def register_agents_step(
    dest: Path,
    register_arg: str | None,
    yes: bool,
    copy_skills_arg: str | None = None,
    skip_copy_skills: bool = False,
    python_exe: str | None = None,
) -> None:
    """Offer to register the gateway into the user's AI agents and copy skills.

    Delegates entirely to register_agents.py (extracted to dest), forwarding
    --register, --yes, --copy-skills, and --skip-copy-skills so all interactive
    logic lives in one place.
    """
    only = (
        [p.strip() for p in register_arg.split(",")]
        if register_arg is not None
        else None
    )

    if yes and only is None:
        only = ["none"]

    # register_agents.py is bundled as a loose asset and extracted to dest.
    script = dest / "register_agents.py"
    if not script.is_file():
        print(f"\n  (Agent registration skipped: {script} not found)")
        return

    py = str(python_exe) if python_exe else sys.executable
    argv = [py, str(script), "--dest", str(dest)]

    if only is not None:
        argv += ["--register", ",".join(only)]
    if yes:
        argv += ["--yes"]
    if skip_copy_skills:
        argv += ["--skip-copy-skills"]
    elif copy_skills_arg is not None:
        # Explicit path override given.
        if copy_skills_arg:
            argv += ["--copy-skills", copy_skills_arg]
        else:
            argv += ["--copy-skills"]
    else:
        # No explicit flag: copy-skills always runs interactively by default.
        argv += ["--copy-skills"]
    subprocess.run(argv)


def print_success(dest: Path, used_venv: bool = False) -> None:
    print("\n[3/3] Installation complete!")
    print()
    print(f"  Install location: {dest}")
    if used_venv:
        print(f"  Virtual environment: {dest / '.venv'}")
        print("  The run-mcp.sh / run-mcp.bat wrappers will auto-activate it.")
    print()
    print("  See README.md for more information.")
    print()

    try:
        input("  Press Enter to exit...")
    except (EOFError, KeyboardInterrupt):
        pass
    print()


def main():
    parser = argparse.ArgumentParser(
        description="S32DS Agentic AI Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dest", "-d",
        type=str,
        default=None,
        help=_default_dest_help(),
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip all confirmation prompts and install everything",
    )
    parser.add_argument(
        "--packages", "-p",
        type=str,
        default=None,
        metavar="PKG[,PKG...]",
        help=(
            "Comma-separated list of sub-packages to install "
            "(e.g. --packages compiler,s32ct,knowledge). "
            "Short names (without 'nxp-mcp-' prefix) are accepted."
        ),
    )
    parser.add_argument(
        "--register",
        type=str,
        default=None,
        metavar="AGENT[,AGENT...]",
        help=(
            "Register the gateway into the listed AI agents after install "
            "(claude-desktop, vero, vscode, cursor, goose). Use 'none' to "
            "skip registration. Omit to show an interactive menu."
        ),
    )
    parser.add_argument(
        "--copy-skills",
        nargs="?",
        const="",
        default=None,
        metavar="DIR",
        help=(
            "Copy every bundled skill folder into DIR after install. "
            "Omit DIR to show an interactive per-agent menu. "
            "Skills are always copied unless --skip-copy-skills is given."
        ),
    )
    parser.add_argument(
        "--skip-copy-skills",
        action="store_true",
        help="Skip the skills copy step entirely.",
    )
    parser.add_argument(
        "--no-venv",
        action="store_true",
        help=(
            "Install the wheels into the system Python instead of an isolated "
            "virtual environment. By default the installer creates a .venv "
            "inside the destination directory and installs into it (required "
            "on PEP 668 'externally-managed' distributions such as Ubuntu "
            "24.04, Debian 12+ and Fedora, where system-wide pip installs are "
            "blocked). Use this flag only when you explicitly want a "
            "system-wide install."
        ),
    )

    args = parser.parse_args()
    print(BANNER.format(version=VERSION))

    # A virtual environment is created by default; --no-venv opts out and
    # installs into the system Python instead.
    use_venv = not args.no_venv

    check_python_version()
    # A freshly created venv always ships with pip, so the system-pip check is
    # only meaningful for the non-venv install path.
    if not use_venv:
        check_pip()

    # Resolve destination. Both the --dest value and anything typed at the
    # prompt are untrusted input: resolve() normalises '..' segments but does
    # not make the result safe, so every candidate goes through validate_dest
    # before the installer creates directories or extracts files.
    if args.dest:
        dest = Path(args.dest).expanduser().resolve()
        try:
            validate_dest(dest)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(2)
    else:
        default_dest = default_install_dest()
        # On POSIX the default lives under /usr/local, which is normally only
        # writable by root. Say so up front so the user can redirect the
        # install into their home directory instead of hitting a late
        # permission error (or unknowingly installing system-wide).
        if os.name != "nt" and not running_as_root():
            print(
                f"NOTE: The default destination ({default_dest}) usually "
                "requires root privileges.\n"
                "      Enter a different path (for example one under your "
                "home directory) if you do not\n"
                "      want to install system-wide with sudo."
            )
        dest = prompt_dest(default_dest)

    print(f"\nInstall destination: {dest}")

    skip_extraction = False
    if dest.exists() and any(dest.iterdir()):
        print("WARNING: Destination directory already exists and is not empty.")
        if not args.yes:
            confirm = input("Continue and overwrite existing files? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                reinstall = input("Reinstall packages only (skip file extraction)? [y/N]: ").strip().lower()
                if reinstall not in ("y", "yes"):
                    print("Installation cancelled.")
                    sys.exit(0)
                skip_extraction = True

    dest.mkdir(parents=True, exist_ok=True)

    # Close the time-of-check/time-of-use window: the destination was
    # validated before it existed, so re-check the real path now that it does
    # and before any file is written into it.
    try:
        assert_dest_safe_at_write_time(dest)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    # By default create an isolated environment inside the destination and
    # install the wheels there instead of the system Python; --no-venv opts out.
    python_exe = create_venv(dest) if use_venv else None

    preselect = [p.strip() for p in args.packages.split(",")] if args.packages else None


    with tempfile.TemporaryDirectory(prefix="nxp_mcp_install_") as tmp:
        tmp_whl_dir = Path(tmp) / WHL_DIR
        tmp_whl_dir.mkdir()

        with get_this_zip() as zf:
            components = discover_components()

            if skip_extraction:
                print("\n[1/3] Skipping asset extraction (reinstall only)...")
                # Still need to stage all WHLs for reinstall.
                _stage_whls(zf, tmp_whl_dir, list_whl_entries(zf))
                # Select all components for reinstall.
                selected = set(components.keys())
            else:
                # Package selection (interactive or via flags).
                selected = select_components(components, yes=args.yes, preselect=preselect)
                extract_assets(zf, dest, tmp_whl_dir, selected)

        install_wheels(tmp_whl_dir, selected, python_exe)


    # Reconcile the extracted gateway config against the user's selection
    # so unselected servers are marked disabled and the gateway does not
    # attempt to mount wheels that were never installed.
    _disable_unselected_servers(dest, selected)

    register_agents_step(
        dest,
        args.register,
        args.yes,
        copy_skills_arg=args.copy_skills,
        skip_copy_skills=args.skip_copy_skills,
        python_exe=python_exe,
    )

    print_success(dest, used_venv=use_venv)


if __name__ == "__main__":
    main()
