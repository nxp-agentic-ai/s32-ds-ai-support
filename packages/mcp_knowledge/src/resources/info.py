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

"""info:// resources - server, corpora, stats and sources summaries."""
from fastmcp import FastMCP

from nxp.mcp.knowledge.db.registry import KnowledgeStoreRegistry
from nxp.mcp.knowledge.ingestion.pipeline import IngestionPipeline


def register_info_resources(
    server: FastMCP,
    config,
    registry: KnowledgeStoreRegistry,
    pipeline: IngestionPipeline,
) -> None:
    """Register ``info://`` resources on *server*.

    Exposes:
      - ``info://corpora`` - list of configured corpus names with per-corpus stats.
      - ``info://stats``   - aggregated server / index statistics.
      - ``info://sources`` - mapping of ``corpus -> {source: chunk_count}``.
    """

    # ----- helpers -----------------------------------------------------
    corpora_settings = list(config.settings.corpora)
    dirs_by_corpus = {c.name: list(c.dirs) for c in corpora_settings}

    def _per_corpus_stats() -> list[dict]:
        out: list[dict] = []
        for name in registry.names():
            store = registry.get(name)
            s = store.stats()
            out.append({
                "name": name,
                "total_chunks": s["total_chunks"],
                "indexed_sources": len(store.list_sources()),
                "dirs": dirs_by_corpus.get(name, []),
                # ANN index snapshot (section 2.3). Present when the table
                # carries a vector index; identifies index_type + name.
                "ann_index": s.get("ann_index", {"present": False}),
            })
        return out

    # ----- resources ---------------------------------------------------
    @server.resource("info://corpora")
    def kb_corpora() -> dict:
        """Configured corpora with per-corpus chunk and source counts."""
        return {"corpora": _per_corpus_stats()}

    @server.resource("info://stats")
    def kb_stats() -> str:
        """Aggregated knowledge-server state across all corpora."""
        per = _per_corpus_stats()
        total_chunks = sum(c["total_chunks"] for c in per)
        total_sources = sum(c["indexed_sources"] for c in per)
        try:
            embedding_dim = registry.embedder.dimension
        except Exception:
            embedding_dim = 0
        lines = [
            "mcp_server: knowledge",
            f"db_path: {config.settings.db_path}",
            f"corpora: {', '.join(c['name'] for c in per) or '(none configured)'}",
            f"total_chunks: {total_chunks}",
            f"embedding_dimension: {embedding_dim}",
            f"indexed_sources: {total_sources}",
            f"supported_extensions: {', '.join(sorted(pipeline.supported_extensions))}",
        ]
        # Top-line ANN summary so operators can tell at a glance if
        # settings.ann.enabled took effect this session.
        ann_present = sum(1 for c in per if c.get("ann_index", {}).get("present"))
        ann_configured = getattr(config.settings.ann, "enabled", False)
        lines.append(
            f"ann_indexes: enabled_in_config={ann_configured}  "
            f"present_on_disk={ann_present}/{len(per)}"
        )
        for c in per:
            ann = c.get("ann_index", {}) or {}
            if ann.get("present"):
                ann_str = f" ann={ann.get('index_type') or 'yes'}"
            else:
                ann_str = " ann=linear"
            lines.append(
                f"  - {c['name']}: chunks={c['total_chunks']} "
                f"sources={c['indexed_sources']}{ann_str} "
                f"dirs={', '.join(c['dirs']) or '(none)'}"
            )
        return "\n".join(lines)

    @server.resource("info://sources")
    def kb_sources() -> dict:
        """Sources indexed per corpus.

        Returns:
            Dict mapping ``corpus_name -> {source_path: chunk_count}``.
        """
        return {name: registry.get(name).list_sources() for name in registry.names()}
