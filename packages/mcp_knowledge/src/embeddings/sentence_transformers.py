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

"""Sentence Transformers embedding provider."""
import logging
from pathlib import Path

from sentence_transformers import SentenceTransformer

from nxp.mcp.knowledge.metadata import MCP_SERVER_NAME

from .base import EmbedderProvider

PROVIDER = "sentence_transformers"
# Default model — lightweight, fast, good all-round quality for semantic search
DEFAULT_MODEL = "bge-base-en-v1.5"
DEFAULT_DIMENSION = 768
# Default directory where downloaded models are cached / loaded from
DEFAULT_CACHE = "models"
# Default network policy - when True, never contact the HuggingFace Hub
DEFAULT_OFFLINE = False


logger = logging.getLogger(MCP_SERVER_NAME)


def _is_local_path(model: str) -> bool:
    """Return True if *model* refers to an existing filesystem path."""
    return Path(model).exists()


class SentenceTransformersEmbedder(EmbedderProvider):
    """Embedding provider backed by the ``sentence-transformers`` library.

    The underlying model is loaded **lazily** on the first call to
    :meth:`embed`, so that server startup is fast when all indexed
    files are unchanged and no embedding is required.

    Two loading modes are selected automatically based on the ``model`` value:

    * **Model name** (e.g. ``"bge-base-en-v1.5"``) — the library downloads the
      model to the HuggingFace cache on first use and loads from disk on
      subsequent runs.
    * **Local path** (e.g. ``"C:/models/bge-base-en-v1.5"``) — the model is
      loaded directly from the given directory; no network access is performed.

    Args:
        model:     HuggingFace model name **or** absolute/relative path to a
                   pre-downloaded model directory.
        device:    PyTorch device string — ``"cpu"``, ``"cuda"``, ``"mps"``, etc.
        dimension: Expected embedding dimension.  Must match the chosen model.
                   Used to configure the LanceDB schema without loading the
                   model at startup.  Defaults to 768 (``bge-base-en-v1.5``).
        cache:     Directory used to cache / load model files. Passed through to
                   the underlying ``SentenceTransformer`` as ``cache_folder``.
                   Defaults to ``"models"``.
        offline:   When True, load only from the local cache and never contact
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
        dimension: int = DEFAULT_DIMENSION,
        cache: str = DEFAULT_CACHE,
        offline: bool = DEFAULT_OFFLINE,
    ) -> None:
        self._model_name = model
        self._device = device
        self._dimension = dimension
        self._cache = cache
        self._offline = offline
        self._model = None  # loaded lazily on first embed() call


    # ------------------------------------------------------------------
    # Lazy loader
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        """Load the SentenceTransformer model if not already loaded."""
        if self._model is not None:
            return

        if _is_local_path(self._model_name):
            logger.info(
                "Loading embedding model from local path '%s' on device '%s'",
                self._model_name,
                self._device,
            )
        elif self._offline:
            logger.info(
                "Loading embedding model '%s' on device '%s' (offline: local cache only)",
                self._model_name,
                self._device,
            )
        else:
            logger.info(
                "Loading embedding model '%s' on device '%s' (will download if not cached)",
                self._model_name,
                self._device,
            )

        try:
            self._model = SentenceTransformer(
                self._model_name,
                device=self._device,
                cache_folder=self._cache,
                local_files_only=self._offline,
            )
        except Exception as exc:
            if _is_local_path(self._model_name):
                logger.error(
                    "Failed to load embedding model from local path '%s': %s",
                    self._model_name,
                    exc,
                )
            elif self._offline:
                logger.error(
                    "Failed to load embedding model '%s' in offline mode: %s\n"
                    "The model was not found in the local cache '%s'. Pre-download it "
                    "(e.g. with the model id, so a '%s' cache snapshot is created) or set "
                    "'embedder.offline: false' to allow a download.",
                    self._model_name,
                    exc,
                    self._cache,
                    self._model_name,
                )
            else:
                logger.error(
                    "Failed to load embedding model '%s': %s\n"
                    "Either the name is invalid or the download is blocked",
                    self._model_name,
                    exc,
                )
            raise


        actual_dim = self._model.get_embedding_dimension()
        if actual_dim != self._dimension:
            logger.warning(
                "Configured dimension=%d does not match model dimension=%d — "
                "update 'embedder.dimension' in your config to avoid schema mismatch",
                self._dimension,
                actual_dim,
            )
            self._dimension = actual_dim

        logger.info("Embedding model ready — dimension=%d", self._dimension)

    # ------------------------------------------------------------------
    # EmbedderProvider interface
    # ------------------------------------------------------------------

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._ensure_model()
        vectors = self._model.encode(texts, convert_to_numpy=True)
        return [v.tolist() for v in vectors]

    @property
    def dimension(self) -> int:
        return self._dimension
