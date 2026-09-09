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

"""Factory for instantiating embedding providers from config."""
from nxp.mcp.knowledge.config.models import EmbedderSettings

from .base import EmbedderProvider


def create_embedder(settings: EmbedderSettings) -> EmbedderProvider:
    """Instantiate an :class:`EmbedderProvider` from config settings.

    Supported providers
    -------------------
    ``sentence_transformers``
        Local offline embeddings via the ``sentence-transformers`` library.
        Default model: ``bge-base-en-v1.5``.

    To add a new provider, implement :class:`~mcp_knowledge.embeddings.base.EmbedderProvider`
    and add a branch here keyed on the ``provider`` string.

    Args:
        settings: :class:`~mcp_knowledge.config.models.EmbedderSettings` from the server config.

    Returns:
        A ready-to-use :class:`EmbedderProvider` instance.

    Raises:
        ValueError: If ``settings.provider`` is not recognised.
    """
    from .sentence_transformers import PROVIDER as _ST_PROVIDER, SentenceTransformersEmbedder

    if settings.provider == _ST_PROVIDER:
        return SentenceTransformersEmbedder(
            model=settings.model,
            device=settings.device,
            dimension=settings.dimension,
            cache=settings.cache,
            offline=settings.offline,
        )


    raise ValueError(
        f"Unknown embedder provider '{settings.provider}'. "
        f"Supported: '{_ST_PROVIDER}'."
    )
