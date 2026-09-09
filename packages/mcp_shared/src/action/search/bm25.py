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

"""BM25-based relevance ranking for action-contract search.

This module adapts a lightweight BM25-style ranking approach to the action
catalog so natural-language or keyword queries can return the most relevant
actions first.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Sequence

from ..models import ActionContract
from .text import extract_searchable_action_text, tokenize_search_text


class _BM25Index:
    def __init__(self, documents: Sequence[list[str]], *, k1: float = 1.5, b: float = 0.75) -> None:
        self._documents = documents
        self._k1 = k1
        self._b = b
        self._doc_lengths = [len(document) for document in documents]
        self._avg_doc_length = (
            sum(self._doc_lengths) / len(self._doc_lengths) if self._doc_lengths else 0.0
        )
        self._term_frequencies = [Counter(document) for document in documents]
        self._document_frequencies: dict[str, int] = defaultdict(int)
        for frequencies in self._term_frequencies:
            for term in frequencies:
                self._document_frequencies[term] += 1

    def score(self, query_terms: Sequence[str]) -> list[float]:
        if not self._documents:
            return []
        doc_count = len(self._documents)
        scores = [0.0] * doc_count
        for term in query_terms:
            doc_frequency = self._document_frequencies.get(term, 0)
            if doc_frequency == 0:
                continue
            idf = math.log(1 + (doc_count - doc_frequency + 0.5) / (doc_frequency + 0.5))
            for idx, term_frequencies in enumerate(self._term_frequencies):
                frequency = term_frequencies.get(term, 0)
                if frequency == 0:
                    continue
                doc_length = self._doc_lengths[idx]
                denominator = frequency + self._k1 * (
                    1 - self._b + self._b * doc_length / (self._avg_doc_length or 1.0)
                )
                scores[idx] += idf * (frequency * (self._k1 + 1)) / denominator
        return scores


def bm25_search_action_contracts(
    actions: Sequence[ActionContract],
    query: str,
    *,
    limit: int,
) -> list[ActionContract]:
    if not actions or limit <= 0:
        return []
    query_terms = tokenize_search_text(query)
    if not query_terms:
        return list(actions[:limit])

    documents = [tokenize_search_text(extract_searchable_action_text(action)) for action in actions]
    index = _BM25Index(documents)
    scores = index.score(query_terms)
    ranked_pairs = sorted(
        zip(actions, scores, strict=False),
        key=lambda item: (item[1], item[0].name),
        reverse=True,
    )
    return [action for action, score in ranked_pairs if score > 0][:limit]
