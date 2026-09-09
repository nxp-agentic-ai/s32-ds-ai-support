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

"""Text chunking — splits extracted text into overlapping fixed-size chunks."""

def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> list[str]:
    """Split *text* into overlapping word-based chunks.

    Chunking is performed on whitespace-tokenised words rather than characters
    so that chunk boundaries do not split in the middle of a word.

    Args:
        text:         Input text to chunk.
        chunk_size:   Maximum number of words per chunk.
        chunk_overlap: Number of words to repeat at the start of each
                      subsequent chunk to preserve context across boundaries.

    Returns:
        List of text chunks.  Returns an empty list if *text* is blank.
    """
    text = text.strip()
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    # Guard against nonsensical config values
    chunk_size = max(chunk_size, 1)
    chunk_overlap = max(0, min(chunk_overlap, chunk_size - 1))

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - chunk_overlap

    return chunks
