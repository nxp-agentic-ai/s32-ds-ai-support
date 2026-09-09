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

"""In-memory indexed model for a loaded .flatprofiler session.

A CoverageDataset wraps the raw FlatProfilerData produced by the loader and
adds fast lookup structures:
  - by core name
  - by file path (basename and full path)
  - by function name (exact and prefix)
  - by address range

The ELF index and source index are optional; the dataset is fully usable
without them for metric queries.  Source snippets require both the source
index and the source tree to be accessible on disk.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nxp.mcp.s32trace.impl.common.elf_index import ElfIndex
from nxp.mcp.s32trace.impl.common.source_index import SourceIndex
from nxp.mcp.s32trace.impl.common.source_snippet import SourceSnippet
from nxp.mcp.s32trace.impl.coverage.flatprofiler_loader import (
    FlatProfilerData,
    CoreSection,
    FileRecord,
    FunctionRecord,
    NO_SOURCE_INFO,
    load_flatprofiler,
)


@dataclass
class CoverageDataset:
    """Loaded and indexed coverage session.

    Attributes
    ----------
    session_id:
        Stable UUID string for the session.
    flatprofiler_path:
        Absolute path to the source .flatprofiler file.
    label:
        Human-friendly session name.
    data:
        Raw parsed data from the loader.
    elf_index:
        Optional ELF/DWARF index for the companion binary.
    src_index:
        Optional source-file index rooted at source_root.
    snippets:
        SourceSnippet reader (shared, stateless).
    snippet_window:
        Default context lines for source snippets.
    _func_by_name:
        Mapping function_name -> [(core_name, FileRecord, FunctionRecord), ...].
    _file_by_basename:
        Mapping basename_lower -> [(core_name, FileRecord), ...] (across all cores).
    """

    session_id: str
    flatprofiler_path: str
    label: str
    data: FlatProfilerData
    elf_index: ElfIndex | None
    src_index: SourceIndex | None
    snippets: SourceSnippet
    snippet_window: int = 5

    _func_by_name: dict[str, list[tuple[str, FileRecord, FunctionRecord]]] = field(
        default_factory=dict, init=False, repr=False
    )
    _file_by_basename: dict[str, list[tuple[str, FileRecord]]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self._build_indexes()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        session_id: str,
        flatprofiler_path: str,
        elf_path: str | None,
        source_root: str | None,
        extra_source_roots: list[str] | None = None,
        label: str | None = None,
        snippet_window: int = 5,
    ) -> "CoverageDataset":
        data = load_flatprofiler(flatprofiler_path)

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
            flatprofiler_path=str(flatprofiler_path),
            label=label or Path(flatprofiler_path).name,
            data=data,
            elf_index=elf_index,
            src_index=src_index,
            snippets=SourceSnippet(default_window=snippet_window),
            snippet_window=snippet_window,
        )

    # ------------------------------------------------------------------
    # Index builders
    # ------------------------------------------------------------------

    def _build_indexes(self) -> None:
        for core in self.data.cores:
            for fr in core.files:
                base = os.path.basename(fr.path).lower()
                self._file_by_basename.setdefault(base, []).append((core.name, fr))
                for func in fr.functions:
                    entry = (core.name, fr, func)
                    self._func_by_name.setdefault(func.name, []).append(entry)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def core_names(self) -> list[str]:
        return [c.name for c in self.data.cores]

    def files_for_core(self, core_name: str | None, include_no_source_info: bool = False) -> list[FileRecord]:
        results: list[FileRecord] = []
        for core in self.data.cores:
            if core_name and core.name != core_name:
                continue
            for fr in core.files:
                if not include_no_source_info and fr.is_no_source_info:
                    continue
                results.append(fr)
        return results

    def functions_for_core(self, core_name: str | None, include_no_source_info: bool = False) -> list[tuple[str, FileRecord, FunctionRecord]]:
        results: list[tuple[str, FileRecord, FunctionRecord]] = []
        for core in self.data.cores:
            if core_name and core.name != core_name:
                continue
            for fr in core.files:
                if not include_no_source_info and fr.is_no_source_info:
                    continue
                for func in fr.functions:
                    results.append((core.name, fr, func))
        return results

    def find_functions_by_name(
        self,
        name: str,
        core_name: str | None = None,
    ) -> list[tuple[str, FileRecord, FunctionRecord]]:
        """Find functions by exact name.  Inline duplicates (different addresses) are all returned."""
        entries = self._func_by_name.get(name, [])
        if core_name:
            entries = [(c, f, fn) for c, f, fn in entries if c == core_name]
        return entries

    def find_file_by_hint(self, hint: str, core_name: str | None = None) -> list[FileRecord]:
        """Resolve a path hint (full path or basename) to FileRecord(s)."""
        # Try full path match first.
        matches = []
        for core in self.data.cores:
            if core_name and core.name != core_name:
                continue
            for fr in core.files:
                if fr.path.lower() == hint.lower() or \
                   os.path.normcase(fr.path) == os.path.normcase(hint):
                    matches.append(fr)
        if matches:
            return matches
        # Basename fallback: index stores (core_name, FileRecord) tuples for O(n) filtering.
        base = os.path.basename(hint).lower()
        candidates = [
            fr for c_name, fr in self._file_by_basename.get(base, [])
            if core_name is None or c_name == core_name
        ]
        return candidates

    # ------------------------------------------------------------------
    # Load summary (returned by coverage.load action)
    # ------------------------------------------------------------------

    def to_load_summary(self) -> dict[str, Any]:
        total_funcs = sum(len(fr.functions) for fr in self.files_for_core(None))
        total_files = len(self.files_for_core(None))
        return {
            "session_id": self.session_id,
            "label": self.label,
            "flatprofiler_path": self.flatprofiler_path,
            "version": self.data.version,
            "cores": self.core_names(),
            "file_count": total_files,
            "function_count": total_funcs,
            "elf": self.elf_index.path if self.elf_index else None,
            "source": {
                "available": self.src_index is not None,
                "indexed_files": self.src_index.file_count if self.src_index else 0,
            },
        }
