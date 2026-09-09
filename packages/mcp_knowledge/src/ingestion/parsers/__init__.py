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

"""Parser registry — maps file extensions to parser instances.

Each parser module self-registers by calling :func:`register` at import time.
The registry is populated by importing all built-in parsers at the bottom of
this module.  External parsers can register themselves by calling
:func:`register` directly after import.
"""
from pathlib import Path

from .base import Parser

_REGISTRY: dict[str, Parser] = {}


def register(parser: Parser) -> None:
    """Register *parser* for all extensions declared in ``parser.extensions``."""
    for ext in parser.extensions:
        _REGISTRY[ext.lower()] = parser


def get_parser(path: Path) -> Parser | None:
    """Return the parser for *path*'s extension, or ``None`` if unsupported."""
    return _REGISTRY.get(path.suffix.lower())


def supported_extensions() -> frozenset[str]:
    """Return the set of file extensions currently supported by registered parsers."""
    return frozenset(_REGISTRY)


# --- register all built-in parsers -------------------------------------------
from .txt import TxtParser       # noqa: E402
from .md import MarkdownParser   # noqa: E402
from .pdf import PdfParser       # noqa: E402
from .html import HtmlParser     # noqa: E402
from .code import CodeParser     # noqa: E402
from .data import DataParser     # noqa: E402

register(TxtParser())
register(MarkdownParser())
register(PdfParser())
register(HtmlParser())
register(CodeParser())
register(DataParser())

__all__ = ["Parser", "register", "get_parser", "supported_extensions"]
