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

from nxp.mcp.shared.action import install_envelope_middleware
from nxp.mcp.shared.bootstrap import setup_logging
from nxp.mcp.gateway.config.models import GatewayConfig
from nxp.mcp.gateway.metadata.server import MCP_SERVER_NAME, MCP_SERVER_VERSION, MCP_SERVER_DESCRIPTION
from nxp.mcp.gateway.mounting.composer import mount_mcp_servers


def create_gateway_server(config: GatewayConfig) -> FastMCP:
    logger = setup_logging(config.logging, MCP_SERVER_NAME)
    server = FastMCP(
        name=MCP_SERVER_NAME,
        version=MCP_SERVER_VERSION,
        instructions=MCP_SERVER_DESCRIPTION,
    )
    logger.info(
        "Starting server '%s'  version=%s  description=%s",
        server.name,
        server.version or "n/a",
        server.instructions or "n/a",
    )
    # Standardize the request-validation boundary at the gateway so
    # every mounted sub-server inherits it: a bad-argument ValidationError is
    # mapped to the shared error envelope instead of a raw plaintext error, and
    # a JSON-string `params` argument is coerced before validation runs.
    install_envelope_middleware(server)
    mount_mcp_servers(server, config)

    for skills_path in config.gateway.skills:
        p = Path(skills_path)
        if p.exists():
            logger.info("Registering skills from '%s'", p)
            server.add_provider(SkillsDirectoryProvider(p))
        else:
            logger.warning("Skills path does not exist, skipping: '%s'", p)

    return server
