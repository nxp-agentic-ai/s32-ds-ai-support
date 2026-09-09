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

"""Abstract base class for reranker providers.

A reranker takes a query and a list of candidate documents (already
retrieved by a fast bi-encoder vector search) and returns a relevance
score per document. Cross-encoder models like ``bge-reranker-base``
score (query, document) pairs jointly and are typically much more
accurate than the embedding similarity used during recall, at the cost
of higher per-pair latency.

Implementations are expected to be **deterministic** for a given
(query, documents) input within one process lifetime and to preserve
input order in their output list.
"""
from abc import ABC, abstractmethod


class RerankerProvider(ABC):
    """Contract for all reranker providers.

    Implement this interface to add a new reranker backend
    (e.g. Cohere Rerank API, a local ONNX cross-encoder, etc.).
    """

    @abstractmethod
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        """Return one relevance score per *document*.

        Args:
            query:     Natural-language query string.
            documents: Candidate documents to score. May be empty.

        Returns:
            List of float scores, same length and order as *documents*.
            Higher = more relevant. Score ranges are implementation-defined;
            callers should only use them for ordering, not for thresholding
            across rerankers.
        """
