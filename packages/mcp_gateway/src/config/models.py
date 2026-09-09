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

from dataclasses import dataclass, field
from pathlib import Path

from nxp.mcp.shared.config.models import LoggingSettings


@dataclass(slots=True)
class HttpSettings:
    host: str = "127.0.0.1"
    port: int = 8080


@dataclass(slots=True)
class GatewaySettings:
    strict_startup: bool = True
    skills: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GatewayConfig:
    """Top-level gateway configuration.

    Servers are mounted by default (opt-out semantics): a server is skipped
    only when ``disabled: true`` appears in its own per-server block.

    Transport selection: if the top-level ``http`` block is present, HTTP
    (streamable-http) transport is used; otherwise stdio is used.

    ``base_dir`` carries the directory of the loaded config file so that
    relative path fields of each mounted server can be resolved against the
    config file location. It is ``None`` when the gateway starts from embedded
    defaults (no file).

    """

    logging: LoggingSettings = field(default_factory=LoggingSettings)
    gateway: GatewaySettings = field(default_factory=GatewaySettings)
    http: HttpSettings | None = None
    servers: dict = field(default_factory=dict)
    base_dir: Path | None = None
