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

"""Query functions for timeline analysis sessions."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from .timeline_dataset import TimelineDataset
from .timeline_loader import FunctionEntry, DataRow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fn_key(fn: FunctionEntry) -> str:
    return fn.name


def _aggregate_by_function(
    ds: TimelineDataset,
    source_name: str | None,
) -> dict[str, dict[str, Any]]:
    """Return per-function aggregates: total_samples, total_time, call_count."""
    sources = ds._filter_sources(source_name)
    agg: dict[str, dict[str, Any]] = {}

    for src in sources:
        fn_by_addr: dict[int, FunctionEntry] = {}
        for fn in src.functions:
            fn_by_addr[fn.address] = fn

        for row in src.rows:
            fn = ds.resolve_function(row.address, src.name)
            if fn is None:
                continue
            key = _fn_key(fn)
            if key not in agg:
                agg[key] = {
                    "name": fn.name,
                    "address": fn.address,
                    "size": fn.size,
                    "total_samples": 0,
                    "total_time": 0,
                    "observations": 0,
                }
            entry = agg[key]
            entry["total_samples"] += row.sample_count
            entry["total_time"] += row.timestamp
            if row.sample_count > 0:
                entry["observations"] += 1

    return agg


# ---------------------------------------------------------------------------
# Public queries
# ---------------------------------------------------------------------------

def query_timeline_summary(
    ds: TimelineDataset,
    source_name: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """Return an overall summary: function list, hotspots, timestamp range."""
    agg = _aggregate_by_function(ds, source_name)
    total_samples = sum(v["total_samples"] for v in agg.values())

    hotspots = sorted(agg.values(), key=lambda x: x["total_samples"], reverse=True)[:top_k]
    for h in hotspots:
        h["pct"] = round(h["total_samples"] / total_samples * 100, 2) if total_samples else 0.0

    return {
        "sources": ds.source_names,
        "function_count": ds.function_count,
        "data_row_count": ds.row_count,
        "timestamp_range": list(ds.timestamp_range) if ds.timestamp_range else None,
        "total_samples": total_samples,
        "top_functions_by_samples": hotspots,
    }


def query_timeline_hotspots(
    ds: TimelineDataset,
    source_name: str | None = None,
    sort_by: str = "samples",
    top_k: int = 10,
) -> dict[str, Any]:
    """Return top-k functions ranked by samples or time."""
    agg = _aggregate_by_function(ds, source_name)
    total_samples = sum(v["total_samples"] for v in agg.values())

    key_fn = (lambda x: x["total_time"]) if sort_by == "time" else (lambda x: x["total_samples"])
    ranked = sorted(agg.values(), key=key_fn, reverse=True)[:top_k]
    for r in ranked:
        r["pct"] = round(r["total_samples"] / total_samples * 100, 2) if total_samples else 0.0

    return {
        "sort_by": sort_by,
        "total_samples": total_samples,
        "hotspots": ranked,
    }


def query_timeline_function(
    ds: TimelineDataset,
    name: str,
    source_name: str | None = None,
    include_source: bool = True,
) -> dict[str, Any]:
    """Return detailed stats for a named function including per-address samples."""
    sources = ds._filter_sources(source_name)
    matches: list[FunctionEntry] = []
    for src in sources:
        for fn in src.functions:
            if fn.name == name or fn.name.startswith(name + "_0x"):
                if fn not in matches:
                    matches.append(fn)

    if not matches:
        return {"found": False, "name": name}

    results = []
    for fn in matches:
        addr_samples: dict[int, int] = defaultdict(int)
        addr_time: dict[int, int] = defaultdict(int)
        for src in sources:
            for row in src.rows:
                hit = ds.resolve_function(row.address, src.name)
                if hit and hit.name == fn.name and hit.address == fn.address:
                    addr_samples[row.address] += row.sample_count
                    addr_time[row.address] += row.timestamp

        total_samples = sum(addr_samples.values())
        entry: dict[str, Any] = {
            "name": fn.name,
            "address": hex(fn.address),
            "size": fn.size,
            "is_stub": fn.is_stub,
            "total_samples": total_samples,
            "per_address": [
                {"address": hex(a), "samples": s, "time": addr_time[a]}
                for a, s in sorted(addr_samples.items())
            ],
        }

        # Optionally attach source info via DWARF
        if include_source and ds.elf:
            loc = ds.elf.lookup_address(fn.address)
            if loc.get("file"):
                entry["source_file"] = loc.get("file")
                entry["source_line"] = loc.get("line")
                if ds.src:
                    resolved = ds.src.resolve(loc["file"])
                    if resolved.resolved and resolved.local_path:
                        snippet = ds.snippets.read(
                            resolved.local_path,
                            loc.get("line", 1),
                            window=ds.snippet_window,
                        )
                        if snippet:
                            entry["source_snippet"] = snippet

        results.append(entry)

    return {"found": True, "name": name, "instances": results}


def query_timeline_source(
    ds: TimelineDataset,
    symbol: str | None = None,
    file_hint: str | None = None,
    line: int | None = None,
    source_name: str | None = None,
    snippet_window: int | None = None,
) -> dict[str, Any]:
    """Return a source snippet annotated with sample counts per line."""
    if not ds.elf:
        return {"error": "No ELF loaded; source lookup requires elf_path."}
    if not ds.src:
        return {"error": "No source root indexed; provide source_root on load."}

    window = snippet_window or ds.snippet_window

    # Resolve target file + center line
    target_file: str | None = None
    center_line: int | None = line

    if symbol:
        # Find address of symbol via function list, then DWARF lookup
        sources = ds._filter_sources(source_name)
        for src in sources:
            for fn in src.functions:
                if fn.name == symbol or fn.name.startswith(symbol + "_0x"):
                    loc = ds.elf.lookup_address(fn.address)
                    if loc.get("file"):
                        target_file = loc.get("file")
                        center_line = center_line or loc.get("line", 1)
                    break
            if target_file:
                break

    if file_hint and not target_file:
        resolved = ds.src.resolve(file_hint)
        target_file = resolved.local_path if resolved.resolved else None

    if not target_file:
        return {"error": f"Could not resolve source file for symbol={symbol!r} / file_hint={file_hint!r}."}

    # Resolve to a local path safe for reading.
    resolved_file = ds.src.resolve(target_file)
    if not resolved_file.resolved or not resolved_file.local_path:
        if resolved_file.candidates:
            return {
                "error": (
                    f"Ambiguous file '{target_file}': "
                    f"{len(resolved_file.candidates)} matches. "
                    f"Provide a more specific path."
                ),
                "candidates": resolved_file.candidates[:5],
            }
        return {"error": f"Could not resolve source file: {target_file}"}

    local_path = resolved_file.local_path
    center_line = center_line or 1
    snippet = ds.snippets.read(local_path, center_line, window=window)
    if not snippet:
        return {"error": f"Could not read source file: {local_path}"}

    # Annotate each line with sample counts.
    agg = _aggregate_samples_by_dwarf_line(ds, target_file, source_name)
    lines_out = []
    for sl in snippet.get("lines", []):
        ln = sl.get("n", 0)
        sl["samples"] = agg.get(ln, 0)
        lines_out.append(sl)

    return {
        "file": target_file,
        "local_path": local_path,
        "center_line": center_line,
        "lines": lines_out,
    }


def _aggregate_samples_by_dwarf_line(
    ds: TimelineDataset,
    target_file: str,
    source_name: str | None,
) -> dict[int, int]:
    """Map source line number -> total sample count via DWARF address lookup."""
    if not ds.elf:
        return {}
    line_samples: dict[int, int] = defaultdict(int)
    sources = ds._filter_sources(source_name)
    for src in sources:
        for row in src.rows:
            if row.sample_count == 0:
                continue
            loc = ds.elf.lookup_address(row.address)
            if loc and loc.get("file") == target_file:
                ln = loc.get("line", 0)
                if ln:
                    line_samples[ln] += row.sample_count
    return dict(line_samples)


def query_timeline_window(
    ds: TimelineDataset,
    start_tick: int | None = None,
    end_tick: int | None = None,
    source_name: str | None = None,
    top_k: int = 20,
) -> dict[str, Any]:
    """Return function-level aggregates within a tick window."""
    sources = ds._filter_sources(source_name)
    agg: dict[str, dict[str, Any]] = {}

    for src in sources:
        for row in src.rows:
            if start_tick is not None and row.timestamp < start_tick:
                continue
            if end_tick is not None and row.timestamp > end_tick:
                continue
            fn = ds.resolve_function(row.address, src.name)
            if fn is None:
                continue
            key = fn.name
            if key not in agg:
                agg[key] = {"name": fn.name, "address": fn.address, "total_samples": 0}
            agg[key]["total_samples"] += row.sample_count

    total = sum(v["total_samples"] for v in agg.values())
    ranked = sorted(agg.values(), key=lambda x: x["total_samples"], reverse=True)[:top_k]
    for r in ranked:
        r["pct"] = round(r["total_samples"] / total * 100, 2) if total else 0.0

    return {
        "start_tick": start_tick,
        "end_tick": end_tick,
        "total_samples_in_window": total,
        "functions": ranked,
    }


def query_timeline_call_sequence(
    ds: TimelineDataset,
    source_name: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Return an ordered list of function transitions (PC changes over time)."""
    sources = ds._filter_sources(source_name)
    transitions: list[dict[str, Any]] = []
    prev_name: str | None = None

    for src in sources:
        for row in sorted(src.rows, key=lambda r: r.timestamp):
            fn = ds.resolve_function(row.address, src.name)
            name = fn.name if fn else hex(row.address)
            if name != prev_name:
                transitions.append({
                    "timestamp": row.timestamp,
                    "address": hex(row.address),
                    "function": name,
                    "samples": row.sample_count,
                })
                prev_name = name
            if len(transitions) >= limit:
                break
        if len(transitions) >= limit:
            break

    return {"limit": limit, "transitions": transitions}
