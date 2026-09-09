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

"""kb_search and kb_list_corpora tools - semantic search across one or all corpora.

When a reranker is configured, ``kb_search`` runs in three stages:

1. **Per-corpus recall:** the bi-encoder vector search fetches up to
   ``top_k * candidates_multiplier`` (capped at ``candidates_max``)
   candidates from each selected corpus.
2. **Global pre-rerank cut:** the merged candidate pool is sorted by
   vector score and truncated to ``rerank_budget`` items. This keeps
   the cross-encoder cost bounded regardless of how many corpora are
   configured.
3. **Rerank:** the remaining candidates are rescored by a cross-encoder
   on (query, chunk) pairs; the top_k by rerank score are returned.

The original vector-similarity score is preserved on each row as
``vector_score`` for debugging / hybrid-scoring downstream.

Query-embedding reuse
------------------------------------------------
Every store in the registry shares the same
:class:`~mcp_knowledge.embeddings.base.EmbedderProvider`, so the query
embedding is a pure function of the query string and does not depend on
which corpus is being searched. ``kb_search`` therefore embeds the query
**exactly once** via ``registry.embedder`` and passes the resulting
vector to :meth:`KnowledgeStore.search_by_vector` for every selected
corpus. On an N-corpus fan-out this saves ``N - 1`` bi-encoder forward
passes per request.

Parallel per-corpus search
------------------------------------------------------
The per-corpus vector searches are independent - each store owns its
own LanceDB table and shares only the read-only query vector - so they
can be issued concurrently. ``kb_search`` uses a bounded
:class:`~concurrent.futures.ThreadPoolExecutor` when the fan-out
targets more than one corpus. LanceDB read paths release the GIL for
the ANN math, so real wall-clock speedup is observed on multi-core
hosts even under the CPython GIL.

The worker count is chosen with three tiers of precedence:

1. If the ``kb_search`` tool call supplies its own ``max_workers``, that
   value wins (per-call override; agents can force sequential mode or
   over/under-provision for benchmarking).
2. Otherwise the server-configured default from
   ``KnowledgeSettings.search.max_workers`` is used (YAML-tunable).
3. If neither is set, a **CPU-aware default** is derived at import time
   from :func:`_default_max_workers`, currently
   ``min(8, max(2, os.cpu_count() or 4))``.

The single-corpus path stays sequential regardless of the setting to
avoid pool-creation overhead.

ANN indexing
---------------------------------------
When ``KnowledgeSettings.ann.enabled`` is True, per-corpus tables carry
an ``IVF_PQ`` index (see :meth:`KnowledgeStore.ensure_ann_index`) and
this tool passes the configured ``nprobes`` to each per-corpus search
call, accelerating recall by roughly one order of magnitude on
medium-to-large corpora at the cost of a small, tunable recall drop
(typically <5% at nprobes=10).

The feature is **opt-in and fully reversible**:

* ``ann_enabled=False`` (the default) makes ``kb_search`` explicitly
  call ``bypass_vector_index()`` on every per-corpus search, so even
  if an index has been left on disk from a previous session it is not
  consulted. Results are then bit-identical to the pre-index behavior.
* Per-call overrides ``nprobes`` and ``bypass_ann_index`` allow an
  agent to tune recall on the fly (e.g. raise nprobes for a low-recall
  query, or bypass the index entirely for an on-line recall probe).
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from fastmcp import FastMCP

from nxp.mcp.knowledge.metadata import MCP_SERVER_NAME
from nxp.mcp.knowledge.db.registry import KnowledgeStoreRegistry, UnknownGroupError, UnknownCorpusError
from nxp.mcp.knowledge.reranking.base import RerankerProvider

logger = logging.getLogger(MCP_SERVER_NAME)

# Hard upper bound on the fan-out worker count. Beyond ~8 the coordination
# cost dominates for typical KB sizes and the returns diminish sharply, so
# we cap here even on very large hosts. Tune via ``settings.search.max_workers``
# (server-wide) or the ``max_workers`` argument on ``kb_search`` (per-call).
MAX_WORKERS_CEILING = 8

# Minimum worker count when the host reports a very small CPU count (e.g.
# 1-core VMs). Two workers still give useful overlap because LanceDB
# releases the GIL for the ANN math.
MIN_WORKERS_FLOOR = 2


def _default_max_workers() -> int:
    """Return the CPU-aware default worker count for the fan-out.

    Formula: ``min(MAX_WORKERS_CEILING, max(MIN_WORKERS_FLOOR, cpu_count))``
    with ``cpu_count`` falling back to 4 if the OS refuses to report it.

    Examples (with the current ceiling of 8 and floor of 2):
        1-core VM        -> 2 workers  (floor kicks in)
        2-core VM        -> 2 workers
        4-core laptop    -> 4 workers
        8-core desktop   -> 8 workers
        16-core server   -> 8 workers  (ceiling kicks in)
    """
    return min(MAX_WORKERS_CEILING, max(MIN_WORKERS_FLOOR, os.cpu_count() or 4))


# Public snapshot of the default computed once at import time. Kept for
# backward compatibility with callers that used to import ``DEFAULT_MAX_WORKERS``
# directly, and for use as a sentinel in test suites.
DEFAULT_MAX_WORKERS = _default_max_workers()


def register_search_tool(
    server: FastMCP,
    registry: KnowledgeStoreRegistry,
    reranker: RerankerProvider | None = None,
    candidates_multiplier: int = 4,
    candidates_max: int = 50,
    rerank_budget: int = 40,
    max_workers: int | None = None,
    ann_enabled: bool = False,
    ann_nprobes: int = 10,
) -> None:
    """Register ``kb_search`` and ``kb_list_corpora`` tools on *server*.

    Two-stage retrieval with a bounded rerank cost:

    * **Per-corpus recall:** each corpus contributes at most
      ``min(top_k * candidates_multiplier, candidates_max)`` candidates.
      When more than one corpus is targeted, per-corpus searches run
      concurrently on a :class:`ThreadPoolExecutor` sized as described
      in the module docstring.
    * **Global pre-rerank cut:** the merged pool is sorted by vector score
      and truncated to ``rerank_budget`` items before the cross-encoder
      runs. This keeps rerank latency independent of the number of
      corpora configured. Set ``rerank_budget`` to 0 or a negative value
      to disable the global cap (legacy behavior).

    Args:
        server:                 FastMCP server to register on.
        registry:               Multi-corpus knowledge store registry.
        reranker:               Optional cross-encoder reranker. When supplied,
                                results are reranked after the vector search.
        candidates_multiplier:  Overfetch factor per corpus when reranking.
        candidates_max:         Hard ceiling on candidates per corpus.
        rerank_budget:          Global cap on documents sent to the reranker
                                after merging across corpora. 0 or negative
                                disables the cap.
        max_workers:            Server-wide default for the fan-out thread
                                pool. ``None`` (the default) means "derive
                                from ``os.cpu_count()``" via
                                :func:`_default_max_workers`. Agents can
                                override this on individual ``kb_search``
                                calls via the tool's own ``max_workers``
                                argument.
        ann_enabled:            When True, per-corpus searches use whatever
                                ANN index the table carries (with the
                                configured ``ann_nprobes``). When False -
                                the safe default - every per-corpus search
                                calls ``bypass_vector_index()`` so any
                                on-disk index is ignored and results are
                                identical to pre-2.3 behavior.
        ann_nprobes:            Number of IVF partitions probed per query
                                when ``ann_enabled=True``. Ignored on
                                tables without an index.
    """
    # Resolve the server-wide default once. ``None`` from the caller means
    # "use the CPU-aware built-in", which we compute right now (not lazily)
    # so any config-time validation errors surface at server startup rather
    # than at first search.
    server_default_workers = (
        max_workers if max_workers is not None else _default_max_workers()
    )
    logger.info(
        "kb_search: max_workers_default=%d (source=%s, cpu_count=%s)  "
        "ann_enabled=%s  ann_nprobes=%d",
        server_default_workers,
        "config" if max_workers is not None else "cpu-aware",
        os.cpu_count(),
        ann_enabled,
        ann_nprobes,
    )

    @server.tool(description="Search the knowledge base using semantic similarity.")
    def kb_search(
        query: str,
        top_k: int = 5,
        corpus: str | None = None,
        max_workers: int | None = None,
        nprobes: int | None = None,
        bypass_ann_index: bool | None = None,
    ) -> list[dict]:
        """Search one or all configured corpora.

        Args:
            query:              Natural-language query string.
            top_k:              Maximum number of results to return (default 5).
            corpus:             Optional corpus or group name to search. When multiple corpora share
                                the same group, all are searched and results are merged. When omitted,
                                searches all configured corpora. The
                                merged top_k results (by descending score)
                                are returned. Each result row includes the
                                originating ``corpus`` field.
            max_workers:        Per-call override for the fan-out thread
                                pool. Falls back to the server-configured
                                default when omitted. Set to ``1`` to force
                                fully sequential fan-out (useful for
                                deterministic profiling or when debugging
                                thread safety).
            nprobes:            Per-call override for the IVF probe count
                                (section 2.3). Higher = more recall, slower.
                                Ignored on tables without an ANN index.
                                Falls back to the server-configured default
                                (``settings.ann.nprobes``) when omitted.
            bypass_ann_index:   Per-call override to force a brute-force
                                scan even if the table carries an ANN
                                index. ``None`` inherits the server
                                configuration (``settings.ann.enabled``
                                determines whether the index is used at
                                all). Setting ``True`` here at any time is
                                the on-line escape hatch to reproduce
                                pre-index behavior and establish a recall
                                ground truth.

        Returns:
            List of result dicts with ``source``, ``chunk_index``, ``text``,
            ``score``, ``table``. When a reranker is active, ``score`` is
            the cross-encoder rerank score and ``vector_score`` is the
            original cosine similarity from the vector store.
        """
        # Resolve per-call vs server default. We validate the per-call value
        # here rather than in a decorator so the error message is close to
        # the caller.
        if max_workers is not None and max_workers < 1:
            raise ValueError(
                f"kb_search: max_workers must be >= 1 or None, got {max_workers}"
            )
        if nprobes is not None and nprobes < 1:
            raise ValueError(
                f"kb_search: nprobes must be >= 1 or None, got {nprobes}"
            )
        effective_workers = (
            max_workers if max_workers is not None else server_default_workers
        )

        # ANN resolution: three tiers, same pattern as max_workers.
        #  1. per-call bypass_ann_index=True wins (force linear scan).
        #  2. server-wide ann_enabled=False wins (linear scan) unless the
        #     caller explicitly overrode.
        #  3. otherwise ANN is used with per-call nprobes -> server default.
        if bypass_ann_index is True:
            effective_bypass = True
        elif bypass_ann_index is False:
            effective_bypass = False
        else:
            effective_bypass = not ann_enabled
        effective_nprobes = (
            nprobes if nprobes is not None else ann_nprobes
        )

        # important: corpus is practically the group. When a corpus name is
        # supplied it is resolved as a group so that every corpus sharing that
        # group value is searched together and their results combined. A plain
        # corpus without an explicit group defaults to its own name, so this
        # still resolves a single store for ungrouped corpora.
        if corpus is not None:
            try:
                stores = [(store.collection, store) for store in registry.get_by_group(corpus)]
            except UnknownGroupError as exc:
                raise ValueError(str(exc)) from exc
        elif registry.default() is not None:
            name = registry.default()
            stores = [(name, registry.get(name))]
        else:
            # Search every configured corpus and merge.
            stores = registry.items()

        # Overfetch when a reranker is active so it has more material to work with.
        if reranker is not None:
            fetch_k = min(top_k * candidates_multiplier, candidates_max)
        else:
            fetch_k = top_k

        query_vector = registry.embedder.embed([query])[0]

        def _search_one(item):
            name, store = item
            hits = store.search_by_vector(
                query_vector,
                top_k=fetch_k,
                nprobes=effective_nprobes,
                bypass_ann_index=effective_bypass,
            )
            # Materialize into plain dicts inside the worker so the caller
            # only has to concatenate lists (cheap under the GIL).
            return [
                {
                    "table": name,
                    "source": r.source,
                    "chunk_index": r.chunk_index,
                    "text": r.text,
                    "score": r.score,
                    "corpus" : corpus
                }
                for r in hits
            ]

        merged: list[dict] = []
        if len(stores) <= 1 or effective_workers <= 1:
            # Sequential path: no pool overhead for the common single-corpus
            # case or when the caller has explicitly disabled parallelism.
            for item in stores:
                merged.extend(_search_one(item))
        else:
            workers = min(effective_workers, len(stores))
            # ``executor.map`` preserves input order, which keeps the merged
            # list deterministic across runs (matters for stable tie-breaking
            # in the downstream sort and for reproducible tests).
            with ThreadPoolExecutor(
                max_workers=workers,
                thread_name_prefix="kb-search",
            ) as ex:
                for part in ex.map(_search_one, stores):
                    merged.extend(part)
            logger.debug(
                "kb_search: fan-out over %d corpora with %d worker(s), "
                "collected %d candidates (ann_bypass=%s nprobes=%d)",
                len(stores), workers, len(merged),
                effective_bypass, effective_nprobes,
            )

        if reranker is not None and merged:
            # Global pre-rerank cut: sort by vector score descending and keep
            # only the strongest ``rerank_budget`` candidates across ALL
            # corpora. This bounds the cross-encoder cost so it does not scale
            # with the number of configured corpora. The bi-encoder is trusted
            # for gross relevance; the reranker only refines ordering inside
            # this shortlist.
            if rerank_budget and rerank_budget > 0 and len(merged) > rerank_budget:
                merged_before_cut = len(merged)
                merged.sort(key=lambda d: d["score"], reverse=True)
                merged = merged[:rerank_budget]
                logger.info("kb_search: pre-rerank cut %d -> %d candidates for query=%r",
                            merged_before_cut, rerank_budget, query)

            scores = reranker.rerank(query, [d["text"] for d in merged])
            for d, s in zip(merged, scores):
                # Preserve the bi-encoder cosine similarity for inspection /
                # downstream hybrid scoring, then overwrite ``score`` with the
                # cross-encoder rerank score so the standard "higher is better"
                # contract still holds.
                d["vector_score"] = d["score"]
                d["score"] = s

        # Higher score = more relevant (cosine similarity, or rerank score).
        merged.sort(key=lambda d: d["score"], reverse=True)
        return merged[:top_k]

    @server.tool(
        description=(
            "List configured knowledge-base groups and their member corpora "
            "(tables). Groups are the search targets for kb_search; corpora "
            "are the individual table names used by kb_ingest / kb_remove."
        )
    )
    def kb_list_corpora() -> list[dict]:
        """Return the configured groups together with their member corpora.

        Each group can be backed by one or more corpora (LanceDB tables).
        ``kb_search`` targets a *group* (its ``corpus`` argument is resolved
        as a group so every member table is searched and merged), while
        ``kb_ingest`` and ``kb_remove`` operate on an individual *corpus*
        (table) name. Previously this tool exposed only group names, which
        hid the corpus names an agent needs to ingest into or remove from a
        specific table. Returning both makes every valid target discoverable
        from a single call.

        Returns:
            List of dicts in group registration order, each shaped as::

                {
                    "corpora": <group name>,          # kb_search target
                    "tables": [<corpus>, ...],      # kb_ingest / kb_remove targets
                }

            For an ungrouped corpus the group name equals the corpus name and
            ``corpora`` is a single-element list.
        """
        grouped = registry.tables_by_group()
        # Preserve group registration order from registry.groups().
        return [
            {"corpora": group, "tables": grouped[group]}
            for group in registry.groups()
        ]



