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

"""Generic YAML config-loading helpers shared across all MCP server config/loader.py files.

Usage in a server loader::

    from nxp.mcp.shared.config.loader import load_mcp_server_config
    from nxp.mcp.template.config.models import DemoMcpServerConfig, DemoSettings

    def load_standalone_config(path: str | None = None) -> DemoMcpServerConfig:
        return load_mcp_server_config(path, DemoSettings, DemoMcpServerConfig)

When *path* is ``None`` the server starts with embedded dataclass defaults —
no file on disk is required.
"""
from pathlib import Path
from typing import TypeVar

import yaml

from nxp.mcp.shared.config.factory import build_mcp_server_config
from nxp.mcp.shared.config.models import BaseMcpServerConfig

S = TypeVar("S")
C = TypeVar("C", bound=BaseMcpServerConfig)


def load_mcp_server_config(
    path: str | None,
    settings_cls: type[S],
    config_cls: type[C],
) -> C:
    """Load an MCP server config from a YAML file, or use embedded defaults.

    Relative path fields in the file are resolved against the directory that
    contains the config file.


    Args:
        path:         Explicit path supplied by the caller.  When ``None`` the
                      server is initialised from the dataclass default values —
                      no file on disk is required.
        settings_cls: Server-specific settings dataclass (e.g. ``DemoSettings``).
        config_cls:   Server config dataclass subclassing
                      :class:`~mcp_shared.config.models.BaseMcpServerConfig`.

    Returns:
        A fully-populated instance of *config_cls*.
    """
    if path is None:
        return build_mcp_server_config({}, settings_cls, config_cls)
    p = Path(path).resolve()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return build_mcp_server_config(data, settings_cls, config_cls, base_dir=p.parent)
