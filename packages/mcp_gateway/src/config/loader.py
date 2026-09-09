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

from pathlib import Path

import yaml

from nxp.mcp.gateway.config.models import GatewayConfig, GatewaySettings, HttpSettings
from nxp.mcp.shared.config.models import LoggingSettings
from nxp.mcp.shared.config.paths import resolve_path



def load_gateway_config(path: str | None = None) -> GatewayConfig:
    """Load a gateway config from a YAML file, or use embedded defaults.

    When *path* is ``None`` the gateway starts with embedded dataclass defaults —
    no file on disk is required.

    Relative path fields are resolved against the directory that contains the
    config file. Only known path fields are resolved: the gateway
    ``logging.file`` and the ``gateway.skills`` list.

    Per-server relative paths are resolved later by each server's factory using
    the ``base_dir`` threaded through :class:`GatewayConfig`.

    Transport selection is determined by the config itself: if the top-level ``http``
    block is present, HTTP (streamable-http) transport is used; otherwise stdio is
    used.
    """
    if path is None:
        return GatewayConfig()
    p = Path(path).resolve()
    base_dir = p.parent
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    gateway_data = data.get("gateway", {})
    http_data = data.get("http", None)

    logging = LoggingSettings(**data.get("logging", {}))
    logging.file = resolve_path(logging.file, base_dir)

    skills = [resolve_path(s, base_dir) for s in gateway_data.get("skills", [])]


    return GatewayConfig(
        logging=logging,
        gateway=GatewaySettings(
            strict_startup=gateway_data.get("strict_startup", True),
            skills=skills,
        ),
        http=HttpSettings(**http_data) if http_data is not None else None,
        servers=data.get("servers", {}),
        base_dir=base_dir,
    )
