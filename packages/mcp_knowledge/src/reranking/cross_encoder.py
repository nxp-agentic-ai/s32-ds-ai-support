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

"""Sentence-Transformers CrossEncoder-based reranker (offline, local).

Pairs naturally with the ``sentence_transformers`` embedder. Designed
to be the second stage of a retrieve-then-rerank pipeline: the
bi-encoder (``bge-base-en-v1.5``) does cheap recall over thousands of
chunks, then this reranker rescores the top-N candidates jointly with
the query.

Recommended model pairings:

* ``bge-base-en-v1.5``       -> ``bge-reranker-base``  (English, default)
* ``bge-large-en-v1.5``      -> ``bge-reranker-large`` (English, higher quality)
* ``bge-m3``                 -> ``bge-reranker-v2-m3`` (multilingual, long context)
"""
import logging
from pathlib import Path

from sentence_transformers import CrossEncoder

from nxp.mcp.knowledge.metadata import MCP_SERVER_NAME

from .base import RerankerProvider

PROVIDER = "cross_encoder"
# Default reranker - English, ~278M params, pairs with bge-base-en-v1.5.
DEFAULT_MODEL = "models/bge-reranker-base"
# Cross-encoders truncate the (query, document) pair to this many tokens.
# 512 matches the underlying BERT context window for the BGE rerankers.
DEFAULT_MAX_LENGTH = 512
# Default directory where downloaded models are cached / loaded from
DEFAULT_CACHE = "models"
# Default network policy - when True, never contact the HuggingFace Hub
DEFAULT_OFFLINE = False

logger = logging.getLogger(MCP_SERVER_NAME)



def _is_local_path(model: str) -> bool:
    """Return True if *model* refers to an existing filesystem path."""
    return Path(model).exists()


class CrossEncoderReranker(RerankerProvider):
    """Reranker backed by the ``sentence-transformers`` ``CrossEncoder`` class.

    The underlying model is loaded **lazily** on the first call to
    :meth:`rerank`, so server startup stays fast when the reranker is
    configured but never exercised (e.g. when ``enabled=True`` but no
    search request has arrived yet).

    Two loading modes are selected automatically based on the ``model`` value,
    mirroring :class:`~mcp_knowledge.embeddings.sentence_transformers.SentenceTransformersEmbedder`:

    * **Model name** (e.g. ``"bge-reranker-base"``) - the library downloads the
      model to the HuggingFace cache on first use.
    * **Local path** (e.g. ``"models/bge-reranker-base"``) - the model is
      loaded directly from disk; no network access is performed. Use
      ``scripts/download_model.py --type reranker`` to prepare the directory.

    Args:
        model:      HuggingFace model name **or** absolute/relative path to a
                    pre-downloaded model directory.
        device:     PyTorch device string - ``"cpu"``, ``"cuda"``, ``"mps"``, etc.
        max_length: Maximum tokens per (query, document) pair before truncation.
        cache:      Directory used to cache / load model files. Passed through to
                    the underlying ``CrossEncoder`` as ``cache_folder``.
                    Defaults to ``"models"``.
        offline:    When True, load only from the local cache and never contact
                    the HuggingFace Hub (passes ``local_files_only=True``). A
                    cached model then loads with zero network access; a model
                    that is not cached fails fast instead of attempting a
                    download. Ignored when ``model`` is a local filesystem path
                    (already fully local). Defaults to ``False``.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        device: str = "cpu",
        max_length: int = DEFAULT_MAX_LENGTH,
        cache: str = DEFAULT_CACHE,
        offline: bool = DEFAULT_OFFLINE,
    ) -> None:
        self._model_name = model
        self._device = device
        self._max_length = max_length
        self._cache = cache
        self._offline = offline
        self._model: CrossEncoder | None = None  # loaded lazily on first rerank()


    # ------------------------------------------------------------------
    # Lazy loader
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        if self._model is not None:
            return

        if _is_local_path(self._model_name):
            logger.info(
                "Loading reranker model from local path '%s' on device '%s'",
                self._model_name,
                self._device,
            )
        elif self._offline:
            logger.info(
                "Loading reranker model '%s' on device '%s' (offline: local cache only)",
                self._model_name,
                self._device,
            )
        else:
            logger.info(
                "Loading reranker model '%s' on device '%s' (will download if not cached)",
                self._model_name,
                self._device,
            )

        try:
            self._model = CrossEncoder(
                self._model_name,
                device=self._device,
                max_length=self._max_length,
                cache_folder=self._cache,
                local_files_only=self._offline,
            )
        except Exception as exc:
            if _is_local_path(self._model_name):
                logger.error(
                    "Failed to load reranker model from local path '%s': %s",
                    self._model_name,
                    exc,
                )
            elif self._offline:
                logger.error(
                    "Failed to load reranker model '%s' in offline mode: %s\n"
                    "The model was not found in the local cache '%s'. Pre-download it or set "
                    "'reranker.offline: false' to allow a download. See docs/OFFLINE_MODEL.md.",
                    self._model_name,
                    exc,
                    self._cache,
                )
            else:
                logger.error(
                    "Failed to load reranker model '%s': %s\n"
                    "If the download is blocked, download the model on a machine with internet "
                    "access using scripts/download_model.py --type reranker and set 'reranker.model' "
                    "in the config to the local directory path. See docs/OFFLINE_MODEL.md.",
                    self._model_name,
                    exc,
                )
            raise


        logger.info("Reranker model ready - max_length=%d", self._max_length)

    # ------------------------------------------------------------------
    # RerankerProvider interface
    # ------------------------------------------------------------------

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        logger.info("Reranker received '%s' with %d documents", query, len(documents))
        if not documents:
            return []
        self._ensure_model()
        pairs = [(query, doc) for doc in documents]
        # ``predict`` returns a numpy array of logits/relevance scores.
        scores = self._model.predict(pairs, convert_to_numpy=True)
        return [float(s) for s in scores]
