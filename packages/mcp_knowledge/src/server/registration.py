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

"""Register all tools and resources on the knowledge MCP server."""
import logging

from nxp.mcp.shared.action import StandardizingServer

from nxp.mcp.knowledge.metadata.server import MCP_SERVER_NAME
from nxp.mcp.knowledge.tools import register_search_tool, register_ingest_tools
from nxp.mcp.knowledge.resources import register_info_resources

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_tools(server, config, registry, pipeline, reranker=None) -> None:
    """Register the knowledge tools with the standardized response envelope.

    The knowledge tools raise plain exceptions (e.g. ``ValueError`` for an
    unknown corpus) and return bare payloads. Registering through
    ``StandardizingServer`` converts those failures into the shared
    ``{success: false, error: {...}}`` envelope so an agent can tell that - and
    why - a call failed, instead of receiving an opaque protocol error.
    """

    standardized = StandardizingServer(server, component_logger=_logger)
    rcfg = config.settings.reranker
    scfg = config.settings.search
    acfg = config.settings.ann
    register_search_tool(
        standardized,
        registry,
        reranker=reranker,
        candidates_multiplier=rcfg.candidates_multiplier,
        candidates_max=rcfg.candidates_max,
        rerank_budget=rcfg.rerank_budget,
        max_workers=scfg.max_workers,
        ann_enabled=acfg.enabled,
        ann_nprobes=acfg.nprobes,
    )
    if config.settings.mutable:
        register_ingest_tools(standardized, pipeline)


def register_resources(server, config, registry, pipeline) -> None:
    register_info_resources(server, config, registry, pipeline)
