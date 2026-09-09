#!/usr/bin/env python3
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

"""Create a self-installing S32DS Agentic AI deployment package.

This script collects all built WHL files, bundled assets (knowledge_db, models,
skills, configs), and the installer entry point into a single runnable .pyz
file using Python's zipapp module.

Usage:
    python scripts/create_deploy_package.py
    python scripts/create_deploy_package.py --output dist/s32ds-agentic-ai-installer.pyz
    python scripts/create_deploy_package.py --variant extended

Output:
    dist/s32ds-agentic-ai-installer-<version>.pyz

The resulting .pyz can be distributed as a single file and run with:
    python s32ds-agentic-ai-installer-<version>.pyz
    python s32ds-agentic-ai-installer-<version>.pyz --dest /path/to/install
    python s32ds-agentic-ai-installer-<version>.pyz --yes
    python s32ds-agentic-ai-installer-<version>.pyz --dest /path/to/install --no-venv

By default the bundled installer creates a .venv inside the destination
directory and installs the wheels into it (handled at install time by
scripts/installer/__main__.py); the run-mcp.sh / run-mcp.bat wrappers
auto-activate that .venv. This is required on PEP 668 "externally-managed" Linux
distributions (Ubuntu 24.04, Debian 12+, Fedora, ...) where system-wide pip
installs are blocked. Pass --no-venv to install into the system Python instead.
"""


import argparse
import sys
import tomllib
import zipfile
from pathlib import Path

# --- Paths -------------------------------------------------------------------

PROJECT_ROOT  = Path(__file__).parent.parent
INSTALLER_DIR = PROJECT_ROOT / "scripts" / "installer"

# Supported variants
SUPPORTED_VARIANTS = ["standard", "extended"]
DEFAULT_VARIANT = "standard"


# --- Helpers -----------------------------------------------------------------
# Package-name / wheel-name utilities live in the shared manifest module and are
# accessed via the imported manifest (manifest.normalize, manifest.whl_dist_name,
# manifest.required_whl_names) so there is a single implementation shared with
# the installer.

def load_manifest(variant: str):
    """Dynamically import the appropriate manifest module based on variant.

    Returns the manifest module (_manifest or _manifest_extended).
    """
    sys.path.insert(0, str(INSTALLER_DIR))

    if variant == "standard":
        import _manifest
        return _manifest
    elif variant == "extended":
        import _manifest_extended
        return _manifest_extended
    else:
        print(f"ERROR: Unknown variant '{variant}'. Choose from: {', '.join(SUPPORTED_VARIANTS)}")
        sys.exit(1)


def resolve_version(override: str | None) -> str:
    """Return the version to stamp into the installer.

    If --version was passed on the CLI, use it verbatim.
    Otherwise fall back to the [project].version field in the root
    pyproject.toml so the installer version always tracks the package release.
    """
    if override:
        return override.strip()
    pyproject = PROJECT_ROOT / "pyproject.toml"
    if not pyproject.exists():
        print(f"ERROR: Root pyproject.toml not found: {pyproject}")
        sys.exit(1)
    with open(pyproject, "rb") as fh:
        data = tomllib.load(fh)
    version = data.get("project", {}).get("version")
    if not version:
        print("ERROR: [project].version not found in pyproject.toml")
        sys.exit(1)
    return version


def build_manifest_bytes(version: str, manifest_src: Path) -> bytes:
    """Return the manifest file bytes with @@VERSION@@ substituted.

    Args:
        version: Version string to substitute
        filename: Name of the manifest file (_manifest.py or _manifest_extended.py)
    """
    if not manifest_src.exists():
        print(f"ERROR: {manifest_src} not found.")
        sys.exit(1)

    text = manifest_src.read_text(encoding="utf-8")
    patched = text.replace('"@@VERSION@@"', f'"{version}"')
    return patched.encode("utf-8")


def collect_whl_files(manifest) -> dict[str, Path]:
    """Collect all WHL files referenced in COMPONENTS.

    Returns a dict mapping normalized package name -> Path to .whl file.
    Exits if any required WHL is missing.
    """
    dist_dir = PROJECT_ROOT / "dist"
    if not dist_dir.is_dir():
        print("ERROR: dist/ directory not found. Run: python scripts/build_modules.py")
        sys.exit(1)

    # Build map of all available WHLs (normalized dist name -> path).
    available: dict[str, Path] = {
        manifest.whl_dist_name(w): w for w in dist_dir.glob("*.whl")
    }

    # Collect all required WHL names from all components.
    required: set[str] = manifest.required_whl_names(manifest.COMPONENTS)

    # Check for missing WHLs
    missing = required - set(available.keys())
    if missing:
        print("ERROR: The following required packages have no matching .whl in dist/:")
        for m in sorted(missing):
            print(f"         - {m}")
        print()
        print("       Run 'python scripts/build_modules.py' to rebuild all sub-packages,")
        print("       then retry.")
        sys.exit(1)

    return {name: available[name] for name in required}


def add_component_assets(
    zf: zipfile.ZipFile,
    manifest
) -> int:
    """Add all component assets (files and folders) to the archive.

    Returns the total number of files added.
    """
    count = 0

    for comp_name, comp_def in manifest.COMPONENTS.items():
        # Add files
        for src_rel, dest_rel in comp_def.get("files", []):
            src = PROJECT_ROOT / src_rel
            if not src.exists():
                print(f"WARNING: Component '{comp_name}' file not found: {src}")
                continue
            zf.write(src, dest_rel)
            count += 1

        # Add folders
        #
        # A folder entry is a tuple:
        #   (source_folder, dest_folder)                 - copy whole tree
        #   (source_folder, dest_folder, [excludes])     - copy tree, skipping
        #                                                  the listed relative
        #                                                  subpaths
        # Excludes are relative to source_folder (POSIX-style). A file is
        # skipped when its path equals an exclude or lives under one, so
        # excluding "internal" drops both "internal" and "internal/foo/bar".
        for entry in comp_def.get("folders", []):
            src_rel, dest_prefix = entry[0], entry[1]
            excludes = entry[2] if len(entry) > 2 else []
            src_dir = PROJECT_ROOT / src_rel
            if not src_dir.exists():
                print(f"WARNING: Component '{comp_name}' folder not found: {src_dir}")
                continue
            for path in sorted(src_dir.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(src_dir)
                    rel_posix = rel.as_posix()
                    if any(
                        rel_posix == ex or rel_posix.startswith(ex + "/")
                        for ex in excludes
                    ):
                        continue
                    arcname = f"{dest_prefix}/{rel_posix}"
                    zf.write(path, arcname)
                    count += 1

    return count


def format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# --- Main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build a self-installing .pyz package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output .pyz path (default: dist/s32ds-agentic-ai-installer-<ver>.pyz)",
    )
    parser.add_argument(
        "--version",
        default=None,
        metavar="X.Y.Z",
        help=(
            "Version to stamp into the installer (default: read from "
            "[project].version in the root pyproject.toml)"
        ),
    )
    parser.add_argument(
        "--variant",
        default=DEFAULT_VARIANT,
        choices=SUPPORTED_VARIANTS,
        help=(
            f"Installer variant to build (default: {DEFAULT_VARIANT}). "
            "'standard' excludes internal-only components; "
            "'extended' includes everything."
        ),
    )
    args = parser.parse_args()

    version = resolve_version(args.version)
    manifest = load_manifest(args.variant)

    # Resolve output path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        dist_dir = PROJECT_ROOT / "dist"
        dist_dir.mkdir(parents=True, exist_ok=True)
        if args.variant == DEFAULT_VARIANT:
            output_path = dist_dir / f"s32ds-agentic-ai-installer-{version}.pyz"
        else:
            output_path = dist_dir / f"s32ds-agentic-ai-installer-{args.variant}-{version}.pyz"

    print(f"Building S32DS Agentic AI installer v{version}  [variant: {args.variant}]")
    print(f"Output: {output_path}")
    print()

    # Collect all required WHL files
    whl_map = collect_whl_files(manifest)
    print(f"Found {len(whl_map)} wheel files:")
    for name, path in sorted(whl_map.items()):
        print(f"  {path.name}  ({format_size(path.stat().st_size)})")
    print()

    # Check installer source
    for entry in manifest.INSTALLER_ENTRIES:
        entry_path = INSTALLER_DIR / entry
        if not entry_path.exists():
            print(f"ERROR: Installer source not found: {entry_path}")
            sys.exit(1)

    # Build the .pyz archive
    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:

        # 1. Installer entry point and manifest module(s).
        for entry in manifest.INSTALLER_ENTRIES:
            entry_path = INSTALLER_DIR / entry
            if entry.startswith("_manifest"):
                print(f"Adding installer manifest ({entry})...")
                zf.writestr(entry, build_manifest_bytes(version, entry_path))
            else:
                print(f"Adding installer entry point ({entry})...")
                zf.write(entry_path, entry)

        # 2. Wheel files
        print(f"Adding {len(whl_map)} wheel files...")
        for name, whl_path in sorted(whl_map.items()):
            arcname = f"{manifest.WHL_DIR}/{whl_path.name}"
            zf.write(whl_path, arcname)
            print(f"  + {arcname}")
        print()

        # 3. Component assets (files and folders)
        print("Adding component assets...")
        asset_count = add_component_assets(zf, manifest)
        print(f"  Added {asset_count} asset files")
        print()

    # Make the .pyz self-executable (prepend shebang)
    _prepend_shebang(output_path)

    final_size = output_path.stat().st_size
    print()
    print("=" * 60)
    print("  Package created successfully!")
    print(f"  File:    {output_path}")
    print(f"  Size:    {format_size(final_size)}")
    print(f"  Variant: {args.variant}")
    print("=" * 60)
    print()
    print("  To install on Windows:")
    print(f"    python {output_path.name}")
    print()
    print("  To install to a custom directory:")
    print(f"    python {output_path.name} --dest C:\\NXP\\S32DS-AGENTIC-AI")
    print()
    print("  Silent install (no prompts):")
    print(f"    python {output_path.name} --dest C:\\NXP\\S32DS-AGENTIC-AI --yes")
    print()


def _prepend_shebang(pyz_path: Path) -> None:
    """Prepend a Python shebang to make the .pyz directly executable on Unix."""
    shebang = b"#!/usr/bin/env python3\n"
    original = pyz_path.read_bytes()
    if not original.startswith(b"#!"):
        pyz_path.write_bytes(shebang + original)


if __name__ == "__main__":
    main()
