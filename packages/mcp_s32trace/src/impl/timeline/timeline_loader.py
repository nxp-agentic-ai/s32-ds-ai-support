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

"""Parser for the S32DS Timeline view .timeline binary-text format.

File grammar (observed from S32DS 3.6.9):

    ***Version <N>
    ***Sources: <source_name> [<source_name> ...]
    ***Contexts: <N>
    *
    ***Trace_Source_ID <source_name>
    ***Context_ID <N>

    **Functions
    "<name>",<address_decimal>,<size_bytes>,<is_stub_bool>
    ...

    **Data
    <header_int> <a> <b>
    <source_id> <address> <timestamp_ticks> <sample_count>
    ...
    <footer_int> <checksum>

Multiple Trace_Source_ID / Context_ID sections may be present (one per core).

Data row semantics:
  source_id    -- 0-based index matching the ***Sources declaration order
  address      -- decimal PC value; maps to a function via the Functions table
  timestamp    -- monotonic tick counter (unit depends on board configuration)
  sample_count -- number of instruction cycles (or samples) spent at this PC
                  during this observation window; 0 signals a boundary event

The parser normalises multi-source files: each source gets its own FunctionTable
and DataRow list.  The address->function lookup is done by range (addr in
[func.address, func.address + func.size)).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FunctionEntry:
    name: str
    address: int
    size: int
    is_stub: bool


@dataclass
class DataRow:
    source_id: int
    address: int
    timestamp: int     # raw ticks
    sample_count: int  # cycles / hits at this PC in this window


@dataclass
class TimelineSource:
    """One Trace_Source_ID block (one core)."""
    name: str
    context_id: int
    functions: list[FunctionEntry] = field(default_factory=list)
    rows: list[DataRow] = field(default_factory=list)


@dataclass
class TimelineData:
    version: int
    source_names: list[str]   # from ***Sources header
    sources: list[TimelineSource] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_timeline(path: str | Path) -> TimelineData:
    """Parse a .timeline file and return structured data."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f".timeline not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    return _Parser(text.splitlines()).parse()


# ---------------------------------------------------------------------------
# Internal parser
# ---------------------------------------------------------------------------

_RE_FUNC = re.compile(r'^"((?:[^"\\]|\\.)*)",(\d+),(\d+),(true|false)$')
_RE_DATA = re.compile(r'^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$')
_RE_SOURCES = re.compile(r'^\*\*\*Sources:\s*(.+)$')
_RE_CONTEXTS = re.compile(r'^\*\*\*Contexts:\s*(\d+)$')
_RE_VERSION = re.compile(r'^\*\*\*Version\s+(\d+)$')
_RE_SOURCE_ID = re.compile(r'^\*\*\*Trace_Source_ID\s+(.+)$')
_RE_CONTEXT_ID = re.compile(r'^\*\*\*Context_ID\s+(\d+)$')


class _Parser:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self._pos = 0

    def _peek(self) -> str | None:
        while self._pos < len(self._lines):
            line = self._lines[self._pos]
            if line.strip():
                return line
            self._pos += 1
        return None

    def _next(self) -> str | None:
        line = self._peek()
        if line is not None:
            self._pos += 1
        return line

    def parse(self) -> TimelineData:
        data = TimelineData(version=3, source_names=[])

        # Read file header lines until we hit the first ***Trace_Source_ID
        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()

            m = _RE_VERSION.match(stripped)
            if m:
                data.version = int(m.group(1))
                self._next()
                continue

            m = _RE_SOURCES.match(stripped)
            if m:
                data.source_names = [s.strip() for s in m.group(1).split()]
                self._next()
                continue

            m = _RE_CONTEXTS.match(stripped)
            if m:
                self._next()
                continue

            if stripped == "*":
                self._next()
                continue

            m = _RE_SOURCE_ID.match(stripped)
            if m:
                source_name = m.group(1).strip()
                self._next()
                src = self._parse_source_block(source_name)
                data.sources.append(src)
                continue

            self._next()

        return data

    def _parse_source_block(self, source_name: str) -> TimelineSource:
        """Parse from ***Context_ID through the **Functions and **Data blocks."""
        context_id = 0
        functions: list[FunctionEntry] = []
        rows: list[DataRow] = []

        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()

            # Start of the next source block
            if _RE_SOURCE_ID.match(stripped):
                break

            m = _RE_CONTEXT_ID.match(stripped)
            if m:
                context_id = int(m.group(1))
                self._next()
                continue

            if stripped == "**Functions":
                self._next()
                functions = self._parse_functions()
                continue

            if stripped == "**Data":
                self._next()
                rows = self._parse_data()
                continue

            self._next()

        return TimelineSource(
            name=source_name,
            context_id=context_id,
            functions=functions,
            rows=rows,
        )

    def _parse_functions(self) -> list[FunctionEntry]:
        funcs: list[FunctionEntry] = []
        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()
            if stripped.startswith("**") or _RE_SOURCE_ID.match(stripped):
                break
            m = _RE_FUNC.match(stripped)
            if m:
                funcs.append(FunctionEntry(
                    name=m.group(1),
                    address=int(m.group(2)),
                    size=int(m.group(3)),
                    is_stub=(m.group(4) == "true"),
                ))
            self._next()
        return funcs

    def _parse_data(self) -> list[DataRow]:
        rows: list[DataRow] = []
        # Skip the header line (3 or 2 integers - not a 4-field data row)
        header = self._peek()
        if header is not None:
            parts = header.strip().split()
            if len(parts) in (2, 3) and all(p.isdigit() for p in parts):
                self._next()  # skip data-section header

        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()
            if stripped.startswith("**") or _RE_SOURCE_ID.match(stripped):
                break
            m = _RE_DATA.match(stripped)
            if m:
                rows.append(DataRow(
                    source_id=int(m.group(1)),
                    address=int(m.group(2)),
                    timestamp=int(m.group(3)),
                    sample_count=int(m.group(4)),
                ))
            self._next()
        return rows
