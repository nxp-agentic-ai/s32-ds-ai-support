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

"""Factory for creating the knowledge MCP server instance."""
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.transforms import Namespace

from nxp.mcp.shared.action import install_envelope_middleware
from nxp.mcp.shared.bootstrap import setup_logging

from nxp.mcp.knowledge.metadata import MCP_SERVER_NAME, MCP_SERVER_VERSION, MCP_SERVER_DESCRIPTION
from nxp.mcp.knowledge.db import KnowledgeStoreRegistry
from nxp.mcp.knowledge.embeddings import create_embedder
from nxp.mcp.knowledge.reranking import create_reranker
from nxp.mcp.knowledge.ingestion import IngestionPipeline
from nxp.mcp.knowledge.server.registration import register_tools, register_resources


def build_mcp_server_config(raw: dict, base_dir: Path | None = None):
    """Build a typed config from a raw dict - called by the gateway composer.

    ``base_dir`` is threaded to the knowledge config loader so that this
    server's relative path fields (db_path, corpora dirs, and pathlike model
    fields) resolve against the config file location.
    """
    from nxp.mcp.knowledge.config import build_mcp_server_config as _build
    return _build(raw, base_dir)


def create_mcp_server(config) -> FastMCP:
    """Instantiate and fully configure the knowledge MCP server.

    Startup sequence:
    1. Set up logging.
    2. Create the embedder (lazy load).
    3. Create the reranker if configured (lazy load).
    4. Open the LanceDB directory and build the per-corpus store registry.
    5. Run the initial ingestion scan over every configured corpus.
    6. Register all tools and resources.
    """
    logger = setup_logging(config.logging, MCP_SERVER_NAME)
    logger.info(
        "Starting server '%s'  version=%s  description=%s",
        MCP_SERVER_NAME,
        MCP_SERVER_VERSION or "n/a",
        MCP_SERVER_DESCRIPTION or "n/a",
    )

    # --- embedder ---------------------------------------------------------
    logger.info(
        "Embedder configured (lazy load): provider=%s  model=%s  device=%s  dimension=%d",
        config.settings.embedder.provider,
        config.settings.embedder.model,
        config.settings.embedder.device,
        config.settings.embedder.dimension,
    )
    embedder = create_embedder(config.settings.embedder)

    # --- reranker (optional) ---------------------------------------------
    rcfg = config.settings.reranker
    if rcfg.enabled:
        logger.info(
            "Reranker configured (lazy load): provider=%s  model=%s  device=%s  "
            "max_length=%d  candidates_multiplier=%d  candidates_max=%d  rerank_budget=%d",
            rcfg.provider, rcfg.model, rcfg.device, rcfg.max_length,
            rcfg.candidates_multiplier, rcfg.candidates_max, rcfg.rerank_budget,
        )
    else:
        logger.info("Reranker disabled - kb_search will return raw vector results")
    reranker = create_reranker(rcfg)

    # --- vector store registry -------------------------------------------
    corpus_names_and_groups = [(c.name, c.group) for c in config.settings.corpora]
    registry = KnowledgeStoreRegistry(
        db_path=config.settings.db_path,
        embedder=embedder,
        corpora=corpus_names_and_groups,
    )
    logger.info(
        "Knowledge store registry opened: db_path=%s  corpora=%s",
        config.settings.db_path,
        corpus_names_and_groups,
    )

    # --- ingestion pipeline ----------------------------------------------
    pipeline = IngestionPipeline(
        registry=registry,
        chunk_size=config.settings.chunk_size,
        chunk_overlap=config.settings.chunk_overlap,
    )

    if config.settings.corpora:
        logger.info("Running initial ingestion across %d corpora", len(config.settings.corpora))
        stats = pipeline.ingest_all_configured(config.settings.corpora)
        logger.info(
            "Initial ingestion complete: ingested=%d  skipped=%d  errors=%d",
            stats["ingested"], stats["skipped"], stats["errors"],
        )
    else:
        logger.info("No corpora configured - skipping initial ingestion")

    # --- optional: build/refresh ANN indexes ---------------
    # This is a no-op unless settings.ann.enabled is True. See AnnSettings
    # for the safety contract - failures never bring the server down; a
    # corpus that fails to index just stays on the linear-scan fallback.
    acfg = config.settings.ann
    corpus_names = registry.names()
    if acfg.enabled and corpus_names:
        logger.info(
            "Building ANN indexes (IVF_PQ): min_rows=%d  nprobes=%d  "
            "num_partitions=%s  num_sub_vectors=%s  rebuild_on_startup=%s",
            acfg.min_rows_for_index, acfg.nprobes,
            acfg.num_partitions, acfg.num_sub_vectors, acfg.rebuild_on_startup,
        )
        summary = {"built": 0, "already_indexed": 0, "skipped_too_small": 0, "failed": 0}
        for name in corpus_names:
            store = registry.get(name)
            res = store.ensure_ann_index(
                min_rows=acfg.min_rows_for_index,
                num_partitions=acfg.num_partitions,
                num_sub_vectors=acfg.num_sub_vectors,
                force=acfg.rebuild_on_startup,
            )
            summary[res["status"]] = summary.get(res["status"], 0) + 1
        logger.info(
            "ANN index summary: built=%d  already_indexed=%d  "
            "skipped_too_small=%d  failed=%d",
            summary["built"], summary["already_indexed"],
            summary["skipped_too_small"], summary["failed"],
        )
    else:
        logger.info(
            "ANN indexing disabled (settings.ann.enabled=%s) - "
            "kb_search will use linear scan on every corpus",
            acfg.enabled,
        )

    # --- FastMCP server ---------------------------------------------------
    server = FastMCP(
        name=MCP_SERVER_NAME,
        version=MCP_SERVER_VERSION,
        instructions=MCP_SERVER_DESCRIPTION,
        transforms=[Namespace(config.namespace.format(server_name=MCP_SERVER_NAME))]
    )

    install_envelope_middleware(server)
    register_tools(server, config, registry, pipeline, reranker=reranker)
    register_resources(server, config, registry, pipeline)

    logger.info("Knowledge server ready")
    return server
