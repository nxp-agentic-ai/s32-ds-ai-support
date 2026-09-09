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

"""Query functions that operate on a loaded TraceDataset.

All functions are pure (no side effects) and return JSON-serializable dicts.

Response size guardrails
------------------------
- MAX_ROWS:      maximum event rows returned per query call (hard cap 5000).
- MAX_SRC_BYTES: maximum total source snippet bytes per call (64 KB).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .trace_dataset import TraceDataset

MAX_ROWS = 5000
MAX_SRC_BYTES = 65536
_DEFAULT_LIMIT = 100
_TOP_N = 10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _enrich_row(
    row: dict[str, Any],
    ds: TraceDataset,
    include_source: bool,
    snippet_window: int | None,
    src_bytes_budget: list[int],
) -> dict[str, Any]:
    """Add ELF-resolved symbol/file:line and optional source snippet to a row."""
    addr_int: int | None = row.get("address_int")
    result = dict(row)

    elf_info: dict[str, Any] = {}
    if addr_int is not None:
        elf_info = ds.elf.lookup_address(addr_int)
        sym = elf_info.get("symbol")
        offset = elf_info.get("offset")
        result["elf_symbol"] = f"{sym}+0x{int(offset):x}" if sym is not None and offset is not None else sym
        result["elf_file"] = elf_info.get("file")
        result["elf_line"] = elf_info.get("line")

    if include_source and ds.src is not None:
        dwarf_file = elf_info.get("file") or ""
        elf_line = elf_info.get("line")
        if dwarf_file and elf_line:
            resolved = ds.src.resolve(dwarf_file)
            if resolved.resolved and resolved.local_path:
                if src_bytes_budget[0] > 0:
                    snip = ds.snippets.read(resolved.local_path, elf_line, window=snippet_window)
                    if snip is not None:
                        snip_bytes = sum(len(l["text"]) for l in snip.get("lines", []))
                        if snip_bytes <= src_bytes_budget[0]:
                            result["source_snippet"] = snip
                            src_bytes_budget[0] -= snip_bytes
            elif not resolved.resolved and resolved.candidates:
                result["source_candidates"] = resolved.candidates

    return result


import pandas as _pd

_INT_KEYS = frozenset({"address_int", "destination_int", "timestamp_int", "detail_count"})


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a pandas Series to a JSON-safe dict of native Python types."""
    d: dict[str, Any] = row.to_dict()
    for k, v in d.items():
        if v is _pd.NA or v is None:
            d[k] = None
            continue
        if isinstance(v, float) and v != v:  # NaN
            d[k] = None
            continue
        item_fn = getattr(v, "item", None)
        if item_fn is not None:
            try:
                d[k] = item_fn()
            except (ValueError, TypeError):
                pass
    for k in _INT_KEYS.intersection(d):
        v = d[k]
        if v is not None and not isinstance(v, int):
            try:
                d[k] = int(v)
            except (TypeError, ValueError):
                pass
    return d


def _match_selector(df: Any, sel: dict[str, Any]) -> Any:
    """Apply a filter selector to a DataFrame and return a boolean mask."""
    import pandas as pd
    mask = pd.Series([True] * len(df), index=df.index)

    symbol_pat = sel.get("symbol")
    if symbol_pat and "elf_symbol" in df.columns:
        mask &= df["elf_symbol"].fillna("").str.contains(symbol_pat, regex=True, na=False)
    elif symbol_pat and "description" in df.columns:
        mask &= df["description"].fillna("").str.contains(symbol_pat, regex=True, na=False)

    pc_range = sel.get("pc_range")
    if pc_range and "address_int" in df.columns:
        lo, hi = int(pc_range[0], 16) if isinstance(pc_range[0], str) else int(pc_range[0]), \
                 int(pc_range[1], 16) if isinstance(pc_range[1], str) else int(pc_range[1])
        mask &= df["address_int"].between(lo, hi)

    event_type = sel.get("event_type")
    if event_type and "event_type" in df.columns:
        mask &= df["event_type"].fillna("").str.lower() == event_type.lower()

    core = sel.get("core")
    if core and "core" in df.columns:
        mask &= df["core"].fillna("").str.lower() == core.lower()

    time_range = sel.get("time_range")
    if time_range and "timestamp_int" in df.columns:
        t_lo = int(time_range[0])
        t_hi = int(time_range[1])
        mask &= df["timestamp_int"].between(t_lo, t_hi)

    instr_re = sel.get("instruction_regex")
    if instr_re and "description" in df.columns:
        mask &= df["description"].fillna("").str.contains(instr_re, regex=True, na=False)

    return mask


# ---------------------------------------------------------------------------
# Query: summary
# ---------------------------------------------------------------------------

def query_summary(ds: TraceDataset, top_n: int = _TOP_N) -> dict[str, Any]:
    """Return coarse statistics for the loaded trace."""
    df = ds.parent_df

    per_core: dict[str, int] = {}
    if "core" in df.columns:
        per_core = df["core"].value_counts().to_dict()

    per_type: dict[str, int] = {}
    if "event_type" in df.columns:
        per_type = df["event_type"].value_counts().to_dict()

    duration_raw: int | None = None
    duration_ns: float | None = None
    if ds.time_range_raw:
        duration_raw = ds.time_range_raw[1] - ds.time_range_raw[0]
        if ds.time_unit_ns is not None:
            duration_ns = duration_raw * ds.time_unit_ns

    # Compute hot functions by event count using ELF symbol resolution.
    sym_event_counts: Counter = Counter()
    if "address_int" in df.columns:
        for addr in df["address_int"].dropna():
            info = ds.elf.lookup_address(int(addr))
            sym = info.get("symbol")
            if sym:
                sym_event_counts[sym] += 1

    # Compute hot functions by detail (instruction) count.
    sym_instr_counts: Counter = Counter()
    for i, row_details in enumerate(ds.details):
        if i >= len(df):
            break
        addr_int = df.iloc[i].get("address_int") if "address_int" in df.columns else None
        if addr_int is None or addr_int is __import__("pandas").NA:
            continue
        info = ds.elf.lookup_address(int(addr_int))
        sym = info.get("symbol")
        if sym:
            sym_instr_counts[sym] += len(row_details)

    top_by_events = [{"symbol": s, "event_count": c} for s, c in sym_event_counts.most_common(top_n)]
    top_by_instrs = [{"symbol": s, "instruction_count": c} for s, c in sym_instr_counts.most_common(top_n)]

    unresolved: list[str] = []
    if ds.src is not None and "address_int" in df.columns:
        seen: set[str] = set()
        for addr in df["address_int"].dropna():
            info = ds.elf.lookup_address(int(addr))
            dfile = info.get("file") or ""
            if dfile and dfile not in seen:
                seen.add(dfile)
                r = ds.src.resolve(dfile)
                if not r.resolved:
                    unresolved.append(dfile)

    return {
        "trace_id": ds.trace_id,
        "label": ds.label,
        "parent_event_count": ds.row_count,
        "total_detail_count": ds.total_detail_count,
        "cores": ds.cores,
        "per_core_event_counts": per_core,
        "per_type_event_counts": per_type,
        "time_range_raw": list(ds.time_range_raw) if ds.time_range_raw else None,
        "duration_raw": duration_raw,
        "duration_ns": duration_ns,
        "top_functions_by_events": top_by_events,
        "top_functions_by_instructions": top_by_instrs,
        "unresolved_source_files": unresolved[:20],
    }


# ---------------------------------------------------------------------------
# Query: find_event
# ---------------------------------------------------------------------------

def query_find_event(
    ds: TraceDataset,
    selector: dict[str, Any],
    limit: int = _DEFAULT_LIMIT,
    include_source: bool = True,
    include_details: bool = False,
    snippet_window: int | None = None,
) -> dict[str, Any]:
    """Filter parent events by a selector dict and return enriched rows."""
    limit = min(limit, MAX_ROWS)
    df = ds.parent_df

    mask = _match_selector(df, selector)
    matched = df[mask].head(limit)
    total_matches = int(mask.sum())

    budget = [MAX_SRC_BYTES]
    rows: list[dict[str, Any]] = []
    for i, (_, row) in enumerate(matched.iterrows()):
        d = _row_to_dict(row)
        enriched = _enrich_row(d, ds, include_source, snippet_window, budget)
        if include_details:
            idx = df.index.get_loc(row.name)
            enriched["details"] = ds.details[idx] if idx < len(ds.details) else []
        rows.append(enriched)

    return {
        "total_matches": total_matches,
        "returned": len(rows),
        "limit": limit,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Query: address_at
# ---------------------------------------------------------------------------

def query_address_at(
    ds: TraceDataset | None,
    *,
    pc: int | str | None = None,
    symbol: str | None = None,
    elf_index: Any = None,
    src_index: Any = None,
    snippets: Any = None,
    snippet_window: int | None = None,
) -> dict[str, Any]:
    """ELF lookup by address or symbol name.

    When ``ds`` is provided the ELF index is taken from it.
    ``elf_index``, ``src_index``, ``snippets`` override or supply standalone indexes.
    """
    elf = elf_index or (ds.elf if ds else None)
    src = src_index or (ds.src if ds else None)
    snip_reader = snippets or (ds.snippets if ds else None)

    if elf is None:
        return {"error": "No ELF index available."}

    results: list[dict[str, Any]] = []

    if pc is not None:
        addr_int = int(pc, 16) if isinstance(pc, str) and pc.startswith("0x") else int(pc)
        info = elf.lookup_address(addr_int)
        info["address"] = hex(addr_int)
        if src and snip_reader and info.get("file") and info.get("line"):
            resolved = src.resolve(info["file"])
            if resolved.resolved and resolved.local_path:
                info["source_snippet"] = snip_reader.read(resolved.local_path, info["line"], window=snippet_window)
            elif resolved.candidates:
                info["source_candidates"] = resolved.candidates
        results.append(info)

    if symbol is not None:
        matches = elf.lookup_symbol(symbol)
        for m in matches:
            if src and snip_reader and m.get("decl_file") and m.get("addr") is not None:
                # Try to find the definition line via addr_to_line.
                le = elf.addr_to_line.get(m["addr"])
                if le:
                    resolved = src.resolve(le.file)
                    if resolved.resolved and resolved.local_path:
                        m["source_snippet"] = snip_reader.read(resolved.local_path, le.line, window=snippet_window)
            results.append(m)

    return {"results": results, "count": len(results)}


# ---------------------------------------------------------------------------
# Query: time_between
# ---------------------------------------------------------------------------

def query_time_between(
    ds: TraceDataset,
    from_selector: dict[str, Any],
    to_selector: dict[str, Any],
    occurrence: str = "first",
    max_intermediate_symbols: int = _TOP_N,
) -> dict[str, Any]:
    """Measure time delta between two matched events.

    Parameters
    ----------
    occurrence:
        "first" - first match for both selectors.
        "last"  - last match for both selectors.
        "all"   - every consecutive (from, to) pair.
    """
    df = ds.parent_df

    from_mask = _match_selector(df, from_selector)
    to_mask = _match_selector(df, to_selector)

    from_df = df[from_mask]
    to_df = df[to_mask]

    if from_df.empty:
        return {"error": "No events matched the 'from' selector."}
    if to_df.empty:
        return {"error": "No events matched the 'to' selector."}

    def _ts(row: Any) -> int | None:
        v = row.get("timestamp_int")
        if v is None or (isinstance(v, float) and __import__("math").isnan(v)):
            return None
        return int(v)

    def _pair_info(from_row: Any, to_row: Any) -> dict[str, Any]:
        t_from = _ts(from_row)
        t_to = _ts(to_row)
        delta_raw: int | None = (t_to - t_from) if t_from is not None and t_to is not None else None
        delta_ns: float | None = delta_raw * ds.time_unit_ns if delta_raw is not None and ds.time_unit_ns else None

        # Intermediate events between the two timestamps.
        intermediate: Any = df
        if t_from is not None and t_to is not None and "timestamp_int" in df.columns:
            intermediate = df[df["timestamp_int"].between(t_from, t_to)]

        sym_counts: Counter = Counter()
        if "address_int" in intermediate.columns:
            for addr in intermediate["address_int"].dropna():
                info = ds.elf.lookup_address(int(addr))
                sym = info.get("symbol")
                if sym:
                    sym_counts[sym] += 1

        return {
            "from_event": _row_to_dict(from_row),
            "to_event": _row_to_dict(to_row),
            "delta_raw": delta_raw,
            "delta_ns": delta_ns,
            "intermediate_event_count": len(intermediate),
            "top_intermediate_symbols": [
                {"symbol": s, "count": c}
                for s, c in sym_counts.most_common(max_intermediate_symbols)
            ],
        }

    if occurrence == "all":
        pairs = []
        for _, frow in from_df.iterrows():
            t_f = _ts(frow)
            if t_f is None:
                continue
            later_to = to_df[to_df["timestamp_int"] >= t_f]
            if not later_to.empty:
                trow = later_to.iloc[0]
                pairs.append(_pair_info(frow, trow))
        return {"occurrence": "all", "pairs": pairs, "count": len(pairs)}

    if occurrence == "last":
        frow = from_df.iloc[-1]
        trow = to_df.iloc[-1]
    else:
        frow = from_df.iloc[0]
        trow = to_df.iloc[0]

    result = _pair_info(frow, trow)
    result["occurrence"] = occurrence
    return result


# ---------------------------------------------------------------------------
# Query: range_events
# ---------------------------------------------------------------------------

def query_range_events(
    ds: TraceDataset,
    *,
    time_range: list[int] | None = None,
    from_selector: dict[str, Any] | None = None,
    to_selector: dict[str, Any] | None = None,
    include_raw_rows: bool = False,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Return events in a time range or between two selectors."""
    df = ds.parent_df

    if time_range:
        t_lo, t_hi = int(time_range[0]), int(time_range[1])
        if "timestamp_int" in df.columns:
            subset = df[df["timestamp_int"].between(t_lo, t_hi)]
        else:
            subset = df
    elif from_selector and to_selector:
        from_mask = _match_selector(df, from_selector)
        to_mask = _match_selector(df, to_selector)
        from_df = df[from_mask]
        to_df = df[to_mask]
        if from_df.empty or to_df.empty:
            return {"error": "One or both selectors matched nothing."}
        t_from = from_df.iloc[0].get("timestamp_int")
        t_to = to_df.iloc[0].get("timestamp_int")
        if t_from is None or t_to is None or "timestamp_int" not in df.columns:
            subset = df
        else:
            subset = df[df["timestamp_int"].between(int(t_from), int(t_to))]
    else:
        return {"error": "Provide either 'time_range' or both 'from_selector' and 'to_selector'."}

    sym_counts: Counter = Counter()
    file_counts: Counter = Counter()
    type_counts: Counter = Counter()

    if "address_int" in subset.columns:
        for addr in subset["address_int"].dropna():
            info = ds.elf.lookup_address(int(addr))
            sym = info.get("symbol")
            if sym:
                sym_counts[sym] += 1
            f = info.get("file")
            if f:
                import os
                file_counts[os.path.basename(f)] += 1

    if "event_type" in subset.columns:
        type_counts = Counter(subset["event_type"].dropna().tolist())

    raw_rows: list[dict[str, Any]] = []
    if include_raw_rows:
        budget = [MAX_SRC_BYTES]
        for _, row in subset.head(min(limit, MAX_ROWS)).iterrows():
            raw_rows.append(_enrich_row(_row_to_dict(row), ds, True, None, budget))

    return {
        "event_count": len(subset),
        "top_symbols": [{"symbol": s, "count": c} for s, c in sym_counts.most_common(_TOP_N)],
        "top_files": [{"file": f, "count": c} for f, c in file_counts.most_common(_TOP_N)],
        "top_event_types": [{"type": t, "count": c} for t, c in type_counts.most_common()],
        "raw_rows": raw_rows if include_raw_rows else None,
    }


# ---------------------------------------------------------------------------
# Query: get_source
# ---------------------------------------------------------------------------

def query_get_source(
    ds: TraceDataset,
    *,
    file_hint: str | None = None,
    line: int | None = None,
    symbol: str | None = None,
    snippet_window: int | None = None,
) -> dict[str, Any]:
    """Fetch a source snippet by file:line or symbol name."""
    if ds.src is None:
        return {"error": "No source root is configured for this trace session."}

    if symbol is not None:
        matches = ds.elf.lookup_symbol(symbol)
        if not matches:
            return {"error": f"Symbol '{symbol}' not found in ELF."}
        addr = matches[0]["addr"]
        le = ds.elf.addr_to_line.get(addr)
        if le is None:
            return {"error": f"No DWARF line info for symbol '{symbol}'."}
        file_hint = le.file
        line = le.line

    if not file_hint or line is None:
        return {"error": "Provide 'file_hint' + 'line' or 'symbol'."}

    resolved = ds.src.resolve(file_hint)
    if not resolved.resolved:
        if resolved.candidates:
            return {
                "resolved": False,
                "candidates": resolved.candidates,
                "message": "Multiple source files match this name. Re-call with the exact path.",
            }
        return {
            "resolved": False,
            "dwarf_path": file_hint,
            "message": "Source file could not be resolved to a local path.",
        }

    snip = ds.snippets.read(resolved.local_path, line, window=snippet_window)
    if snip is None:
        return {"error": f"Could not read file: {resolved.local_path}"}

    return {"resolved": True, "snippet": snip}
