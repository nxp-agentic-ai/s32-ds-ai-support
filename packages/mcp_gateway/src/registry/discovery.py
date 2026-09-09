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
Dynamic server discovery via Python package entry-points.

Each server package self-registers under the :data:`MCP_SERVERS_ENTRY_POINT_GROUP`
group in its ``pyproject.toml``::

    [project.entry-points."nxp.mcp.servers"]
    template = "nxp.mcp.template"

The gateway calls :func:`discover_mcp_servers` at startup; no gateway code
needs to change when a new server is installed or an existing one is
extracted to an independent package.

The entry-point group string is defined once in
:mod:`nxp.mcp.shared.metadata` and imported here to avoid duplication.
"""

from importlib.metadata import entry_points

from nxp.mcp.shared.metadata import MCP_SERVERS_ENTRY_POINT_GROUP
from nxp.mcp.gateway.metadata.server import MCP_SERVER_NAME as _GATEWAY_NAME


def discover_mcp_servers() -> dict[str, str]:
    """Return ``{server_name: module_path}`` for all installed servers.

    Falls back to an empty dict if no entry-points are registered (e.g. when
    running from source without ``pip install -e .``).
    """
    eps = entry_points(group=MCP_SERVERS_ENTRY_POINT_GROUP)
    return {ep.name: ep.value for ep in eps if ep.name != _GATEWAY_NAME}
