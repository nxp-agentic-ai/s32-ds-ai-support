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

"""Parser for the S32DS Flat Profiler .flatprofiler text format.

File grammar (observed from S32DS 3.6.9):

    **<version>
    <blank>
    **Lines
    <blank>
    "File":     <col-spec ; ...>
    "Function": <col-spec ; ...>
    "Source"(...): <col-spec ; ...>
    "Assembly"(...): <col-spec ; ...>
    <blank>
    # <CoreName>
    <blank>
    ## Context <N>
    <blank>
    **Data
    <blank>
    *0
    "File"(index N): "<path>"(...); <fields...>
    "Function"(parent N): "<name>"(...); <fields...>
    ...
    *<link_id>
    "Source": "<line>"; "<file>"; "<coverage>"; ...; "<asm_count>"; "<time>"
    "Assembly": "<addr>"; "<instr>"; "<coverage>"; ...; "<count>"; "<time>";
    ...

Fields for File / Function rows (semicolon-separated, after the name token):
  address, covered_asm_pct, not_covered_asm_pct, total_asm,
  covered_src_pct, partially_covered_src_pct, not_covered_src_pct,
  total_src_lines, asm_decision_coverage_pct, time, size

Coverage values: "covered", "not covered", "partially covered", or "" (inherit).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)

NO_SOURCE_INFO = "_No source info"


# ---------------------------------------------------------------------------
# Data structures produced by the loader
# ---------------------------------------------------------------------------

@dataclass
class AsmRow:
    address: int
    instruction: str
    coverage: str              # "covered" | "not covered" | "partially covered" | ""
    asm_decision_coverage: str
    count: int
    time: int


@dataclass
class SourceRow:
    line_no: int               # 1-based source line number (0 for blank continuation lines)
    file: str                  # absolute source path (empty for continuation lines)
    coverage: str
    asm_decision_coverage: str
    asm_count: int
    time: int
    asm_rows: list[AsmRow] = field(default_factory=list)


@dataclass
class FunctionRecord:
    name: str
    address: int
    covered_asm_pct: float
    not_covered_asm_pct: float
    total_asm: int
    covered_src_pct: float
    partially_covered_src_pct: float
    not_covered_src_pct: float
    total_src_lines: int
    asm_decision_coverage_pct: float
    time: int
    size: int
    source_rows: list[SourceRow] = field(default_factory=list)
    link_id: int = 0


@dataclass
class FileRecord:
    path: str
    functions: list[FunctionRecord] = field(default_factory=list)
    covered_asm_pct: float = float("nan")
    not_covered_asm_pct: float = float("nan")
    total_asm: int = 0
    covered_src_pct: float = float("nan")
    partially_covered_src_pct: float = float("nan")
    not_covered_src_pct: float = float("nan")
    total_src_lines: int = 0
    asm_decision_coverage_pct: float = float("nan")
    time: int = 0
    size: int = 0

    @property
    def is_no_source_info(self) -> bool:
        return self.path == NO_SOURCE_INFO


@dataclass
class CoreSection:
    name: str
    context_id: int
    files: list[FileRecord] = field(default_factory=list)


@dataclass
class FlatProfilerData:
    version: int
    cores: list[CoreSection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_flatprofiler(path: str | Path) -> FlatProfilerData:
    """Parse a .flatprofiler file and return structured data."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f".flatprofiler not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    return _Parser(text.splitlines()).parse()


# ---------------------------------------------------------------------------
# Internal helpers
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
    """Split on ';' respecting quoted strings."""
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


def _parse_metrics(metric_fields: list[str]) -> dict[str, Any]:
    f = metric_fields
    return {
        "address": _parse_addr(f[0]) if len(f) > 0 else 0,
        "covered_asm_pct": _parse_float(f[1]) if len(f) > 1 else float("nan"),
        "not_covered_asm_pct": _parse_float(f[2]) if len(f) > 2 else float("nan"),
        "total_asm": _parse_int(f[3]) if len(f) > 3 else 0,
        "covered_src_pct": _parse_float(f[4]) if len(f) > 4 else float("nan"),
        "partially_covered_src_pct": _parse_float(f[5]) if len(f) > 5 else float("nan"),
        "not_covered_src_pct": _parse_float(f[6]) if len(f) > 6 else float("nan"),
        "total_src_lines": _parse_int(f[7]) if len(f) > 7 else 0,
        "asm_decision_coverage_pct": _parse_float(f[8]) if len(f) > 8 else float("nan"),
        "time": _parse_int(f[9]) if len(f) > 9 else 0,
        "size": _parse_int(f[10]) if len(f) > 10 else 0,
    }


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

    def parse(self) -> FlatProfilerData:
        data = FlatProfilerData(version=2)
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
        files_by_index: dict[int, FileRecord] = {}
        current_file_index: int | None = None

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
                    continue
                func = self._link_map.get(link_id)
                self._parse_detail(func)
                continue

            if stripped.startswith('"File"(index'):
                self._next()
                label, _, value_str = stripped.partition(': ')
                fields = _split_fields(value_str)
                idx_m = re.search(r'index\s+(\d+)', label)
                idx = int(idx_m.group(1)) if idx_m else len(files_by_index)
                file_name, _ = _extract_name_and_links(fields[0])
                m = _parse_metrics(fields[1:])
                fr = FileRecord(
                    path=file_name,
                    covered_asm_pct=m["covered_asm_pct"],
                    not_covered_asm_pct=m["not_covered_asm_pct"],
                    total_asm=m["total_asm"],
                    covered_src_pct=m["covered_src_pct"],
                    partially_covered_src_pct=m["partially_covered_src_pct"],
                    not_covered_src_pct=m["not_covered_src_pct"],
                    total_src_lines=m["total_src_lines"],
                    asm_decision_coverage_pct=m["asm_decision_coverage_pct"],
                    time=m["time"],
                    size=m["size"],
                )
                files_by_index[idx] = fr
                section.files.append(fr)
                current_file_index = idx
                continue

            if stripped.startswith('"Function"(parent'):
                self._next()
                label, _, value_str = stripped.partition(': ')
                fields = _split_fields(value_str)
                parent_m = re.search(r'parent\s+(\d+)', label)
                parent_idx = int(parent_m.group(1)) if parent_m else current_file_index
                func_name, link_ids = _extract_name_and_links(fields[0])
                m = _parse_metrics(fields[1:])
                func = FunctionRecord(
                    name=func_name,
                    address=m["address"],
                    covered_asm_pct=m["covered_asm_pct"],
                    not_covered_asm_pct=m["not_covered_asm_pct"],
                    total_asm=m["total_asm"],
                    covered_src_pct=m["covered_src_pct"],
                    partially_covered_src_pct=m["partially_covered_src_pct"],
                    not_covered_src_pct=m["not_covered_src_pct"],
                    total_src_lines=m["total_src_lines"],
                    asm_decision_coverage_pct=m["asm_decision_coverage_pct"],
                    time=m["time"],
                    size=m["size"],
                    link_id=link_ids[0] if link_ids else 0,
                )
                if parent_idx is not None and parent_idx in files_by_index:
                    files_by_index[parent_idx].functions.append(func)
                if func.link_id:
                    self._link_map[func.link_id] = func
                continue

            self._next()

    def _parse_detail(self, func: FunctionRecord | None) -> None:
        if func is None:
            _LOG.warning("flatprofiler: detail block references unknown link_id; skipping")
            while self._pos < len(self._lines):
                stripped = self._peek()
                if stripped is None:
                    break
                stripped = stripped.strip()
                if stripped.startswith(("*", '"File"', '"Function"', "#")):
                    break
                self._next()
            return

        current_file = ""
        pending: SourceRow | None = None

        def flush() -> None:
            nonlocal pending
            if pending is not None:
                func.source_rows.append(pending)
            pending = None

        while True:
            line = self._peek()
            if line is None:
                break
            stripped = line.strip()
            if (stripped.startswith("*") and not stripped.startswith("**")) or \
               (stripped.startswith("# ") and not stripped.startswith("## ")):
                break

            if stripped.startswith('"Source"'):
                self._next()
                flush()
                colon = stripped.find(': ')
                if colon == -1:
                    continue
                dfields = _split_fields(stripped[colon + 2:])
                if len(dfields) < 2:
                    continue
                try:
                    line_no = int(_unquote(dfields[0]))
                except ValueError:
                    line_no = 0
                file_str = _unquote(dfields[1]) if len(dfields) > 1 else ""
                if file_str:
                    current_file = file_str
                coverage = _unquote(dfields[2]) if len(dfields) > 2 else ""
                asm_dec = _unquote(dfields[3]) if len(dfields) > 3 else ""
                asm_cnt = _parse_int(dfields[4]) if len(dfields) > 4 else 0
                time_v = _parse_int(dfields[5]) if len(dfields) > 5 else 0
                pending = SourceRow(
                    line_no=line_no,
                    file=current_file if line_no > 0 else "",
                    coverage=coverage,
                    asm_decision_coverage=asm_dec,
                    asm_count=asm_cnt,
                    time=time_v,
                )
                continue

            if stripped.startswith('"Assembly"'):
                self._next()
                colon = stripped.find(': ')
                if colon == -1:
                    continue
                dfields = _split_fields(stripped[colon + 2:])
                if len(dfields) < 2:
                    continue
                asm_row = AsmRow(
                    address=_parse_addr(dfields[0]),
                    instruction=_unquote(dfields[1]) if len(dfields) > 1 else "",
                    coverage=_unquote(dfields[2]) if len(dfields) > 2 else "",
                    asm_decision_coverage=_unquote(dfields[3]) if len(dfields) > 3 else "",
                    count=_parse_int(dfields[4]) if len(dfields) > 4 else 0,
                    time=_parse_int(dfields[5]) if len(dfields) > 5 else 0,
                )
                if pending is not None:
                    pending.asm_rows.append(asm_row)
                continue

            self._next()

        flush()
