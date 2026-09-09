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

"""Parser for the S32DS Performance View .perf text format.

File grammar (observed from S32DS 3.6.9):

    **<version>
    <blank>
    **Lines
    <blank>
    "Function": <col-spec ; ...>
    "Call Pair": <col-spec ; ...>
    <blank>
    # <CoreName>
    <blank>
    ## Context <N>
    <blank>
    **Data
    <blank>
    *0
    "Function": "<name>"(link <id>); <fields...>
    ...
    *<link_id>
    "Call Pair": "<caller>"; "<callee>"; <fields...>
    ...

Function fields (after the name token):
  num_calls, inclusive, min_inclusive, max_inclusive, avg_inclusive,
  pct_inclusive, exclusive, min_exclusive, max_exclusive, avg_exclusive,
  pct_exclusive, pct_total_calls, code_size
  (followed by duplicated "Variable0" variant columns which are skipped)

Call Pair fields:
  num_calls_callee, inclusive_callee, min_inclusive_callee, max_inclusive_callee,
  avg_inclusive_callee, pct_callee, pct_caller, ...duplicates, call_site (hex)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

_LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CallPairRecord:
    caller: str
    callee: str
    num_calls: int
    inclusive_callee: float
    min_inclusive_callee: float
    max_inclusive_callee: float
    avg_inclusive_callee: float
    pct_callee: float
    pct_caller: float
    call_site: int


@dataclass
class FunctionRecord:
    name: str
    link_id: int
    num_calls: int
    inclusive: float
    min_inclusive: float
    max_inclusive: float
    avg_inclusive: float
    pct_inclusive: float
    exclusive: float
    min_exclusive: float
    max_exclusive: float
    avg_exclusive: float
    pct_exclusive: float
    pct_total_calls: float
    code_size: int
    call_pairs: list[CallPairRecord] = field(default_factory=list)


@dataclass
class CoreSection:
    name: str
    context_id: int
    functions: list[FunctionRecord] = field(default_factory=list)


@dataclass
class PerfData:
    version: int
    cores: list[CoreSection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_perf(path: str | Path) -> PerfData:
    """Parse a .perf file and return structured data."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f".perf not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    return _Parser(text.splitlines()).parse()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RE_LINK_IDS = re.compile(r'link\s+(\d+)', re.IGNORECASE)


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _parse_float(s: str) -> float:
    s = s.strip().strip('"')
    if s in ("N/A", "", "N"):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _parse_int(s: str) -> int:
    s = s.strip().strip('"')
    if s in ("N/A", ""):
        return 0
    try:
        return int(s)
    except ValueError:
        return 0


def _parse_addr(s: str) -> int:
    s = s.strip().strip('"')
    if not s or s == "N/A":
        return 0
    try:
        return int(s, 16) if s.lower().startswith("0x") else int(s)
    except ValueError:
        return 0


def _split_fields(line: str) -> list[str]:
    tokens: list[str] = []
    buf: list[str] = []
    in_quote = False
    for ch in line:
        if ch == '"':
            in_quote = not in_quote
            buf.append(ch)
        elif ch == ';' and not in_quote:
            tokens.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append("".join(buf).strip())
    return tokens


def _extract_name_and_links(token: str) -> tuple[str, list[int]]:
    m = re.search(r'"((?:[^"\\]|\\.)*)"', token)
    name = m.group(1) if m else token.strip()
    links = [int(x) for x in _RE_LINK_IDS.findall(token)]
    return name, links


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class _Parser:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self._pos = 0
        self._link_map: dict[int, FunctionRecord] = {}

    def _peek(self) -> str | None:
        return self._lines[self._pos] if self._pos < len(self._lines) else None

    def _next(self) -> str | None:
        line = self._peek()
        self._pos += 1
        return line

    def parse(self) -> PerfData:
        data = PerfData(version=2)
        first = self._next()
        if first and first.startswith("**"):
            try:
                data.version = int(first[2:].strip())
            except ValueError:
                pass

        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                core_name = stripped[2:].strip()
                self._next()
                section = self._parse_core(core_name)
                if section is not None:
                    data.cores.append(section)
            else:
                self._next()
        return data

    def _parse_core(self, core_name: str) -> CoreSection | None:
        context_id = 0
        section: CoreSection | None = None

        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                break
            if stripped.startswith("## Context"):
                try:
                    context_id = int(stripped.split()[-1])
                except ValueError:
                    pass
                self._next()
                continue
            if stripped == "**Data":
                self._next()
                section = CoreSection(name=core_name, context_id=context_id)
                self._parse_data(section)
                continue
            self._next()

        return section

    def _parse_data(self, section: CoreSection) -> None:
        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()

            if stripped.startswith("# ") and not stripped.startswith("## "):
                break

            if stripped.startswith("*") and not stripped.startswith("**"):
                raw_id = stripped[1:].strip()
                try:
                    link_id = int(raw_id)
                except ValueError:
                    self._next()
                    continue
                self._next()
                if link_id == 0:
                    # Function rows under *0
                    self._parse_function_rows(section)
                else:
                    func = self._link_map.get(link_id)
                    self._parse_call_pairs(func)
                continue

            self._next()

    def _parse_function_rows(self, section: CoreSection) -> None:
        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()
            if stripped.startswith("*") or (stripped.startswith("# ") and not stripped.startswith("## ")):
                break

            if stripped.startswith('"Function"'):
                self._next()
                colon = stripped.find(': ')
                if colon == -1:
                    continue
                value_str = stripped[colon + 2:]
                fields = _split_fields(value_str)
                if not fields:
                    continue
                func_name, link_ids = _extract_name_and_links(fields[0])
                f = fields
                func = FunctionRecord(
                    name=func_name,
                    link_id=link_ids[0] if link_ids else 0,
                    num_calls=_parse_int(f[1]) if len(f) > 1 else 0,
                    inclusive=_parse_float(f[2]) if len(f) > 2 else float("nan"),
                    min_inclusive=_parse_float(f[3]) if len(f) > 3 else float("nan"),
                    max_inclusive=_parse_float(f[4]) if len(f) > 4 else float("nan"),
                    avg_inclusive=_parse_float(f[5]) if len(f) > 5 else float("nan"),
                    pct_inclusive=_parse_float(f[6]) if len(f) > 6 else float("nan"),
                    exclusive=_parse_float(f[7]) if len(f) > 7 else float("nan"),
                    min_exclusive=_parse_float(f[8]) if len(f) > 8 else float("nan"),
                    max_exclusive=_parse_float(f[9]) if len(f) > 9 else float("nan"),
                    avg_exclusive=_parse_float(f[10]) if len(f) > 10 else float("nan"),
                    pct_exclusive=_parse_float(f[11]) if len(f) > 11 else float("nan"),
                    pct_total_calls=_parse_float(f[12]) if len(f) > 12 else float("nan"),
                    code_size=_parse_int(f[13]) if len(f) > 13 else 0,
                )
                section.functions.append(func)
                if func.link_id:
                    self._link_map[func.link_id] = func
                continue

            self._next()

    def _parse_call_pairs(self, func: FunctionRecord | None) -> None:
        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()
            if stripped.startswith("*") or (stripped.startswith("# ") and not stripped.startswith("## ")):
                break

            if stripped.startswith('"Call Pair"'):
                self._next()
                colon = stripped.find(': ')
                if colon == -1:
                    continue
                value_str = stripped[colon + 2:]
                fields = _split_fields(value_str)
                if len(fields) < 7:
                    continue
                caller = _unquote(fields[0])
                callee = _unquote(fields[1])
                # Find call_site: last field that looks like a hex address
                call_site = 0
                for fv in reversed(fields):
                    v = fv.strip().strip('"')
                    if v.lower().startswith("0x"):
                        call_site = _parse_addr(v)
                        break
                cp = CallPairRecord(
                    caller=caller,
                    callee=callee,
                    num_calls=_parse_int(fields[2]) if len(fields) > 2 else 0,
                    inclusive_callee=_parse_float(fields[3]) if len(fields) > 3 else float("nan"),
                    min_inclusive_callee=_parse_float(fields[4]) if len(fields) > 4 else float("nan"),
                    max_inclusive_callee=_parse_float(fields[5]) if len(fields) > 5 else float("nan"),
                    avg_inclusive_callee=_parse_float(fields[6]) if len(fields) > 6 else float("nan"),
                    pct_callee=_parse_float(fields[7]) if len(fields) > 7 else float("nan"),
                    pct_caller=_parse_float(fields[8]) if len(fields) > 8 else float("nan"),
                    call_site=call_site,
                )
                if func is not None:
                    func.call_pairs.append(cp)
                continue

            self._next()
