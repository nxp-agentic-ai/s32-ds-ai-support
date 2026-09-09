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

"""Markdown file parser — strips YAML frontmatter, returns body text."""
import re
from pathlib import Path

from .base import Parser

_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n.*?\n---\s*\n", re.DOTALL)


class MarkdownParser(Parser):
    """Parses ``.md`` and ``.markdown`` files.

    YAML frontmatter (delimited by ``---`` blocks) is stripped before the
    body text is returned so that metadata fields do not pollute the chunks.
    """

    extensions: frozenset[str] = frozenset({".md", ".markdown"})

    def parse(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8", errors="replace")
        text = _FRONTMATTER_RE.sub("", text, count=1)
        return text.strip()
