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

"""HTML parser — strips tags and returns visible text using BeautifulSoup."""
from pathlib import Path

from .base import Parser


class HtmlParser(Parser):
    """Extracts visible text from HTML files using ``beautifulsoup4``.

    Script, style, and head elements are removed before text extraction
    so that only user-visible content is indexed.
    """

    extensions: frozenset[str] = frozenset({".html", ".htm"})

    def parse(self, path: Path) -> str:
        from bs4 import BeautifulSoup  # lazy import

        raw = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")

        # Remove non-content tags
        for tag in soup(["script", "style", "head", "meta", "link"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        # Collapse excessive blank lines
        lines = [line.strip() for line in text.splitlines()]
        cleaned = "\n".join(line for line in lines if line)
        return cleaned
