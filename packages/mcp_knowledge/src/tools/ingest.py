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

"""kb_ingest and kb_remove tools - runtime knowledge base management."""
from fastmcp import FastMCP

from nxp.mcp.knowledge.db.registry import UnknownCorpusError
from nxp.mcp.knowledge.ingestion.pipeline import IngestionPipeline


def register_ingest_tools(server: FastMCP, pipeline: IngestionPipeline) -> None:
    """Register ``kb_ingest`` and ``kb_remove`` tools on *server*."""

    @server.tool()
    def kb_ingest(path: str, corpus: str | None = None) -> dict:
        """Ingest a file or directory into a corpus.

        Args:
            path:   Absolute or relative path to a file or directory.
            corpus: Target corpus name. Required when more than one corpus is
                    configured; may be omitted when exactly one corpus exists.

        Returns:
            Dict with keys ``ingested``, ``skipped``, ``errors``, and
            ``corpus`` (the corpus the data was written to).
        """
        try:
            stats = pipeline.ingest_path(path, corpus=corpus)
        except UnknownCorpusError as exc:
            raise ValueError(str(exc)) from exc
        resolved = corpus if corpus is not None else pipeline.registry.default()
        stats["corpus"] = resolved
        return stats

    @server.tool()
    def kb_remove(source: str, corpus: str | None = None) -> dict:
        """Remove all indexed chunks for *source* from a corpus.

        Args:
            source: The source path string exactly as stored.
            corpus: Target corpus name; required when more than one is configured.

        Returns:
            Dict with keys ``removed`` (the source path) and ``corpus``.
        """
        try:
            pipeline.remove(source, corpus=corpus)
        except UnknownCorpusError as exc:
            raise ValueError(str(exc)) from exc
        resolved = corpus if corpus is not None else pipeline.registry.default()
        return {"removed": source, "corpus": resolved}
