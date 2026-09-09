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

"""Regex-based action-contract search for precise pattern matching.

This module applies case-insensitive regular-expression matching over the
searchable action text and is useful for exact or pattern-oriented action
lookups.
"""

import re
from collections.abc import Sequence

from ..models import ActionContract
from .text import extract_searchable_action_text


def regex_search_action_contracts(
    actions: Sequence[ActionContract],
    query: str,
    *,
    limit: int,
) -> list[ActionContract]:
    if not actions or limit <= 0:
        return []
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        return []

    matches: list[ActionContract] = []
    for action in actions:
        if pattern.search(extract_searchable_action_text(action)):
            matches.append(action)
            if len(matches) >= limit:
                break
    return matches
