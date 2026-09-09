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

"""In-memory indexed model for a loaded .perf session."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nxp.mcp.s32trace.impl.common.elf_index import ElfIndex
from nxp.mcp.s32trace.impl.common.source_index import SourceIndex
from nxp.mcp.s32trace.impl.common.source_snippet import SourceSnippet
from nxp.mcp.s32trace.impl.performance.perf_loader import (
    PerfData,
    FunctionRecord,
    load_perf,
)


@dataclass
class PerformanceDataset:
    """Loaded and indexed performance session."""

    session_id: str
    perf_path: str
    label: str
    data: PerfData
    elf_index: ElfIndex | None
    src_index: SourceIndex | None
    snippets: SourceSnippet
    snippet_window: int = 5

    _func_by_name: dict[str, list[tuple[str, FunctionRecord]]] = field(
        default_factory=dict, init=False, repr=False
    )
    # caller -> set of callee names; callee -> set of caller names
    _callees: dict[str, set[str]] = field(default_factory=dict, init=False, repr=False)
    _callers: dict[str, set[str]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._build_indexes()

    @classmethod
    def load(
        cls,
        session_id: str,
        perf_path: str,
        elf_path: str | None,
        source_root: str | None,
        extra_source_roots: list[str] | None = None,
        label: str | None = None,
        snippet_window: int = 5,
    ) -> "PerformanceDataset":
        data = load_perf(perf_path)

        elf_index: ElfIndex | None = None
        if elf_path:
            elf_index = ElfIndex.from_file(elf_path)

        src_index: SourceIndex | None = None
        roots: list[str] = []
        if source_root:
            roots.append(source_root)
        if extra_source_roots:
            roots.extend(extra_source_roots)
        if roots:
            src_index = SourceIndex.from_roots(roots)

        return cls(
            session_id=session_id,
            perf_path=str(perf_path),
            label=label or Path(perf_path).name,
            data=data,
            elf_index=elf_index,
            src_index=src_index,
            snippets=SourceSnippet(default_window=snippet_window),
            snippet_window=snippet_window,
        )

    def _build_indexes(self) -> None:
        for core in self.data.cores:
            for fn in core.functions:
                self._func_by_name.setdefault(fn.name, []).append((core.name, fn))
                for cp in fn.call_pairs:
                    self._callees.setdefault(cp.caller, set()).add(cp.callee)
                    self._callers.setdefault(cp.callee, set()).add(cp.caller)

    def core_names(self) -> list[str]:
        return [c.name for c in self.data.cores]

    def functions_for_core(self, core_name: str | None) -> list[tuple[str, FunctionRecord]]:
        result: list[tuple[str, FunctionRecord]] = []
        for core in self.data.cores:
            if core_name and core.name != core_name:
                continue
            for fn in core.functions:
                result.append((core.name, fn))
        return result

    def find_functions_by_name(
        self, name: str, core_name: str | None = None
    ) -> list[tuple[str, FunctionRecord]]:
        entries = self._func_by_name.get(name, [])
        if core_name:
            entries = [(c, f) for c, f in entries if c == core_name]
        return entries

    def callees_of(self, name: str) -> list[str]:
        return sorted(self._callees.get(name, set()))

    def callers_of(self, name: str) -> list[str]:
        return sorted(self._callers.get(name, set()))

    def to_load_summary(self) -> dict[str, Any]:
        total = sum(len(c.functions) for c in self.data.cores)
        return {
            "session_id": self.session_id,
            "label": self.label,
            "perf_path": self.perf_path,
            "version": self.data.version,
            "cores": self.core_names(),
            "function_count": total,
            "elf": self.elf_index.path if self.elf_index else None,
            "source": {
                "available": self.src_index is not None,
                "indexed_files": self.src_index.file_count if self.src_index else 0,
            },
        }
