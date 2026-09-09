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

"""Search text normalization and extraction helpers for action contracts.

This module turns action metadata into searchable text and provides simple text
normalization/tokenization utilities shared by BM25 and regex-based search.
"""

import re

from ..models import ActionContract

_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")


def normalize_search_text(text: str) -> str:
    return text.casefold().strip()


def tokenize_search_text(text: str) -> list[str]:
    normalized = normalize_search_text(text)
    return [token for token in _TOKEN_SPLIT_RE.split(normalized) if token]


def extract_searchable_action_text(action: ActionContract) -> str:
    parts: list[str] = [
        action.name,
        action.description,
        action.category,
    ]
    if action.related_actions:
        parts.extend(action.related_actions)
    return "\n".join(part for part in parts if part)
