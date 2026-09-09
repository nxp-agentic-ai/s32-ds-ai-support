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

"""Build all MCP sub-packages and the root monorepo meta-package as Python wheels (and optionally sdists).

Usage:
    python build_modules.py                              # build all packages + root (default)
    python build_modules.py --no-root                    # build sub-packages only, skip root
    python build_modules.py --sdist                      # build wheels + sdists
    python build_modules.py --package mcp_freemaster     # build one specific package
    python build_modules.py --outdir my_dist             # custom output directory
    python build_modules.py --clean                      # remove dist/ before building
    python build_modules.py --list                       # list discovered packages and exit
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent.resolve()
PACKAGES_DIR = ROOT / "packages"
DEFAULT_OUTDIR = ROOT / "dist"


def discover_packages() -> list[Path]:
    """Return sorted list of package dirs under packages/ that have a pyproject.toml."""
    return sorted(
        p for p in PACKAGES_DIR.iterdir()
        if p.is_dir() and (p / "pyproject.toml").exists()
    )


def build_package(package_dir: Path, outdir: Path, *, wheel: bool = True, sdist: bool = False) -> bool:
    """Build a single package. Returns True on success, False on failure."""
    cmd = [sys.executable, "-m", "build"]
    if wheel and not sdist:
        cmd.append("--wheel")
    elif sdist and not wheel:
        cmd.append("--sdist")
    # if both, omit flags - build produces both by default
    cmd += ["--outdir", str(outdir), str(package_dir)]

    print(f"\n{'='*60}")
    print(f"Building: {package_dir.name}")
    print(f"Command:  {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        print(f"[OK]    {package_dir.name}")
        return True
    else:
        print(f"[FAILED] {package_dir.name} (exit code {result.returncode})")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build all MCP sub-packages as wheels.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--package", "-p",
        metavar="NAME",
        help="Build only this package (directory name under packages/, e.g. mcp_freemaster).",
    )
    parser.add_argument(
        "--no-root",
        action="store_false",
        dest="include_root",
        help="Skip building the root monorepo meta-package.",
    )
    parser.add_argument(
        "--sdist",
        action="store_true",
        help="Also produce source distributions (.tar.gz) in addition to wheels.",
    )
    parser.add_argument(
        "--outdir", "-o",
        default=str(DEFAULT_OUTDIR),
        metavar="DIR",
        help=f"Output directory for built artifacts (default: {DEFAULT_OUTDIR}).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the output directory before building.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List discovered packages and exit without building.",
    )
    args = parser.parse_args()

    outdir = Path(args.outdir).resolve()
    all_packages = discover_packages()

    # --list
    if args.list:
        print("Discovered packages:")
        for p in all_packages:
            print(f"  {p.name}  ({p})")
        if (ROOT / "pyproject.toml").exists():
            print(f"  [root]   ({ROOT})")
        return

    # --clean
    if args.clean and outdir.exists():
        print(f"Removing {outdir} ...")
        shutil.rmtree(outdir)

    outdir.mkdir(parents=True, exist_ok=True)

    # Select packages to build
    if args.package:
        target = PACKAGES_DIR / args.package
        if not target.exists():
            print(f"ERROR: Package '{args.package}' not found under {PACKAGES_DIR}", file=sys.stderr)
            sys.exit(1)
        if not (target / "pyproject.toml").exists():
            print(f"ERROR: No pyproject.toml found in {target}", file=sys.stderr)
            sys.exit(1)
        packages_to_build = [target]
    else:
        packages_to_build = all_packages

    # Optionally prepend root
    build_targets: list[Path] = []
    if args.include_root and (ROOT / "pyproject.toml").exists():
        build_targets.append(ROOT)
    build_targets.extend(packages_to_build)

    print(f"\nBuilding {len(build_targets)} package(s) -> {outdir}")

    results: dict[str, bool] = {}
    for pkg_dir in build_targets:
        label = pkg_dir.name if pkg_dir != ROOT else "[root]"
        success = build_package(pkg_dir, outdir, wheel=True, sdist=args.sdist)
        results[label] = success

    # Summary
    print(f"\n{'='*60}")
    print("BUILD SUMMARY")
    print(f"{'='*60}")
    passed = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]
    for name in passed:
        print(f"  [OK]     {name}")
    for name in failed:
        print(f"  [FAILED] {name}")
    print(f"\n{len(passed)}/{len(results)} packages built successfully.")

    if failed:
        print(f"\nFailed packages: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)

    print(f"\nArtifacts written to: {outdir}")


if __name__ == "__main__":
    main()
