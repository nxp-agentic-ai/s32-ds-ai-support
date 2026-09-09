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

"""Ingestion pipeline - discovers files, parses, chunks, and upserts into a corpus."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from .chunker import chunk_text
from .parsers import get_parser, supported_extensions
from nxp.mcp.knowledge.metadata import MCP_SERVER_NAME
from nxp.mcp.knowledge.db.store import KnowledgeStore
from nxp.mcp.knowledge.db.registry import KnowledgeStoreRegistry

logger = logging.getLogger(MCP_SERVER_NAME)


class IngestionPipeline:
    """Orchestrates file discovery, parsing, chunking, and vector upsert.

    Each public ingest/remove method takes a ``corpus`` argument selecting
    which table within the registry to write to. ``corpus=None`` resolves
    to the registry's default corpus (only valid when exactly one corpus
    is configured).

    Args:
        registry:      :class:`KnowledgeStoreRegistry` providing per-corpus stores.
        chunk_size:    Maximum words per chunk.
        chunk_overlap: Overlap words between consecutive chunks.
    """

    def __init__(
        self,
        registry: KnowledgeStoreRegistry,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> None:
        self._registry = registry
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def registry(self) -> KnowledgeStoreRegistry:
        return self._registry

    def ingest_path(self, path: str | Path, corpus: str | None = None) -> dict:
        """Ingest a single file or recursively ingest a directory into *corpus*.

        Args:
            path:   File or directory path to ingest.
            corpus: Target corpus name; ``None`` falls back to the registry default.

        Returns:
            Dict with keys ``ingested``, ``skipped``, ``errors``.
        """
        store = self._registry.resolve(corpus)
        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        files = [target] if target.is_file() else [f for f in target.rglob("*") if f.is_file()]

        ingested = skipped = errors = 0
        for file_path in sorted(files):
            result = self._ingest_file(file_path, store)
            if result == "ingested":
                ingested += 1
            elif result == "skipped":
                skipped += 1
            else:
                errors += 1

        logger.info(
            "Ingestion complete for '%s' (corpus=%s): ingested=%d skipped=%d errors=%d",
            path, store.collection, ingested, skipped, errors,
        )
        return {"ingested": ingested, "skipped": skipped, "errors": errors}

    def ingest_dirs(self, dirs: Iterable[str], corpus: str | None = None) -> dict:
        """Ingest all files across multiple directories into *corpus*."""
        total = {"ingested": 0, "skipped": 0, "errors": 0}
        for d in dirs:
            try:
                result = self.ingest_path(d, corpus=corpus)
                for key in total:
                    total[key] += result[key]
            except FileNotFoundError as exc:
                logger.warning("Skipping non-existent dir '%s': %s", d, exc)
        return total

    def ingest_all_configured(self, corpora) -> dict:
        """Run startup ingestion: for every configured corpus, scan its dirs.

        Args:
            corpora: Iterable of objects with ``name`` and ``dirs`` attributes
                     (typically :class:`CorpusSettings` instances).

        Returns:
            Aggregated stats across every corpus.
        """
        total = {"ingested": 0, "skipped": 0, "errors": 0}
        for c in corpora:
            if not c.dirs:
                logger.info("Corpus '%s' has no dirs - skipping", c.name)
                continue
            logger.info("Ingesting corpus '%s' from dirs: %s", c.name, list(c.dirs))
            result = self.ingest_dirs(c.dirs, corpus=c.name)
            for key in total:
                total[key] += result[key]
        return total

    def remove(self, source: str, corpus: str | None = None) -> None:
        """Remove all chunks for a given source path from *corpus*."""
        store = self._registry.resolve(corpus)
        store.delete(source)
        logger.info("Removed source '%s' from corpus '%s'", source, store.collection)

    @property
    def supported_extensions(self) -> frozenset[str]:
        """File extensions that can be parsed by the registry."""
        return supported_extensions()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ingest_file(self, path: Path, store: KnowledgeStore) -> str:
        """Parse, chunk, and upsert a single file into *store*."""
        parser = get_parser(path)
        if parser is None:
            logger.debug("No parser for '%s' (%s) - skipping", path.name, path.suffix)
            return "skipped"

        source = str(path)

        try:
            raw = path.read_bytes()
        except OSError as exc:
            logger.warning("Cannot read '%s': %s", source, exc)
            return "error"

        file_hash = store._file_hash(raw)
        if store.is_current(source, file_hash):
            logger.debug("Unchanged '%s' - skipping", source)
            return "skipped"

        try:
            text = parser.parse(path)
        except Exception as exc:
            logger.warning("Parse error for '%s': %s", source, exc)
            return "error"

        if not text.strip():
            logger.debug("Empty content for '%s' - skipping", source)
            return "skipped"

        chunks = chunk_text(text, self._chunk_size, self._chunk_overlap)
        if not chunks:
            return "skipped"

        try:
            count = store.upsert(source, chunks, source_hash=file_hash)
            logger.debug("Ingested '%s' -> %d chunks", source, count)
            return "ingested"
        except Exception as exc:
            logger.warning("Store error for '%s': %s", source, exc)
            return "error"
