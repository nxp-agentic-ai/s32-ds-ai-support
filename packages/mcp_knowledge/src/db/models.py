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

"""Shared data models for the knowledge MCP server."""
from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single result returned by a vector similarity search.

    Attributes:
        source:      Path of the source file that was indexed.
        chunk_index: Zero-based position of this chunk within the source file.
        text:        The matching chunk text.
        score:       L2 distance score from the vector search (lower = more similar).
    """

    source: str
    chunk_index: int
    text: str
    score: float
