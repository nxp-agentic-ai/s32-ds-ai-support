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

"""LanceDB-backed vector store for the knowledge base.

Vector-search operations run on the ``vector`` column and are agnostic
to whether that column carries an ANN (approximate nearest neighbor)
index. When an ``IVF_PQ`` index is present, LanceDB accelerates the
search using inverted files + product quantization; when it is absent,
the same call falls back to a brute-force scan. The public search API
is therefore stable across the two configurations - see
:meth:`KnowledgeStore.search_by_vector`.

Index lifecycle helpers are exposed under three carefully-scoped methods:

* :meth:`KnowledgeStore.ensure_ann_index` - idempotent build; skips
  tables below a configurable row threshold and never raises on
  build failure (falls back to linear scan silently).
* :meth:`KnowledgeStore.drop_ann_index` - one-command rollback that
  removes every vector-column index the table currently carries. Row
  data is untouched.
* :meth:`KnowledgeStore.ann_index_info` - read-only inspection used by
  the ``info://stats`` resource so operators can see which corpora are
  indexed and with what parameters.
"""
import hashlib
import logging
import math
import time
from pathlib import Path
import pyarrow as pa

from .schema import make_schema
from nxp.mcp.knowledge.metadata import MCP_SERVER_NAME
from nxp.mcp.knowledge.db.models import SearchResult
from nxp.mcp.knowledge.embeddings.base import EmbedderProvider

logger = logging.getLogger(MCP_SERVER_NAME)

# ---------------------------------------------------------------------------
# ANN index defaults
#
# These are chosen to be safe for the small-to-medium corpora typical of a
# knowledge-base MCP server (a few hundred to a few tens of thousands of
# chunks per corpus). Every value can be overridden via config; the
# derivation rules are documented next to each constant so operators can
# tune with confidence.
# ---------------------------------------------------------------------------

# Below this row count, an ANN index is counter-productive - the index
# metadata / partition overhead exceeds a brute-force scan of the raw
# vectors. LanceDB will still let you build an index on very small tables
# but the win is negative. 256 is conservative: it comfortably covers the
# tiny satellite corpora (compiler=10 rows, s32flashtool=108 rows) that
# would gain nothing from an index, while still indexing anything of
# meaningful size.
DEFAULT_MIN_ROWS_FOR_INDEX = 256

# num_partitions rule of thumb for IVF: sqrt(N_rows), rounded up and
# clamped to a sane range. Too few partitions -> partitions are large
# and each query scans too many vectors; too many -> each partition is
# tiny and the top-K is spread across too many partitions, hurting
# recall unless nprobes is bumped correspondingly.
_MIN_PARTITIONS = 8
_MAX_PARTITIONS = 4096

# num_sub_vectors for PQ: dim / _SUB_VECTOR_DIVISOR. With 768-dim BGE
# embeddings and divisor 16, each vector is quantized into 48 sub-vectors
# of 16 float32 values each, compressed to 48 * 8 bits = 48 bytes on disk
# (vs. 768*4 = 3072 bytes uncompressed). Compression ratio ~64x on the
# code storage; the raw vectors remain in the ``data/`` files unchanged.
_SUB_VECTOR_DIVISOR = 16
_MIN_SUB_VECTORS = 8

# Default nprobes at query time. 10 is the LanceDB documentation's
# recommended starting point for IVF_PQ and empirically gives recall@10
# above 0.95 for BGE embeddings on medium-sized corpora. Bump to 15-20
# if the recall probe (see scripts/bench_kb_search.py) shows regressions
# on a specific dataset.
DEFAULT_NPROBES = 10


class KnowledgeStore:
    """Thin wrapper around a LanceDB table providing upsert, delete, and search.

    Args:
        db_path:   Directory where LanceDB stores its data files.
        collection: Name of the LanceDB table (created if it does not exist).
        embedder:   :class:`~mcp_knowledge.embeddings.base.EmbedderProvider` instance.
    """

    def __init__(
        self,
        db_path: str | None = None,
        collection: str = "default",
        embedder: EmbedderProvider | None = None,
        *,
        connection=None,
        group: str=None,
    ) -> None:
        """Open or create a LanceDB-backed table.

        Either *db_path* (the directory) or *connection* (an already-opened
        ``lancedb`` connection - shared across multiple stores) must be
        provided.  *embedder* is required.

        *group* is an optional grouping key used by the registry to combine
        several stores at search time. When omitted it defaults to the
        collection name.
        """
        if embedder is None:
            raise ValueError("KnowledgeStore requires an embedder")

        self._embedder = embedder
        self._group = group if group else collection
        self._schema = make_schema(embedder.dimension)

        if connection is not None:
            self._db = connection
        else:
            if db_path is None:
                raise ValueError("KnowledgeStore requires db_path or connection")
            import lancedb  # lazy import — only needed at runtime

            Path(db_path).mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(db_path)

        self._collection = collection
        self._table = self._open_or_create_table(collection)

    @property
    def collection(self) -> str:
        return self._collection

    @property
    def group(self) -> str:
        """Grouping key for this store (defaults to the collection name)."""
        return self._group

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open_or_create_table(self, name: str):
        existing = self._db.table_names(limit=1_000)
        if name in existing:
            table = self._db.open_table(name)
            logger.debug("Opened existing LanceDB table '%s'", name)
            # ---------------------------------------------------------------
            # Schema migration: recreate the table when source_hash is absent.
            # All existing rows lack a valid hash so they would be re-ingested
            # regardless — dropping and recreating has the same net effect.
            # ---------------------------------------------------------------
            if "source_hash" not in table.schema.names:
                logger.info(
                    "Table '%s' predates source_hash column — dropping and "
                    "recreating (all files will be re-ingested this startup)",
                    name,
                )
                self._db.drop_table(name)
                table = self._db.create_table(name, schema=self._schema)
                logger.info("Table '%s' recreated with updated schema", name)
        else:
            table = self._db.create_table(name, schema=self._schema)
            logger.debug("Created new LanceDB table '%s'", name)
        return table

    @staticmethod
    def _chunk_id(source: str, chunk_index: int) -> str:
        key = f"{source}:{chunk_index}"
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def _file_hash(data: bytes) -> str:
        """Return the hex SHA-256 digest of *data*."""
        return hashlib.sha256(data).hexdigest()

    def _build_records(self, source: str, chunks: list[str], source_hash: str) -> list[dict]:
        if not chunks:
            return []
        vectors = self._embedder.embed(chunks)
        records = []
        for idx, (text, vector) in enumerate(zip(chunks, vectors)):
            records.append(
                {
                    "id": self._chunk_id(source, idx),
                    "source": source,
                    "chunk_index": idx,
                    "text": text,
                    "vector": vector,
                    "source_hash": source_hash,
                }
            )
        return records

    # ------------------------------------------------------------------
    # Public API - data
    # ------------------------------------------------------------------

    def is_current(self, source: str, file_hash: str) -> bool:
        """Return ``True`` if *source* is already indexed with the given *file_hash*.

        Used to skip re-ingestion of unchanged files at startup.

        Args:
            source:    File path identifier.
            file_hash: SHA-256 hex digest of the file's raw bytes.
        """
        try:
            tbl = (
                self._table.search()
                .where(f"source = '{source}'")
                .limit(1)
                .select(["source_hash"])
                .to_arrow()
            )
            if tbl.num_rows == 0:
                return False
            stored = tbl.column("source_hash")[0].as_py()
            return stored == file_hash
        except Exception:
            return False

    def upsert(self, source: str, chunks: list[str], source_hash: str = "") -> int:
        """Embed *chunks* and upsert them for *source*, replacing any existing chunks.

        Args:
            source:      File path used as the document identifier.
            chunks:      List of text chunks extracted from the document.
            source_hash: SHA-256 hex digest of the source file's raw bytes.
                         Stored alongside each chunk so that :meth:`is_current`
                         can detect unchanged files on subsequent startups.

        Returns:
            Number of chunks written.
        """
        if not chunks:
            logger.debug("upsert: no chunks for '%s', skipping", source)
            return 0

        # Delete any pre-existing rows for this source first
        self.delete(source)

        records = self._build_records(source, chunks, source_hash)
        batch = pa.RecordBatch.from_pylist(records, schema=self._schema)
        self._table.add(pa.Table.from_batches([batch]))
        logger.debug("Upserted %d chunks for '%s'", len(records), source)
        return len(records)

    def delete(self, source: str) -> None:
        """Remove all chunks whose ``source`` matches *source*.

        Args:
            source: File path identifier to remove.
        """
        try:
            self._table.delete(f"source = '{source}'")
            logger.debug("Deleted chunks for source '%s'", source)
        except Exception as exc:  # table may be empty on first call
            logger.debug("delete: %s (ignored)", exc)

    # ------------------------------------------------------------------
    # Public API - search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Semantic search over the knowledge table.

        Convenience wrapper that embeds *query* once and delegates to
        :meth:`search_by_vector`. Prefer :meth:`search_by_vector` directly
        when the caller needs to reuse the same query embedding across
        multiple stores (e.g. multi-corpus fan-out), to avoid recomputing
        the embedding once per store.

        Args:
            query:  Natural-language query string.
            top_k:  Maximum number of results to return.

        Returns:
            List of :class:`SearchResult` ordered by descending relevance score.
        """
        query_vector = self._embedder.embed([query])[0]
        return self.search_by_vector(query_vector, top_k=top_k)

    def search_by_vector(
        self,
        query_vector,
        top_k: int = 5,
        nprobes: int | None = None,
        bypass_ann_index: bool = False,
    ) -> list[SearchResult]:
        """Semantic search using a pre-computed query embedding.

        Exposed so that multi-corpus callers (see ``kb_search``) can embed
        the query exactly once and reuse the same vector across every
        :class:`KnowledgeStore` in the registry, instead of paying one
        embedder forward pass per corpus.

        The call is stable across four configurations, and each ``nprobes``
        / ``bypass_ann_index`` value is honored the same way whether the
        table has an ANN index or not:

        * **No index, nprobes=None, bypass=False**  -> full linear scan
          (identical to the pre-ANN behavior).
        * **No index, nprobes=X, bypass=False**     -> full linear scan;
          ``nprobes`` is silently ignored by LanceDB.
        * **Index present, nprobes=X, bypass=False** -> IVF_PQ search
          with the given nprobes.
        * **Index present, nprobes=X, bypass=True**  -> full linear scan,
          runtime override that ignores the on-disk index. Useful to
          reproduce pre-index behavior without dropping the index, and
          to establish a recall ground truth against the ANN result.

        Args:
            query_vector:      Query embedding produced by this registry's
                               shared embedder. Must have the same
                               dimensionality as the vectors stored in the
                               table (``self._embedder.dimension``).
            top_k:             Maximum number of results to return.
            nprobes:           Number of IVF partitions to probe. ``None``
                               leaves LanceDB's default in effect. Higher =
                               better recall, slower query. Only meaningful
                               when an ANN index exists on the table.
            bypass_ann_index:  When True, forces a brute-force scan even if
                               an ANN index is present. Never raises when
                               the underlying LanceDB build does not support
                               the flag - falls back to the standard path.

        Returns:
            List of :class:`SearchResult` ordered by descending relevance score.
        """
        q = self._table.search(query_vector).metric("cosine").limit(top_k)

        # Optional bypass first, so nprobes/refine still make sense to log
        # in future diagnostics but do not attempt to interact with an
        # index we are explicitly ignoring.
        if bypass_ann_index:
            bypass_fn = getattr(q, "bypass_vector_index", None)
            if bypass_fn is not None:
                q = bypass_fn()
            # If the installed LanceDB predates this API, the call would be
            # silently a no-op - we accept that rather than raising, because
            # the caller's intent (a linear scan) is satisfied by the fact
            # that a table without an index also does a linear scan.

        if nprobes is not None and nprobes >= 1 and not bypass_ann_index:
            # ``nprobes`` is a builder method that is safe to call on any
            # LanceDB query builder in the versions we support; when no
            # index exists on the table it is effectively a no-op.
            nprobes_fn = getattr(q, "nprobes", None)
            if nprobes_fn is not None:
                q = nprobes_fn(nprobes)

        rows = q.select(["source", "chunk_index", "text"]).to_list()

        results = []
        for row in rows:
            # Cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity: 1 - (distance/2) → range [0, 1]
            distance = float(row.get("_distance", 1.0))
            similarity = 1.0 - (distance / 2.0)
            results.append(
                SearchResult(
                    source=row["source"],
                    chunk_index=int(row["chunk_index"]),
                    text=row["text"],
                    score=similarity,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Public API - ANN index lifecycle
    # ------------------------------------------------------------------

    def _list_vector_indices(self) -> list:
        """Return every index currently attached to the ``vector`` column.

        Wraps :meth:`lancedb.table.Table.list_indices` and filters to the
        vector column. Kept as a helper because ``list_indices`` returns
        an iterable of :class:`lancedb.index.IndexConfig` whose exact
        attribute names have shifted slightly across LanceDB versions.
        """
        out: list = []
        list_fn = getattr(self._table, "list_indices", None)
        if list_fn is None:
            return out
        try:
            for idx in list_fn():
                # ``IndexConfig`` exposes ``columns`` (list) or the older
                # ``column`` (str). Guard both.
                cols = getattr(idx, "columns", None) or [getattr(idx, "column", None)]
                if cols and "vector" in cols:
                    out.append(idx)
        except Exception as exc:
            logger.debug("list_indices failed on '%s': %s", self._collection, exc)
        return out

    def has_ann_index(self) -> bool:
        """Return True iff the ``vector`` column currently carries an index."""
        return bool(self._list_vector_indices())

    def ann_index_info(self) -> dict:
        """Read-only snapshot of the ANN index state for diagnostics.

        Returns a dict with keys:

        * ``present`` (bool):     whether any index is attached to ``vector``.
        * ``name`` (str|None):    index name if present.
        * ``index_type`` (str|None): e.g. ``"IVF_PQ"`` when present.
        * ``rows`` (int):         current row count of the table.

        Safe to call on any table, indexed or not; never raises.
        """
        rows = 0
        try:
            rows = int(self._table.count_rows())
        except Exception:
            pass
        indices = self._list_vector_indices()
        if not indices:
            return {"present": False, "name": None, "index_type": None, "rows": rows}
        idx = indices[0]
        return {
            "present": True,
            "name": getattr(idx, "name", None),
            "index_type": getattr(idx, "index_type", None),
            "rows": rows,
        }

    @classmethod
    def _derive_index_params(
        cls,
        row_count: int,
        vector_dim: int,
        num_partitions: int | None,
        num_sub_vectors: int | None,
    ) -> tuple[int, int]:
        """Compute (num_partitions, num_sub_vectors) with safe defaults.

        The overrides are honored when supplied; otherwise:

        * ``num_partitions``  = ``clamp(ceil(sqrt(row_count)), 8, 4096)``
        * ``num_sub_vectors`` = ``max(8, vector_dim // 16)``, clamped so
          it always divides the vector dimension evenly (LanceDB requires
          ``vector_dim % num_sub_vectors == 0``).
        """
        if num_partitions is None:
            num_partitions = max(
                _MIN_PARTITIONS,
                min(_MAX_PARTITIONS, math.ceil(math.sqrt(max(row_count, 1)))),
            )
        if num_sub_vectors is None:
            num_sub_vectors = max(_MIN_SUB_VECTORS, vector_dim // _SUB_VECTOR_DIVISOR)
        # LanceDB requires the vector dimension to be divisible by
        # num_sub_vectors. Snap downwards to the largest divisor that
        # respects the floor, so we never hand LanceDB an invalid combo.
        while num_sub_vectors > _MIN_SUB_VECTORS and vector_dim % num_sub_vectors != 0:
            num_sub_vectors -= 1
        if vector_dim % num_sub_vectors != 0:
            # As a last resort try the floor value; if even that does not
            # divide evenly, fall back to 8 (which divides 768, 1024, 1536,
            # and every common embedding dimension in circulation).
            num_sub_vectors = _MIN_SUB_VECTORS
        return num_partitions, num_sub_vectors

    def ensure_ann_index(
        self,
        min_rows: int = DEFAULT_MIN_ROWS_FOR_INDEX,
        num_partitions: int | None = None,
        num_sub_vectors: int | None = None,
        force: bool = False,
    ) -> dict:
        """Build an ``IVF_PQ`` index on the ``vector`` column, if warranted.

        Idempotent and defensively coded: catches every exception, returns
        a structured status dict, and never brings the search path down.
        Row data is never rewritten - the index is additive metadata that
        sits alongside the ``data/`` directory in the LanceDB table.

        Args:
            min_rows:        Skip index creation when the table has fewer
                             than this many rows. Below the threshold a
                             brute-force scan outperforms an index because
                             the partitioning overhead dominates.
            num_partitions:  Explicit IVF partition count. When ``None`` the
                             value is derived per :meth:`_derive_index_params`.
            num_sub_vectors: Explicit PQ sub-vector count. When ``None`` the
                             value is derived per :meth:`_derive_index_params`.
            force:           When True, rebuild even if an index already
                             exists. Otherwise a pre-existing index is a
                             no-op success.

        Returns:
            Dict with keys ``status`` (one of ``built``, ``already_indexed``,
            ``skipped_too_small``, ``failed``), ``collection``, ``rows``,
            and, on success, ``num_partitions`` / ``num_sub_vectors`` /
            ``seconds``. On failure, ``error`` carries the exception message.
        """
        result: dict = {
            "status": "unknown",
            "collection": self._collection,
            "rows": 0,
        }
        try:
            rows = int(self._table.count_rows())
        except Exception as exc:
            logger.warning(
                "ensure_ann_index('%s'): count_rows failed (%s); staying linear",
                self._collection, exc,
            )
            result.update(status="failed", error=f"count_rows: {exc}")
            return result

        result["rows"] = rows

        if rows < min_rows:
            logger.info(
                "ensure_ann_index('%s'): %d rows < min_rows=%d, staying linear",
                self._collection, rows, min_rows,
            )
            result["status"] = "skipped_too_small"
            return result

        if not force and self.has_ann_index():
            logger.debug(
                "ensure_ann_index('%s'): index already present, skipping",
                self._collection,
            )
            info = self.ann_index_info()
            result.update(
                status="already_indexed",
                name=info.get("name"),
                index_type=info.get("index_type"),
            )
            return result

        num_partitions, num_sub_vectors = self._derive_index_params(
            row_count=rows,
            vector_dim=self._embedder.dimension,
            num_partitions=num_partitions,
            num_sub_vectors=num_sub_vectors,
        )

        t0 = time.perf_counter()
        try:
            self._table.create_index(
                metric="cosine",
                num_partitions=num_partitions,
                num_sub_vectors=num_sub_vectors,
                vector_column_name="vector",
                index_type="IVF_PQ",
                replace=True,
            )
        except Exception as exc:
            # We deliberately swallow every failure here. A failed index
            # build must never prevent the server from starting or a search
            # from returning results - the linear-scan path is still fully
            # functional. The operator sees the failure in logs and in the
            # info://stats resource.
            elapsed = time.perf_counter() - t0
            logger.warning(
                "ensure_ann_index('%s'): create_index failed after %.2fs "
                "(rows=%d, num_partitions=%d, num_sub_vectors=%d): %s "
                "-- table stays on linear scan",
                self._collection, elapsed, rows, num_partitions, num_sub_vectors, exc,
            )
            result.update(
                status="failed",
                num_partitions=num_partitions,
                num_sub_vectors=num_sub_vectors,
                seconds=elapsed,
                error=str(exc),
            )
            return result

        elapsed = time.perf_counter() - t0
        logger.info(
            "ensure_ann_index('%s'): built IVF_PQ in %.2fs "
            "(rows=%d, num_partitions=%d, num_sub_vectors=%d)",
            self._collection, elapsed, rows, num_partitions, num_sub_vectors,
        )
        result.update(
            status="built",
            num_partitions=num_partitions,
            num_sub_vectors=num_sub_vectors,
            seconds=elapsed,
        )
        return result

    def drop_ann_index(self) -> dict:
        """Remove every index currently attached to the ``vector`` column.

        Row data is untouched. After this call the table is byte-identical
        to its pre-index state modulo LanceDB's internal version manifest.
        Idempotent: calling on an already-unindexed table is a no-op.

        Returns:
            Dict ``{"status": "dropped"|"noop", "collection": ..., "dropped": [names...]}``.
        """
        indices = self._list_vector_indices()
        if not indices:
            return {"status": "noop", "collection": self._collection, "dropped": []}
        dropped: list[str] = []
        for idx in indices:
            name = getattr(idx, "name", None)
            if not name:
                # An index without a name cannot be dropped through the
                # public API; log and continue rather than crash.
                logger.warning(
                    "drop_ann_index('%s'): found an unnamed index, skipping",
                    self._collection,
                )
                continue
            try:
                self._table.drop_index(name)
                dropped.append(name)
                logger.info("drop_ann_index('%s'): dropped '%s'", self._collection, name)
            except Exception as exc:
                logger.warning(
                    "drop_ann_index('%s'): failed to drop '%s': %s",
                    self._collection, name, exc,
                )
        return {
            "status": "dropped" if dropped else "noop",
            "collection": self._collection,
            "dropped": dropped,
        }

    # ------------------------------------------------------------------
    # Public API - inspection
    # ------------------------------------------------------------------

    def list_sources(self) -> dict[str, int]:
        """Return a mapping of ``{source: chunk_count}`` for all indexed files."""
        try:
            tbl = self._table.to_arrow().select(["source"])
            sources = tbl.column("source").to_pylist()
            counts: dict[str, int] = {}
            for s in sources:
                counts[s] = counts.get(s, 0) + 1
            return counts
        except Exception as exc:
            logger.warning("list_sources failed: %s", exc, exc_info=True)
            return {}

    def stats(self) -> dict:
        """Return high-level statistics about the knowledge table.

        Includes the ANN index snapshot so operators can see, in one call,
        whether a table is linearly scanned or index-accelerated.
        """
        try:
            total = self._table.count_rows()
        except Exception:
            total = 0
        return {
            "total_chunks": int(total),
            "embedding_dimension": self._embedder.dimension,
            "ann_index": self.ann_index_info(),
        }
