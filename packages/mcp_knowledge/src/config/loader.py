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

"""Config loader for the knowledge MCP server.

Handles the nested ``embedder``, ``reranker`` and ``corpora`` sub-sections
inside ``settings`` which the generic shared factory cannot resolve
automatically.

Path resolution is explicit and component-owned. The knowledge server knows
which of its settings are file-system paths:

* ``db_path``                      - always a path.
* ``corpora[].dirs[]``             - always a list of paths.
* ``embedder.model`` / ``reranker.model`` - resolved via ``resolve_model_ref``.
  These accept either a config-relative path to a pre-downloaded model
  directory (e.g. ``../models/bge-base-en-v1.5``) OR a bare HuggingFace model
  id (e.g. ``BAAI/bge-base-en-v1.5``). Path-like values are resolved against
  the config dir; bare ids are passed through untouched so the underlying
  library can download them into the cache dir on first use.
* ``embedder.cache`` - always a path; resolved against the config dir so the
  model cache lives in a stable location regardless of the working directory.
"""
from pathlib import Path

import yaml

from nxp.mcp.shared.config.models import LoggingSettings
from nxp.mcp.shared.config.paths import resolve_model_ref, resolve_path


from .models import (
    AnnSettings,
    CorpusSettings,
    EmbedderSettings,
    KnowledgeMcpServerConfig,
    KnowledgeSettings,
    RerankerSettings,
    SearchSettings,
)


def _build_corpora(raw_corpora) -> list[CorpusSettings]:
    if raw_corpora is None:
        return []
    if not isinstance(raw_corpora, list):
        raise ValueError(
            f"settings.corpora must be a list, got {type(raw_corpora).__name__}"
        )
    result: list[CorpusSettings] = []
    for entry in raw_corpora:
        if not isinstance(entry, dict):
            raise ValueError(
                f"settings.corpora entries must be mappings, got {type(entry).__name__}"
            )
        if "name" not in entry:
            raise ValueError("settings.corpora entry is missing required 'name' field")
        result.append(
            CorpusSettings(
                name=entry["name"],
                dirs=list(entry.get("dirs", [])),
                group=entry.get("group"),
            )
        )
    return result


def _build_settings(raw_settings: dict, base_dir: Path | None = None) -> KnowledgeSettings:
    raw = dict(raw_settings)  # shallow copy; we pop sub-sections
    embedder_raw = raw.pop("embedder", {})
    reranker_raw = raw.pop("reranker", {})
    search_raw = raw.pop("search", {})
    ann_raw = raw.pop("ann", {})
    corpora_raw = raw.pop("corpora", None)
    embedder = EmbedderSettings(**embedder_raw) if embedder_raw else EmbedderSettings()
    reranker = RerankerSettings(**reranker_raw) if reranker_raw else RerankerSettings()
    search = SearchSettings(**search_raw) if search_raw else SearchSettings()
    ann = AnnSettings(**ann_raw) if ann_raw else AnnSettings()
    corpora = _build_corpora(corpora_raw)

    if base_dir is not None:
        # db_path and corpus dirs are always file-system paths.
        if "db_path" in raw:
            raw["db_path"] = resolve_path(raw["db_path"], base_dir)
        for corpus in corpora:
            corpus.dirs = [resolve_path(d, base_dir) for d in corpus.dirs]
        # Model refs may be a path OR a bare HuggingFace id - only resolve
        # path-like values; bare ids pass through so they can be downloaded.
        embedder.model = resolve_model_ref(embedder.model, base_dir)
        reranker.model = resolve_model_ref(reranker.model, base_dir)
        # The cache dir is always a path; resolve it against the config dir so
        # the model cache location is stable regardless of the working dir.
        embedder.cache = resolve_path(embedder.cache, base_dir)
        reranker.cache = resolve_path(reranker.cache, base_dir)


    return KnowledgeSettings(
        **raw,
        embedder=embedder,
        reranker=reranker,
        search=search,
        ann=ann,
        corpora=corpora,
    )


def load_standalone_config(path: str | None = None) -> KnowledgeMcpServerConfig:
    """Load knowledge server config from a YAML file, or use embedded defaults.

    Relative path fields are resolved against the directory containing the
    config file.
    """
    if path is None:
        return KnowledgeMcpServerConfig()
    p = Path(path).resolve()
    base_dir = p.parent
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return _assemble(data, base_dir)


def build_mcp_server_config(
    raw: dict, base_dir: Path | None = None
) -> KnowledgeMcpServerConfig:
    """Build a KnowledgeMcpServerConfig from a raw dict (called by the gateway composer).

    ``base_dir`` is the directory of the gateway config file, used to resolve
    this server's relative path fields. When ``None`` no resolution is done.
    """
    return _assemble(raw, base_dir)


def _assemble(data: dict, base_dir: Path | None) -> KnowledgeMcpServerConfig:
    logging = LoggingSettings(**data.get("logging", {}))
    skills = data.get("skills", "")
    if base_dir is not None:
        logging.file = resolve_path(logging.file, base_dir)
        skills = resolve_path(skills, base_dir)
    raw_settings = dict(data.get("settings", {}))
    return KnowledgeMcpServerConfig(
        logging=logging,
        settings=_build_settings(raw_settings, base_dir),
        skills=skills,
    )
