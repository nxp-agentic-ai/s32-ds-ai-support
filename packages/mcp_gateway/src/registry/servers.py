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

"""
MCP server registry for the gateway.

Server packages are discovered dynamically via Python package entry-points.
Each server package self-registers under the ``mcp.servers`` group
in its own ``pyproject.toml``::

    [project.entry-points."nxp.mcp.servers"]
    template = "nxp.mcp.template"

Install all server packages editably (``pip install -r requirements.txt``)
so their entry-points are registered in the Python environment.  The gateway
then discovers them automatically at startup — no gateway code changes are
needed when a new server is added or an existing one is updated.

Metadata (description, version) is read from each installed package via
``importlib.metadata`` and resolves individually per package.
"""

from importlib.metadata import metadata as pkg_meta, PackageNotFoundError

from nxp.mcp.shared.models.server import McpServerRegistryEntry

from .discovery import discover_mcp_servers


def _build_registry() -> dict[str, McpServerRegistryEntry]:
    """Build registry from dynamically discovered entry-points."""
    discovered = discover_mcp_servers()
    registry: dict[str, McpServerRegistryEntry] = {}
    for name, path in discovered.items():
        # Derive the installed package name from the module path:
        # "nxp.mcp.template" → "nxp-mcp-template"
        package_name = path.replace("_", "-").replace(".", "-")
        try:
            m = pkg_meta(package_name)
            registry[name] = McpServerRegistryEntry(
                module_path=path,
                version=m["Version"] or "",
                description=m["Summary"] or "",
            )
        except PackageNotFoundError:
            registry[name] = McpServerRegistryEntry(module_path=path)
    return registry


# Module-level singleton — consumed by the gateway composer
MCP_SERVER_REGISTRY: dict[str, McpServerRegistryEntry] = _build_registry()
