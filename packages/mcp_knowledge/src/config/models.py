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

import re
from dataclasses import dataclass, field

from nxp.mcp.shared.config.models import BaseMcpServerConfig
from nxp.mcp.knowledge.embeddings.sentence_transformers import (
    PROVIDER as _ST_PROVIDER,
    DEFAULT_MODEL as _ST_DEFAULT_MODEL,
    DEFAULT_DIMENSION as _ST_DEFAULT_DIMENSION,
    DEFAULT_CACHE as _ST_DEFAULT_CACHE,
)


# Corpus names are used as LanceDB table names. Restrict to a safe identifier
# subset so they are also valid as path/table identifiers across backends.
_CORPUS_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")


@dataclass(slots=True)
class EmbedderSettings:
    provider: str = _ST_PROVIDER
    model: str = _ST_DEFAULT_MODEL
    device: str = "cpu"
    # Embedding vector size - must match the chosen model.
    # Override when using a different model so the LanceDB schema can be
    # created without loading the model at startup.
    dimension: int = _ST_DEFAULT_DIMENSION
    # Directory used to cache / load model files (passed to cache_folder).
    cache: str = _ST_DEFAULT_CACHE
    # When True, never contact the HuggingFace Hub: load only from local cache
    # (passes local_files_only=True). Cached models load with zero network;
    # a missing model fails fast instead of attempting a download.
    offline: bool = False


@dataclass(slots=True)
class RerankerSettings:

    """Optional second-stage reranker run after the vector search.

    When ``enabled`` is True, ``kb_search`` overfetches candidates from the
    vector store (``top_k * candidates_multiplier``, capped at
    ``candidates_max`` per corpus), scores each (query, chunk) pair with a
    cross-encoder, and returns the top_k by rerank score.

    Defaults are tuned to pair with ``bge-base-en-v1.5`` for English-only
    corpora. Override ``model`` to ``bge-reranker-v2-m3`` for multilingual
    setups or ``bge-reranker-large`` for higher quality at higher latency.
    """

    enabled: bool = False
    provider: str = "cross_encoder"
    model: str = "bge-reranker-base"
    device: str = "cpu"
    # Directory used to cache / load model files (passed to cache_folder).
    cache: str = "../models"
    # When True, never contact the HuggingFace Hub: load only from local cache
    # (passes local_files_only=True). Cached models load with zero network;
    # a missing model fails fast instead of attempting a download.
    offline: bool = False
    # Cross-encoder token budget per (query, document) pair.

    max_length: int = 512
    # How aggressively to overfetch from the vector store before reranking.
    # With top_k=5 and multiplier=4, each corpus contributes up to 20 candidates.
    candidates_multiplier: int = 4
    # Hard ceiling on candidates fetched per corpus, regardless of multiplier.
    candidates_max: int = 50
    # Global cap on documents sent to the cross-encoder AFTER merging results
    # from every corpus. Keeps rerank latency bounded when many corpora are
    # configured. Set to 0 or a negative value to disable the global cap
    # (legacy behaviour: rerank the full merged pool).
    rerank_budget: int = 40

    def __post_init__(self) -> None:
        if self.candidates_multiplier < 1:
            raise ValueError(
                f"reranker.candidates_multiplier must be >= 1, got {self.candidates_multiplier}"
            )
        if self.candidates_max < 1:
            raise ValueError(
                f"reranker.candidates_max must be >= 1, got {self.candidates_max}"
            )
        if self.max_length < 16:
            raise ValueError(
                f"reranker.max_length must be >= 16, got {self.max_length}"
            )


@dataclass(slots=True)
class SearchSettings:
    """Runtime tuning knobs for the ``kb_search`` tool.

    These control the multi-corpus fan-out described in
    ``tools/search.py``. All fields are optional in YAML - omit any of
    them to use the built-in default (CPU-aware for ``max_workers``).

    Attributes:
        max_workers: Server-wide default for the per-corpus fan-out
                     thread pool used by ``kb_search``. When ``None``,
                     the tool derives a CPU-aware default of
                     ``min(8, max(2, os.cpu_count()))``. When set to 1,
                     the fan-out is fully sequential (useful for
                     deterministic profiling or when debugging thread
                     safety). Agents may still override this on a
                     per-call basis via the ``max_workers`` argument of
                     ``kb_search``; this field only sets the default.
    """

    max_workers: int | None = None

    def __post_init__(self) -> None:
        if self.max_workers is not None and self.max_workers < 1:
            raise ValueError(
                f"search.max_workers must be >= 1 or None, got {self.max_workers}"
            )


@dataclass(slots=True)
class AnnSettings:
    """Runtime configuration for the LanceDB ANN (IVF_PQ) index.

    All fields are optional in YAML - omit the whole ``settings.ann`` block
    to keep the current linear-scan behavior unchanged. The feature is
    **disabled by default** so a code deploy alone never changes runtime
    behavior; enable per environment when you are ready.

    Attributes:
        enabled:              Master switch. When False, no index is ever
                              built and ``kb_search`` bypasses any pre-existing
                              index on disk via LanceDB's
                              ``bypass_vector_index()`` builder. Default False
                              for zero-behavior-change on rollout.
        min_rows_for_index:   Skip index creation on tables with fewer than
                              this many rows (linear scan wins below this).
        num_partitions:       Explicit IVF partition count. When None, the
                              store derives sqrt(N_rows) clamped to a safe
                              range.
        num_sub_vectors:      Explicit PQ sub-vector count. When None, the
                              store derives ``embedding_dim / 16``, adjusted
                              so it divides the dimension evenly.
        nprobes:              Number of partitions probed per query. Higher =
                              better recall, slower query. 10 is a safe
                              starting point for IVF_PQ over BGE embeddings.
                              Ignored on tables without an index.
        rebuild_on_startup:   When True, force a full rebuild of every
                              indexable corpus at server startup. Useful for
                              switching embedders or recovering from a
                              corrupted index; leave False in normal ops.
    """

    enabled: bool = False
    min_rows_for_index: int = 256
    num_partitions: int | None = None
    num_sub_vectors: int | None = None
    nprobes: int = 10
    rebuild_on_startup: bool = False

    def __post_init__(self) -> None:
        if self.min_rows_for_index < 1:
            raise ValueError(
                f"ann.min_rows_for_index must be >= 1, got {self.min_rows_for_index}"
            )
        if self.num_partitions is not None and self.num_partitions < 1:
            raise ValueError(
                f"ann.num_partitions must be >= 1 or None, got {self.num_partitions}"
            )
        if self.num_sub_vectors is not None and self.num_sub_vectors < 1:
            raise ValueError(
                f"ann.num_sub_vectors must be >= 1 or None, got {self.num_sub_vectors}"
            )
        if self.nprobes < 1:
            raise ValueError(f"ann.nprobes must be >= 1, got {self.nprobes}")


@dataclass(slots=True)
class CorpusSettings:
    """A single named corpus = one LanceDB table + the dirs ingested into it.

    Attributes:
        name:  Unique corpus name; also used as the LanceDB table name.
        dirs:  Source directories ingested into this corpus.
        group: Optional grouping key. When None or empty, it defaults to the
               corpus name so that an ungrouped corpus forms a group of
               exactly one. Corpora that share the same ``group`` value are
               combined together at search time.
    """

    name: str
    dirs: list = field(default_factory=list)
    group: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _CORPUS_NAME_RE.match(self.name):
            raise ValueError(
                f"Invalid corpus name {self.name!r}: must match {_CORPUS_NAME_RE.pattern}"
            )
        if not isinstance(self.dirs, list):
            raise ValueError(
                f"Corpus {self.name!r}: 'dirs' must be a list, got {type(self.dirs).__name__}"
            )
        # When no group is provided, fall back to the corpus name so that
        # every corpus always belongs to a well-defined group.
        if not self.group:
            self.group = self.name
        elif not isinstance(self.group, str) or not _CORPUS_NAME_RE.match(self.group):
            raise ValueError(
                f"Invalid corpus group {self.group!r}: must match {_CORPUS_NAME_RE.pattern}"
            )


@dataclass(slots=True)
class KnowledgeSettings:
    db_path: str = "knowledge_db"
    corpora: list = field(default_factory=list)
    chunk_size: int = 512
    chunk_overlap: int = 64
    embedder: EmbedderSettings = field(default_factory=EmbedderSettings)
    reranker: RerankerSettings = field(default_factory=RerankerSettings)
    search: SearchSettings = field(default_factory=SearchSettings)
    ann: AnnSettings = field(default_factory=AnnSettings)
    mutable: bool = False           # when True, ingest/remove tools are registered; False = read-only KB

    def __post_init__(self) -> None:
        # Allow empty corpora at construction time (server may run with no
        # configured corpus, e.g. in tests). When non-empty, enforce uniqueness.
        seen: set[str] = set()
        for c in self.corpora:
            if not isinstance(c, CorpusSettings):
                raise ValueError(
                    "KnowledgeSettings.corpora must contain CorpusSettings instances"
                )
            if c.name in seen:
                raise ValueError(f"Duplicate corpus name: {c.name!r}")
            seen.add(c.name)


@dataclass(slots=True)
class KnowledgeMcpServerConfig(BaseMcpServerConfig):
    """Full configuration for the knowledge MCP server (logging + settings)."""

    settings: KnowledgeSettings = field(default_factory=KnowledgeSettings)
