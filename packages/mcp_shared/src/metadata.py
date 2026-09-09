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

"""Unified package metadata resolution for MCP server packages.

Resolves the entry-point name, version, and description for an MCP server
package by querying ``importlib.metadata`` (fast path when installed) or
reading ``pyproject.toml`` directly (source-only fallback).

Usage in any server's ``metadata/server.py``::

    from pathlib import Path
    from nxp.mcp.shared.metadata import resolve_mcp_server_metadata

    _PROJECT_ROOT = Path(__file__).parent.parent.parent

    MCP_SERVER_NAME, MCP_SERVER_VERSION, MCP_SERVER_DESCRIPTION = (
        resolve_mcp_server_metadata("nxp-mcp-<name>", _PROJECT_ROOT)
    )

The constant :data:`MCP_SERVERS_ENTRY_POINT_GROUP` is the single authoritative
definition of the entry-point group name used by all MCP server packages.
Import it wherever the group name is needed (e.g. the gateway discovery
module) so it is never duplicated as a string literal.
"""
import tomllib
from pathlib import Path
from importlib.metadata import distribution, PackageNotFoundError

#: Entry-point group under which every MCP server package self-registers.
#: Defined once here; imported by both this module and the gateway discovery.
MCP_SERVERS_ENTRY_POINT_GROUP = "nxp.mcp.servers"


def resolve_mcp_server_metadata(
    package_name: str, project_root: str | Path
) -> tuple[str, str, str]:
    """Return ``(entry_point_name, version, description)`` for an MCP server.

    Resolution order:

    1. **Installed metadata** (``importlib.metadata``) — used whenever the
       package has been installed (e.g. via ``pip install -e .``).

       * The distribution is looked up directly by *package_name* — an O(1)
         lookup with no namespace ambiguity.
       * The entry-point key registered under
         :data:`MCP_SERVERS_ENTRY_POINT_GROUP` is used as the server name
         (``MCP_SERVER_NAME``).

    2. **Source pyproject.toml** — used when running directly from source
       without installation.  The file is read from *project_root* directly
       (``project_root / "pyproject.toml"``).

    3. **Empty strings** — graceful fallback if neither source is available.

    Args:
        package_name:  The pip distribution name, e.g. ``"nxp-mcp-freemaster"``.
                       Matches the ``[project] name`` field in ``pyproject.toml``.
        project_root:  Path to the directory that contains ``pyproject.toml``
                       for the calling server package (used only in the
                       source-fallback path).

    Returns:
        A three-tuple ``(entry_point_name, version, description)``.
    """
    # --- Fast path: installed package metadata ---
    try:
        dist = distribution(package_name)
        ep_name = next(
            (ep.name for ep in dist.entry_points
             if ep.group == MCP_SERVERS_ENTRY_POINT_GROUP),
            "",
        )
        m = dist.metadata
        return ep_name, m["Version"] or "", m["Summary"] or ""
    except PackageNotFoundError:
        pass

    # --- Fallback: read pyproject.toml from the project root ---
    toml_path = Path(project_root) / "pyproject.toml"
    try:
        with toml_path.open("rb") as f:
            data = tomllib.load(f)
        proj = data.get("project", {})
        ep_name = next(
            iter(
                proj.get("entry-points", {})
                    .get(MCP_SERVERS_ENTRY_POINT_GROUP, {})
                    .keys()
            ),
            "",
        )
        return ep_name, proj.get("version", ""), proj.get("description", "")
    except Exception:
        return "", "", ""
