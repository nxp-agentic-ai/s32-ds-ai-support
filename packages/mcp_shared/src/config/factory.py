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

"""Generic config-building helpers shared across all MCP server factory.py files.

Usage in a server factory::

    from nxp.mcp.shared.config.factory import build_mcp_server_config
    from nxp.mcp.template.config.models import TemplateMcpServerConfig, TemplateSettings

    def build_mcp_server_config(raw: dict, base_dir=None) -> TemplateMcpServerConfig:
        return build_mcp_server_config(raw, TemplateSettings, TemplateMcpServerConfig, base_dir)
"""
from pathlib import Path
from typing import TypeVar

from nxp.mcp.shared.config.models import BaseMcpServerConfig, LoggingSettings
from nxp.mcp.shared.config.paths import resolve_path

S = TypeVar("S")
C = TypeVar("C", bound=BaseMcpServerConfig)


def build_mcp_server_config(
    raw: dict,
    settings_cls: type[S],
    config_cls: type[C],
    base_dir: Path | None = None,
) -> C:
    """Instantiate an MCP server config dataclass from a raw YAML dict.

    Args:
        raw:          Parsed YAML dictionary (top-level keys: ``logging``,
                      ``settings``).
        settings_cls: Server-specific settings dataclass (e.g. ``DemoSettings``).
        config_cls:   Server config dataclass that subclasses
                      :class:`~mcp_shared.config.models.BaseMcpServerConfig`
                      and has a ``settings`` field of type *settings_cls*.
        base_dir:     Directory that relative path fields are resolved against
                      (typically the config file's parent). When ``None`` no
                      path resolution is performed (embedded-defaults path).

    Returns:
        A fully-populated instance of *config_cls*.

    Note:
        Only the base-class path fields ``logging.file`` and ``skills`` are
        resolved here. Server-specific path fields living inside ``settings``
        must be resolved by that server's own factory, since only the
        component knows which of its settings are file-system paths.
    """
    logging = LoggingSettings(**raw.get("logging", {}))
    skills = raw.get("skills", "")
    if base_dir is not None:
        logging.file = resolve_path(logging.file, base_dir)
        skills = resolve_path(skills, base_dir)
    return config_cls(
        logging=logging,
        settings=settings_cls(**raw.get("settings", {})),
        skills=skills,
        namespace=raw.get("namespace", "nxp_{server_name}"),
    )
