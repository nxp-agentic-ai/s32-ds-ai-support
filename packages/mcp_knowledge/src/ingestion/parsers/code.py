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

"""Source code parser — treats source files as plain text for semantic indexing.

Covers Python, JavaScript, TypeScript, JSX, TSX, Java, C, C++ and headers.
No AST parsing is performed: the full file content (comments, identifiers,
string literals, docstrings) is returned as-is, which is sufficient for
semantic search without adding per-language AST dependencies.
"""
from pathlib import Path

from .base import Parser


class CodeParser(Parser):
    """Returns the raw text of source code files.

    All identifiers, comments, docstrings, and string literals are preserved
    and included in the text passed to the chunker and embedder.
    """

    extensions: frozenset[str] = frozenset(
        {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
        }
    )

    def parse(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace")
