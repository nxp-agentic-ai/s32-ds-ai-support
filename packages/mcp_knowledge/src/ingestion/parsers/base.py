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

"""Abstract base class for all file parsers."""
from abc import ABC, abstractmethod
from pathlib import Path


class Parser(ABC):
    """Contract for file parsers.

    Each concrete parser declares the file extensions it handles via the
    ``extensions`` class attribute and implements :meth:`parse` to extract
    plain text from a file of that type.

    The returned text is then chunked and embedded by the ingestion pipeline —
    parsers are only responsible for text extraction.
    """

    extensions: frozenset[str]

    @abstractmethod
    def parse(self, path: Path) -> str:
        """Extract and return the full text content of *path*.

        Args:
            path: Path to the file to parse.

        Returns:
            Extracted plain text.  May be empty if the file contains no
            extractable text content.

        Raises:
            Any IO or parsing exception is allowed to propagate; the pipeline
            catches and logs it, then skips the file.
        """
