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

"""Shared ELF/source utilities used by both trace-analysis and coverage subsystems."""

from .elf_index import ElfIndex, SymbolEntry, LineEntry
from .source_index import SourceIndex, ResolvedPath
from .source_snippet import SourceSnippet, DEFAULT_WINDOW, HARD_MAX_WINDOW

__all__ = [
    "ElfIndex",
    "SymbolEntry",
    "LineEntry",
    "SourceIndex",
    "ResolvedPath",
    "SourceSnippet",
    "DEFAULT_WINDOW",
    "HARD_MAX_WINDOW",
]
