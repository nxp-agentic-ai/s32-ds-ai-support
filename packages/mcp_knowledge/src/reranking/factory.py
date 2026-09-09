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

"""Factory for instantiating reranker providers from config."""
from nxp.mcp.knowledge.config.models import RerankerSettings

from .base import RerankerProvider


def create_reranker(settings: RerankerSettings | None) -> RerankerProvider | None:
    """Instantiate a :class:`RerankerProvider` from config settings.

    Returns ``None`` when no reranker is configured or ``enabled`` is False,
    so callers can do ``if reranker is not None: ...`` without separately
    inspecting the config.

    Supported providers
    -------------------
    ``cross_encoder``
        Local offline reranker via ``sentence-transformers.CrossEncoder``.
        Default model: ``bge-reranker-base``.

    To add a new provider, implement
    :class:`~mcp_knowledge.reranking.base.RerankerProvider` and add a branch
    here keyed on the ``provider`` string.

    Args:
        settings: :class:`~mcp_knowledge.config.models.RerankerSettings` from
                  the server config, or ``None`` when the section is absent.

    Returns:
        A ready-to-use :class:`RerankerProvider` instance, or ``None`` when
        reranking is disabled.

    Raises:
        ValueError: If ``settings.provider`` is not recognised.
    """
    if settings is None or not settings.enabled:
        return None

    from .cross_encoder import PROVIDER as _CE_PROVIDER, CrossEncoderReranker

    if settings.provider == _CE_PROVIDER:
        return CrossEncoderReranker(
            model=settings.model,
            device=settings.device,
            max_length=settings.max_length,
            cache=settings.cache,
            offline=settings.offline,
        )


    raise ValueError(
        f"Unknown reranker provider '{settings.provider}'. "
        f"Supported: '{_CE_PROVIDER}'."
    )
