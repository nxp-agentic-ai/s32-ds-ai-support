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

from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider
from fastmcp.server.transforms import Namespace

from nxp.mcp.shared.action import install_envelope_middleware
from nxp.mcp.shared.bootstrap import setup_logging
from nxp.mcp.shared.config.factory import build_mcp_server_config as _build_config
from nxp.mcp.shared.config.paths import resolve_path

from nxp.mcp.s32ds.config.models import S32dsMcpServerConfig, S32dsSettings, CorpusEntry
from nxp.mcp.s32ds.metadata.server import MCP_SERVER_NAME, MCP_SERVER_VERSION, MCP_SERVER_DESCRIPTION
from nxp.mcp.s32ds.server.registration import register_tools, register_resources, register_prompts


def build_mcp_server_config(raw: dict, base_dir: Path | None = None) -> S32dsMcpServerConfig:
    config = _build_config(raw, S32dsSettings, S32dsMcpServerConfig, base_dir)
    if base_dir is not None:
        s = config.settings
        s.model_path = resolve_path(s.model_path, base_dir)
        for entry in s.corpora.values():
            if isinstance(entry, CorpusEntry):
                entry.index_path = resolve_path(entry.index_path, base_dir)
                entry.metadata_path = resolve_path(entry.metadata_path, base_dir)
    return config



def create_mcp_server(config: S32dsMcpServerConfig) -> FastMCP:
    logger = setup_logging(config.logging, MCP_SERVER_NAME)
    server = FastMCP(
        name=MCP_SERVER_NAME,
        version=MCP_SERVER_VERSION,
        instructions=MCP_SERVER_DESCRIPTION,
        transforms=[Namespace(config.namespace.format(server_name=MCP_SERVER_NAME))]
    )

    logger.info(
        "Starting server '%s'  version=%s  description=%s",
        server.name,
        server.version or "n/a",
        server.instructions or "n/a",
    )

    install_envelope_middleware(server)
    register_tools(server, config)
    register_resources(server, config)
    register_prompts(server, config)
    if config.skills:
        logger.info("Registering skills from '%s'", config.skills)
        server.add_provider(SkillsDirectoryProvider(config.skills))
    return server

