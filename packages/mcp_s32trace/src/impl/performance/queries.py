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

"""Query functions for performance.* MCP actions.

All functions accept a PerformanceDataset and return plain dicts suitable
for JSON serialisation.  None of them mutate the dataset.
"""

from __future__ import annotations

import heapq
import math
from typing import Any

from nxp.mcp.s32trace.impl.performance.performance_dataset import PerformanceDataset
from nxp.mcp.s32trace.impl.performance.perf_loader import FunctionRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(v: float) -> float | None:
    return None if math.isnan(v) else round(v, 2)


def _fn_dict(core: str, fn: FunctionRecord) -> dict[str, Any]:
    return {
        "name": fn.name,
        "core": core,
        "num_calls": fn.num_calls,
        "inclusive": fn.inclusive,
        "avg_inclusive": _pct(fn.avg_inclusive),
        "pct_inclusive": _pct(fn.pct_inclusive),
        "exclusive": fn.exclusive,
        "avg_exclusive": _pct(fn.avg_exclusive),
        "pct_exclusive": _pct(fn.pct_exclusive),
        "pct_total_calls": _pct(fn.pct_total_calls),
        "code_size": fn.code_size,
    }


# ---------------------------------------------------------------------------
# performance.summary
# ---------------------------------------------------------------------------

def query_performance_summary(
    ds: PerformanceDataset,
    core: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    funcs = ds.functions_for_core(core)
    total_calls = sum(fn.num_calls for _, fn in funcs)

    top_inclusive = [
        _fn_dict(c, fn)
        for c, fn in heapq.nlargest(top_k, funcs, key=lambda t: t[1].inclusive)
    ]
    top_exclusive = [
        _fn_dict(c, fn)
        for c, fn in heapq.nlargest(top_k, funcs, key=lambda t: t[1].exclusive)
    ]
    top_calls = [
        _fn_dict(c, fn)
        for c, fn in heapq.nlargest(top_k, funcs, key=lambda t: t[1].num_calls)
    ]

    return {
        "session_id": ds.session_id,
        "label": ds.label,
        "cores_included": [c.name for c in ds.data.cores] if not core else [core],
        "total_functions": len(funcs),
        "total_calls": total_calls,
        "top_by_inclusive_time": top_inclusive,
        "top_by_exclusive_time": top_exclusive,
        "top_by_call_count": top_calls,
    }


# ---------------------------------------------------------------------------
# performance.hotspots
# ---------------------------------------------------------------------------

def query_performance_hotspots(
    ds: PerformanceDataset,
    sort_by: str = "inclusive",
    top_k: int = 10,
    core: str | None = None,
) -> dict[str, Any]:
    funcs = ds.functions_for_core(core)
    key_map = {
        "inclusive": lambda t: t[1].inclusive,
        "exclusive": lambda t: t[1].exclusive,
        "calls": lambda t: t[1].num_calls,
    }
    key = key_map.get(sort_by, key_map["inclusive"])
    top = heapq.nlargest(top_k, funcs, key=key)
    return {
        "sort_by": sort_by,
        "items": [_fn_dict(c, fn) for c, fn in top],
    }


# ---------------------------------------------------------------------------
# performance.function
# ---------------------------------------------------------------------------

def query_performance_function(
    ds: PerformanceDataset,
    name: str,
    core: str | None = None,
) -> dict[str, Any]:
    entries = ds.find_functions_by_name(name, core_name=core)
    if not entries:
        return {"found": False, "name": name, "instances": []}

    instances = []
    for core_name, fn in entries:
        inst = _fn_dict(core_name, fn)
        # Callers and callees from per-function call_pairs
        callees: list[dict[str, Any]] = []
        callers_map: dict[str, dict[str, Any]] = {}
        for cp in fn.call_pairs:
            if cp.caller == fn.name:
                callees.append({
                    "callee": cp.callee,
                    "num_calls": cp.num_calls,
                    "avg_inclusive_callee": _pct(cp.avg_inclusive_callee),
                    "pct_callee": _pct(cp.pct_callee),
                    "pct_caller": _pct(cp.pct_caller),
                    "call_site": hex(cp.call_site) if cp.call_site else None,
                })
            else:
                # call pair where fn is the callee - track callers
                callers_map[cp.caller] = {
                    "caller": cp.caller,
                    "num_calls": cp.num_calls,
                    "pct_caller": _pct(cp.pct_caller),
                }
        inst["callees"] = callees
        inst["callers"] = list(callers_map.values())
        instances.append(inst)

    return {"found": True, "name": name, "instances": instances}


# ---------------------------------------------------------------------------
# performance.callgraph
# ---------------------------------------------------------------------------

def query_performance_callgraph(
    ds: PerformanceDataset,
    root: str,
    depth: int = 3,
    direction: str = "callees",
    core: str | None = None,
) -> dict[str, Any]:
    """Return a nested call-graph tree rooted at `root`.

    direction='callees'  -> show what root calls (downward tree)
    direction='callers'  -> show who calls root (upward tree)
    """
    if direction not in ("callees", "callers"):
        return {"error": f"direction must be 'callees' or 'callers', got '{direction}'."}

    entries = ds.find_functions_by_name(root, core_name=core)
    if not entries:
        return {"found": False, "root": root}

    _, root_fn = entries[0]

    def _expand(name: str, remaining: int, visited: set[str]) -> dict[str, Any]:
        fn_entries = ds.find_functions_by_name(name, core_name=core)
        node: dict[str, Any] = {"name": name}
        if fn_entries:
            _, fn = fn_entries[0]
            node["num_calls"] = fn.num_calls
            node["pct_inclusive"] = _pct(fn.pct_inclusive)
            node["pct_exclusive"] = _pct(fn.pct_exclusive)
        if remaining <= 0 or name in visited:
            node["truncated"] = True
            return node
        visited = visited | {name}
        neighbors = ds.callees_of(name) if direction == "callees" else ds.callers_of(name)
        children = [_expand(n, remaining - 1, visited) for n in neighbors]
        if children:
            node["children"] = children
        return node

    tree = _expand(root, depth, set())
    return {
        "found": True,
        "root": root,
        "direction": direction,
        "depth": depth,
        "tree": tree,
    }


# ---------------------------------------------------------------------------
# performance.get_source
# ---------------------------------------------------------------------------

def query_performance_get_source(
    ds: PerformanceDataset,
    symbol: str | None = None,
    file_hint: str | None = None,
    line: int | None = None,
    core: str | None = None,
    snippet_window: int | None = None,
) -> dict[str, Any]:
    window = snippet_window or ds.snippet_window

    if not symbol and not file_hint:
        return {"found": False, "reason": "Provide 'symbol' or 'file_hint'."}

    # Resolve target file + anchor line via ELF DWARF.
    target_file: str | None = None
    target_line: int | None = line
    fn_context: dict[str, Any] = {}

    if symbol:
        entries = ds.find_functions_by_name(symbol, core_name=core)
        if not entries:
            return {"found": False, "reason": f"Symbol '{symbol}' not found in performance data."}
        core_name, fn = entries[0]
        fn_context = _fn_dict(core_name, fn)
        # Resolve file + line from ELF DWARF index.
        if ds.elf_index:
            info = ds.elf_index.lookup_symbol(symbol)
            if info:
                target_file = info.get("file")
                if target_line is None:
                    target_line = info.get("line")

    if target_file is None and file_hint:
        target_file = file_hint

    if not target_file:
        return {
            "found": True,
            "source_available": False,
            "reason": "ELF DWARF info unavailable or symbol has no source mapping.",
            "function": fn_context,
        }

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
        return {
            "found": True,
            "source_available": False,
            "dwarf_path": target_file,
            "local_path": None,
            "function": fn_context,
        }

    anchor = target_line or 1
    snippet = ds.snippets.read(local_path, anchor, window=window)
    if snippet is None:
        return {"found": True, "source_available": False, "reason": f"Could not read {local_path}"}

    return {
        "found": True,
        "source_available": True,
        "dwarf_path": target_file,
        "local_path": local_path,
        "target_line": anchor,
        "window_start": snippet["window_start"],
        "window_end": snippet["window_end"],
        "function": fn_context,
        "lines": snippet["lines"],
    }
