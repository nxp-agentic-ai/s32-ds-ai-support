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

"""Abstract base class for embedding providers."""
from abc import ABC, abstractmethod


class EmbedderProvider(ABC):
    """Contract for all embedding providers.

    Implement this interface to add a new embedding backend
    (e.g. OpenAI, Cohere, a local GGUF model, etc.).
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embedding vectors, one per input text.

        Args:
            texts: Non-empty list of strings to embed.

        Returns:
            List of float vectors, same length as *texts*.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the embedding vectors produced by this provider."""
