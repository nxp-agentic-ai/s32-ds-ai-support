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

"""Query functions that implement the coverage.* MCP actions.

All functions accept a CoverageDataset and return plain dicts suitable for
JSON serialisation.  None of them mutate the dataset.
"""

from __future__ import annotations

import heapq
import math
import os
import re
from typing import Any

from nxp.mcp.s32trace.impl.coverage.coverage_dataset import CoverageDataset
from nxp.mcp.s32trace.impl.coverage.flatprofiler_loader import (
    FileRecord,
    FunctionRecord,
    NO_SOURCE_INFO,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(v: float) -> float | None:
    return None if math.isnan(v) else round(v, 2)


def _func_summary(core: str, fr: FileRecord, fn: FunctionRecord) -> dict[str, Any]:
    return {
        "name": fn.name,
        "file": fr.path,
        "core": core,
        "address": hex(fn.address) if fn.address else None,
        "covered_asm_pct": _pct(fn.covered_asm_pct),
        "covered_src_pct": _pct(fn.covered_src_pct),
        "partially_covered_src_pct": _pct(fn.partially_covered_src_pct),
        "asm_decision_coverage_pct": _pct(fn.asm_decision_coverage_pct),
        "total_asm": fn.total_asm,
        "total_src_lines": fn.total_src_lines,
        "time": fn.time,
        "size": fn.size,
    }


def _file_summary(fr: FileRecord, core: str) -> dict[str, Any]:
    return {
        "path": fr.path,
        "core": core,
        "covered_asm_pct": _pct(fr.covered_asm_pct),
        "covered_src_pct": _pct(fr.covered_src_pct),
        "partially_covered_src_pct": _pct(fr.partially_covered_src_pct),
        "asm_decision_coverage_pct": _pct(fr.asm_decision_coverage_pct),
        "total_asm": fr.total_asm,
        "total_src_lines": fr.total_src_lines,
        "time": fr.time,
        "size": fr.size,
        "function_count": len(fr.functions),
    }


# ---------------------------------------------------------------------------
# coverage.summary
# ---------------------------------------------------------------------------

def query_coverage_summary(
    ds: CoverageDataset,
    core: str | None = None,
    top_k: int = 10,
    include_no_source_info: bool = False,
) -> dict[str, Any]:
    funcs = ds.functions_for_core(core, include_no_source_info=include_no_source_info)
    files = ds.files_for_core(core, include_no_source_info=include_no_source_info)

    total_asm = sum(fn.total_asm for _, _, fn in funcs)
    covered_asm = sum(
        round(fn.total_asm * fn.covered_asm_pct / 100)
        for _, _, fn in funcs
        if not math.isnan(fn.covered_asm_pct)
    )
    total_src = sum(fn.total_src_lines for _, _, fn in funcs)
    covered_src = sum(
        round(fn.total_src_lines * fn.covered_src_pct / 100)
        for _, _, fn in funcs
        if not math.isnan(fn.covered_src_pct)
    )

    overall_asm_pct = round(covered_asm / total_asm * 100, 2) if total_asm else None
    overall_src_pct = round(covered_src / total_src * 100, 2) if total_src else None

    fully_covered = [
        _func_summary(c, f, fn) for c, f, fn in funcs
        if not math.isnan(fn.covered_asm_pct) and fn.covered_asm_pct >= 100.0
    ]
    fully_uncovered = [
        _func_summary(c, f, fn) for c, f, fn in funcs
        if not math.isnan(fn.covered_asm_pct) and fn.covered_asm_pct == 0.0
    ]
    partial = [
        _func_summary(c, f, fn) for c, f, fn in funcs
        if not math.isnan(fn.covered_asm_pct) and 0.0 < fn.covered_asm_pct < 100.0
    ]

    top_by_time = [
        _func_summary(c, f, fn)
        for c, f, fn in heapq.nlargest(
            top_k,
            ((c, f, fn) for c, f, fn in funcs if fn.time > 0),
            key=lambda t: t[2].time,
        )
    ]

    top_uncovered_by_size = [
        _func_summary(c, f, fn)
        for c, f, fn in heapq.nlargest(
            top_k,
            ((c, f, fn) for c, f, fn in funcs
             if not math.isnan(fn.covered_asm_pct) and fn.covered_asm_pct == 0.0 and fn.size > 0),
            key=lambda t: t[2].size,
        )
    ]

    # funcs is a list of (core_name, file, func) tuples. When core is None it
    # spans all cores, so metrics are per-instance (same symbol on two cores
    # counts twice). The field names below reflect that.
    return {
        "session_id": ds.session_id,
        "label": ds.label,
        "cores_included": [c.name for c in ds.data.cores] if not core else [core],
        "overall": {
            "asm_coverage_pct": overall_asm_pct,
            "src_coverage_pct": overall_src_pct,
            "total_function_instances": len(funcs),
            "fully_covered_function_instances": len(fully_covered),
            "partially_covered_function_instances": len(partial),
            "fully_uncovered_function_instances": len(fully_uncovered),
            "total_file_instances": len(files),
        },
        "top_by_time": top_by_time,
        "top_uncovered_by_size": top_uncovered_by_size,
    }


# ---------------------------------------------------------------------------
# coverage.function
# ---------------------------------------------------------------------------

def query_coverage_function(
    ds: CoverageDataset,
    name: str,
    core: str | None = None,
    include_source_rows: bool = True,
) -> dict[str, Any]:
    entries = ds.find_functions_by_name(name, core_name=core)
    if not entries:
        return {"found": False, "name": name, "instances": []}

    instances = []
    for core_name, fr, fn in entries:
        inst: dict[str, Any] = _func_summary(core_name, fr, fn)
        if include_source_rows and fn.source_rows:
            src_lines = []
            for sr in fn.source_rows:
                if sr.line_no == 0:
                    continue
                src_lines.append({
                    "line": sr.line_no,
                    "file": sr.file or fr.path,
                    "coverage": sr.coverage,
                    "asm_count": sr.asm_count,
                    "time": sr.time,
                })
            inst["source_lines"] = src_lines
        instances.append(inst)

    return {"found": True, "name": name, "instances": instances}


# ---------------------------------------------------------------------------
# coverage.file
# ---------------------------------------------------------------------------

def query_coverage_file(
    ds: CoverageDataset,
    file_hint: str,
    core: str | None = None,
) -> dict[str, Any]:
    matches = ds.find_file_by_hint(file_hint, core_name=core)
    if not matches:
        return {"found": False, "file_hint": file_hint, "files": []}

    results = []
    for fr in matches:
        core_name = next(
            (c.name for c in ds.data.cores if any(f is fr for f in c.files)),
            "unknown",
        )
        entry: dict[str, Any] = _file_summary(fr, core_name)

        uncovered_ranges: list[dict[str, Any]] = []
        for fn in fr.functions:
            if fn.covered_asm_pct == 0.0:
                uncovered_ranges.append({
                    "function": fn.name,
                    "address": hex(fn.address) if fn.address else None,
                    "size": fn.size,
                    "total_src_lines": fn.total_src_lines,
                })
        entry["fully_uncovered_functions"] = uncovered_ranges

        covered_line_count = 0
        uncovered_line_count = 0
        for fn in fr.functions:
            for sr in fn.source_rows:
                if sr.line_no == 0:
                    continue
                if sr.coverage == "covered":
                    covered_line_count += 1
                elif sr.coverage == "not covered":
                    uncovered_line_count += 1
        entry["covered_lines_detail"] = covered_line_count
        entry["uncovered_lines_detail"] = uncovered_line_count

        results.append(entry)

    return {"found": True, "file_hint": file_hint, "files": results}


# ---------------------------------------------------------------------------
# coverage.uncovered
# ---------------------------------------------------------------------------

def query_coverage_uncovered(
    ds: CoverageDataset,
    granularity: str = "function",
    sort_by: str = "size",
    top_k: int = 20,
    core: str | None = None,
    include_no_source_info: bool = False,
) -> dict[str, Any]:
    funcs = ds.functions_for_core(core, include_no_source_info=include_no_source_info)

    if granularity == "function":
        uncovered_all = [
            (c, f, fn) for c, f, fn in funcs
            if not math.isnan(fn.covered_asm_pct) and fn.covered_asm_pct == 0.0
        ]
        key_attr = "size" if sort_by == "size" else "total_src_lines"
        top = heapq.nlargest(top_k, uncovered_all, key=lambda t: getattr(t[2], key_attr) or 0)
        return {
            "granularity": "function",
            "total_uncovered": len(uncovered_all),
            "items": [_func_summary(c, f, fn) for c, f, fn in top],
        }

    if granularity in ("line", "asm"):
        items: list[dict[str, Any]] = []
        for core_name, fr, fn in funcs:
            for sr in fn.source_rows:
                if sr.line_no == 0:
                    continue
                if granularity == "line" and sr.coverage == "not covered":
                    items.append({
                        "file": sr.file or fr.path,
                        "line": sr.line_no,
                        "function": fn.name,
                        "core": core_name,
                        "asm_count": sr.asm_count,
                    })
                elif granularity == "asm":
                    for ar in sr.asm_rows:
                        if ar.coverage == "not covered":
                            items.append({
                                "address": hex(ar.address),
                                "instruction": ar.instruction,
                                "file": sr.file or fr.path,
                                "line": sr.line_no,
                                "function": fn.name,
                                "core": core_name,
                            })
        return {
            "granularity": granularity,
            "total_uncovered": len(items),
            "items": heapq.nsmallest(top_k, items, key=lambda x: x.get("line", 0)),
        }

    return {"error": f"Unknown granularity '{granularity}'. Use 'function', 'line', or 'asm'."}


# ---------------------------------------------------------------------------
# coverage.hotspots
# ---------------------------------------------------------------------------

def query_coverage_hotspots(
    ds: CoverageDataset,
    sort_by: str = "time",
    granularity: str = "function",
    top_k: int = 10,
    core: str | None = None,
    include_no_source_info: bool = False,
) -> dict[str, Any]:
    funcs = ds.functions_for_core(core, include_no_source_info=include_no_source_info)

    if granularity == "function":
        key = sort_by if sort_by in ("time", "total_asm", "size") else "time"
        top = heapq.nlargest(
            top_k,
            ((c, f, fn) for c, f, fn in funcs if fn.time > 0 or fn.total_asm > 0),
            key=lambda t: getattr(t[2], key) or 0,
        )
        return {"granularity": "function", "sort_by": sort_by, "items": [_func_summary(c, f, fn) for c, f, fn in top]}

    if granularity == "line":
        items: list[dict[str, Any]] = []
        for core_name, fr, fn in funcs:
            for sr in fn.source_rows:
                if sr.line_no == 0 or sr.time == 0:
                    continue
                items.append({
                    "file": sr.file or fr.path,
                    "line": sr.line_no,
                    "function": fn.name,
                    "core": core_name,
                    "time": sr.time,
                    "asm_count": sr.asm_count,
                    "coverage": sr.coverage,
                })
        key = sort_by if sort_by in ("time", "asm_count") else "time"
        return {"granularity": "line", "sort_by": sort_by, "items": heapq.nlargest(top_k, items, key=lambda x: x.get(key, 0) or 0)}

    return {"error": f"Unknown granularity '{granularity}'. Use 'function' or 'line'."}


# ---------------------------------------------------------------------------
# coverage.get_source
# ---------------------------------------------------------------------------

def query_coverage_get_source(
    ds: CoverageDataset,
    symbol: str | None = None,
    file_hint: str | None = None,
    line: int | None = None,
    core: str | None = None,
    snippet_window: int | None = None,
) -> dict[str, Any]:
    window = snippet_window or ds.snippet_window

    # Resolve target file + line from symbol or direct file+line.
    target_file: str | None = None
    target_line: int | None = line
    coverage_context: list[dict[str, Any]] = []

    if symbol:
        entries = ds.find_functions_by_name(symbol, core_name=core)
        if not entries:
            return {"found": False, "reason": f"Symbol '{symbol}' not found in coverage data."}
        core_name, fr, fn = entries[0]
        target_file = fr.path
        # Use first covered source row as anchor if no explicit line given.
        if target_line is None and fn.source_rows:
            first_real = next((sr for sr in fn.source_rows if sr.line_no > 0), None)
            if first_real:
                target_line = first_real.line_no
                if first_real.file:
                    target_file = first_real.file
        # Collect per-line coverage context from the function's source rows.
        for sr in fn.source_rows:
            if sr.line_no == 0:
                continue
            coverage_context.append({
                "line": sr.line_no,
                "coverage": sr.coverage,
                "asm_count": sr.asm_count,
                "time": sr.time,
            })

    elif file_hint:
        file_matches = ds.find_file_by_hint(file_hint, core_name=core)
        if not file_matches:
            return {"found": False, "reason": f"File '{file_hint}' not found in coverage data."}
        target_file = file_matches[0].path
        fr = file_matches[0]
        for fn in fr.functions:
            for sr in fn.source_rows:
                if sr.line_no == 0:
                    continue
                coverage_context.append({
                    "line": sr.line_no,
                    "coverage": sr.coverage,
                    "asm_count": sr.asm_count,
                    "time": sr.time,
                })

    if not target_file:
        return {"found": False, "reason": "Provide 'symbol' or 'file_hint'."}

    # Build coverage_by_line map for annotation.
    cov_by_line: dict[int, str] = {row["line"]: row["coverage"] for row in coverage_context}
    time_by_line: dict[int, int] = {row["line"]: row["time"] for row in coverage_context}

    # Resolve local path via source index.
    local_path: str | None = None
    if ds.src_index:
        resolved = ds.src_index.resolve(target_file)
        if resolved.resolved and resolved.local_path and ds.src_index.is_safe_path(resolved.local_path):
            local_path = resolved.local_path
        elif resolved.candidates:
            return {
                "found": False,
                "reason": (
                    f"Ambiguous file '{target_file}': "
                    f"{len(resolved.candidates)} matches found. "
                    f"Provide a more specific path."
                ),
                "candidates": resolved.candidates[:5],
                "dwarf_path": target_file,
            }

    if local_path is None:
        # Return coverage data without source text.
        result_lines = []
        for ctx in sorted(coverage_context, key=lambda x: x["line"]):
            result_lines.append({
                "n": ctx["line"],
                "coverage": ctx["coverage"],
                "time": ctx["time"],
                "asm_count": ctx["asm_count"],
            })
        return {
            "found": True,
            "source_available": False,
            "dwarf_path": target_file,
            "local_path": None,
            "lines": result_lines,
        }

    # Read snippet and annotate with coverage.
    anchor = target_line or 1
    snippet = ds.snippets.read(local_path, anchor, window=window)
    if snippet is None:
        return {"found": True, "source_available": False, "reason": f"Could not read {local_path}"}

    for ln_entry in snippet["lines"]:
        ln = ln_entry["n"]
        ln_entry["coverage"] = cov_by_line.get(ln, "")
        ln_entry["time"] = time_by_line.get(ln, 0)

    return {
        "found": True,
        "source_available": True,
        "dwarf_path": target_file,
        "local_path": local_path,
        "target_line": anchor,
        "window_start": snippet["window_start"],
        "window_end": snippet["window_end"],
        "lines": snippet["lines"],
    }
