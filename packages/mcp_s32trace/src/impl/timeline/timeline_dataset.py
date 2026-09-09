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

"""TimelineDataset: central container for one loaded timeline session."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .timeline_loader import load_timeline, TimelineData, TimelineSource, FunctionEntry
from ..common.elf_index import ElfIndex
from ..common.source_index import SourceIndex
from ..common.source_snippet import SourceSnippet


@dataclass
class TimelineDataset:
    """One loaded timeline session."""

    session_id: str
    timeline_path: str
    elf_path: str | None
    source_root: str | None
    extra_source_roots: list[str]
    label: str | None
    snippet_window: int

    data: TimelineData = field(repr=False)
    elf: ElfIndex | None = field(repr=False, default=None)
    src: SourceIndex | None = field(repr=False, default=None)
    snippets: SourceSnippet = field(repr=False, default_factory=SourceSnippet)

    # Computed after loading
    source_names: list[str] = field(default_factory=list)
    function_count: int = 0
    row_count: int = 0
    timestamp_range: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        self.source_names = self.data.source_names or [
            s.name for s in self.data.sources
        ]
        self.function_count = sum(len(s.functions) for s in self.data.sources)
        all_rows = [r for s in self.data.sources for r in s.rows]
        self.row_count = len(all_rows)
        timestamps = [r.timestamp for r in all_rows if r.timestamp > 0]
        if timestamps:
            self.timestamp_range = (min(timestamps), max(timestamps))

    @classmethod
    def load(
        cls,
        *,
        session_id: str,
        timeline_path: str | Path,
        elf_path: str | Path | None = None,
        source_root: str | Path | None = None,
        extra_source_roots: list[str | Path] | None = None,
        label: str | None = None,
        snippet_window: int = 5,
    ) -> "TimelineDataset":
        data = load_timeline(timeline_path)

        elf: ElfIndex | None = None
        if elf_path:
            elf = ElfIndex.from_file(elf_path)

        roots: list[str] = []
        if source_root:
            roots.append(str(source_root))
        for r in (extra_source_roots or []):
            roots.append(str(r))
        src: SourceIndex | None = SourceIndex.from_roots(roots) if roots else None

        return cls(
            session_id=session_id,
            timeline_path=str(timeline_path),
            elf_path=str(elf_path) if elf_path else None,
            source_root=str(source_root) if source_root else None,
            extra_source_roots=[str(r) for r in (extra_source_roots or [])],
            label=label,
            snippet_window=snippet_window,
            data=data,
            elf=elf,
            src=src,
            snippets=SourceSnippet(default_window=snippet_window),
        )

    def to_load_summary(self) -> dict[str, Any]:
        src_summary: dict[str, Any] = {"available": self.src is not None}
        if self.src is not None:
            src_summary["roots"] = self.src.roots
            src_summary["indexed_files"] = self.src.file_count

        return {
            "session_id": self.session_id,
            "label": self.label,
            "timeline_path": self.timeline_path,
            "elf_path": self.elf_path,
            "elf_arch": self.elf.arch if self.elf else None,
            "version": self.data.version,
            "sources": self.source_names,
            "function_count": self.function_count,
            "data_row_count": self.row_count,
            "timestamp_range": list(self.timestamp_range) if self.timestamp_range else None,
            "source": src_summary,
            "snippet_window": self.snippet_window,
        }

    # ------------------------------------------------------------------
    # Address-to-function lookup
    # ------------------------------------------------------------------

    def resolve_function(self, address: int, source_name: str | None = None) -> FunctionEntry | None:
        """Return the FunctionEntry whose range contains *address*, or None."""
        sources = self._filter_sources(source_name)
        for src in sources:
            for fn in src.functions:
                if fn.address <= address < fn.address + max(fn.size, 1):
                    return fn
        return None

    def _filter_sources(self, source_name: str | None) -> list[TimelineSource]:
        if source_name is None:
            return self.data.sources
        return [s for s in self.data.sources if s.name == source_name]
