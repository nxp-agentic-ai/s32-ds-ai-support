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

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from fastmcp import FastMCP


@dataclass(slots=True)
class McpServerRegistryEntry:
    module_path: str
    version: str = ""
    description: str = ""


@runtime_checkable
class McpServerModule(Protocol):
    """
    Structural protocol that every MCP server package must satisfy.

    The gateway discovers this contract at runtime (isinstance check) and
    statically via mypy.  Each server's ``__init__.py`` must export all
    four symbols listed below.

    ``build_mcp_server_config`` accepts an optional ``base_dir`` used to
    resolve relative path configuration fields against the config file
    location. When ``None`` (embedded defaults) no resolution is performed.
    """

    MCP_SERVER_NAME: str

    def build_mcp_server_config(self, raw: dict, base_dir: Path | None = None) -> object: ...
    def create_mcp_server(self, config: object) -> FastMCP: ...
    def run_stdio(self, config: object) -> None: ...
