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

"""Shared manifest for the NXP MCP installer.

This module is the single source of truth for all values shared between the
package-creation script (scripts/create_deploy_package.py) and the installer
entry point (scripts/installer/__main__.py).  It is bundled verbatim into
every .pyz archive so both sides read from the same data.

Path strings in component definitions are relative to the repository root.
create_deploy_package.py resolves them against PROJECT_ROOT at build time; the
installer discovers assets by scanning the archive.

The shared utility helpers (normalize, whl_dist_name, required_whl_names) live
here so both the build script and the installer read from one implementation.
_manifest_extended.py re-exports them so the installer sees the same API
whichever manifest was bundled.
"""

import re
from pathlib import Path

# Installer version.
# "@@VERSION@@" is a placeholder replaced by create_deploy_package.py at
# bundle time.  The --version CLI argument (or the root pyproject.toml
# version when omitted) is substituted in-memory before the manifest is
# written into the .pyz archive.  This file is never modified on disk.
VERSION = "@@VERSION@@"

# Archive prefix where wheel files are staged inside the .pyz.
WHL_DIR = "whl"

# Archive entries that belong to the installer itself and must not be
# extracted to the installation destination.
INSTALLER_ENTRIES = frozenset(
    {"__main__.py", "_manifest.py"}
)

# Name of the reserved component holding shared assets that are always
# installed regardless of which components the user selects.
DEFAULT_COMPONENT = "common"


# --- Shared utilities --------------------------------------------------------
# Single source of truth for package-name and wheel handling.  Imported by both
# create_deploy_package.py (build time) and __main__.py (install time), and
# re-exported by _manifest_extended.py.

def normalize(name: str) -> str:
    """Normalise a package name: lower-case, collapse [-_.]+ to '-'."""
    return re.sub(r"[-_.]+", "-", name).lower()


def whl_dist_name(filename) -> str:
    """Return the normalised distribution name from a wheel filename or path.

    Wheel filenames are: {name}-{ver}-{pyver}-{abi}-{plat}.whl
    PEP 427 mandates the name component uses '_' instead of '-'; both are
    normalised to '-' so comparisons are reliable.
    """
    return normalize(Path(str(filename)).name.split("-")[0])


def required_whl_names(components: dict) -> set:
    """Return the set of normalised wheel names referenced by all components."""
    return {
        normalize(whl)
        for comp in components.values()
        for whl in comp.get("whl", [])
    }


# A component (MCP server) definition.
# - whl:     list[str]                 - repo-root-relative wheel paths (or dist glob keys)
# - files:   list[tuple[str, str]]     - (source_file,   dest_file)
# - folders: list[tuple]               - (source_folder, dest_folder) or
#                                        (source_folder, dest_folder, [excludes])
#                                        where [excludes] is a list of
#                                        source-relative subpaths to skip.
# All source paths are repo-root-relative; dest paths are archive-relative.

COMPONENTS = {
    DEFAULT_COMPONENT: {
        "whl": ["nxp-mcp-shared"],        # shared wheels resolved from pyproject
        "files": [
            ("LICENSE", "LICENSE"),
            ("LICENSE_ADDENDUM", "LICENSE_ADDENDUM"),
            ("SBOM-S32-DS-Agentic-AI.spdx.json", "SBOM.spdx.json"),
            ("README.md", "README.md"),
            ("run-mcp.bat", "run-mcp.bat"),
            ("run-mcp.sh", "run-mcp.sh"),
            ("scripts/installer/register_agents.py", "register_agents.py"),
        ],
        "folders": [],
    },
    "gateway": {
        "whl": ["nxp-mcp-gateway"],       # matched against dist/*.whl by normalized name
        "files": [
            ("configs/gateway.stdio.yaml", "configs/gateway.stdio.yaml"),
            ("configs/gateway.http.yaml", "configs/gateway.http.yaml")
        ],
        "folders": [],
    },
    "knowledge":  {
        "whl": ["nxp-mcp-knowledge"],
        "files": [
            ("configs/knowledge.standalone.yaml", "configs/knowledge.standalone.yaml"),
            ("models/CACHEDIR.TAG", "models/CACHEDIR.TAG")
        ],
        "folders": [
            ("models/models--BAAI--bge-base-en-v1.5", "models/models--BAAI--bge-base-en-v1.5")
        ]
    },
    "compiler":   {
        "whl": ["nxp-mcp-compiler"],
        "files": [
            ("configs/compiler.standalone.yaml", "configs/compiler.standalone.yaml")
        ],
        "folders": [
            ("knowledge_db/bge-base-en-v1.5/compiler.lance", "knowledge_db/bge-base-en-v1.5/compiler.lance"),
            ("skills/compiler", "skills/compiler")
        ]
    },
    "freemaster":   {
        "whl": ["nxp-mcp-freemaster"],
        "files": [
            ("configs/freemaster.standalone.yaml", "configs/freemaster.standalone.yaml")
        ],
        "folders": [
            ("knowledge_db/bge-base-en-v1.5/freemaster.lance", "knowledge_db/bge-base-en-v1.5/freemaster.lance"),
            ("skills/freemaster", "skills/freemaster")
        ]
    },
    "s32ct":   {
        "whl": ["nxp-mcp-s32ct"],
        "files": [
            ("configs/s32ct.standalone.yaml", "configs/s32ct.standalone.yaml")
        ],
        "folders": [
            ("knowledge_db/bge-base-en-v1.5/s32ct.lance", "knowledge_db/bge-base-en-v1.5/s32ct.lance"),
            ("skills/s32ct", "skills/s32ct")
        ]
    },
    "s32debugger":   {
        "whl": ["nxp-mcp-s32debugger"],
        "files": [
            ("configs/s32debugger.standalone.yaml", "configs/s32debugger.standalone.yaml")
        ],
        "folders": [
            ("knowledge_db/bge-base-en-v1.5/s32debugger.lance", "knowledge_db/bge-base-en-v1.5/s32debugger.lance"),
            ("skills/s32debugger", "skills/s32debugger", ["internal"])
        ]
    },
    "s32ds":   {
        "whl": ["nxp-mcp-s32ds"],
        "files": [
            ("configs/s32ds.standalone.yaml", "configs/s32ds.standalone.yaml")
        ],
        "folders": [
            ("knowledge_db/bge-base-en-v1.5/s32ds.lance", "knowledge_db/bge-base-en-v1.5/s32ds.lance"),
            ("skills/s32ds", "skills/s32ds")
        ]
    },
    "s32flashtool":   {
        "whl": ["nxp-mcp-s32flashtool"],
        "files": [
            ("configs/s32flashtool.standalone.yaml", "configs/s32flashtool.standalone.yaml")
        ],
        "folders": [
            ("knowledge_db/bge-base-en-v1.5/s32flashtool.lance", "knowledge_db/bge-base-en-v1.5/s32flashtool.lance"),
            ("skills/s32flashtool", "skills/s32flashtool")
        ]
    },
    "s32sdaf":   {
        "whl": ["nxp-mcp-s32sdaf"],
        "files": [
            ("configs/s32sdaf.standalone.yaml", "configs/s32sdaf.standalone.yaml")
        ],
        "folders": [
            ("knowledge_db/bge-base-en-v1.5/s32sdaf.lance", "knowledge_db/bge-base-en-v1.5/s32sdaf.lance"),
            ("skills/s32sdaf", "skills/s32sdaf")
        ]
    },
    "s32trace":   {
        "whl": ["nxp-mcp-s32trace"],
        "files": [
            ("configs/s32trace.standalone.yaml", "configs/s32trace.standalone.yaml")
        ],
        "folders": [
            ("knowledge_db/bge-base-en-v1.5/s32trace.lance", "knowledge_db/bge-base-en-v1.5/s32trace.lance"),
            ("skills/s32trace", "skills/s32trace")
        ]
    }
}

