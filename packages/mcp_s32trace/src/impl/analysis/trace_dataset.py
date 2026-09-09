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

"""TraceDataset: central container for one loaded trace session.

Holds the parsed CSV data, the ELF/DWARF index, an optional source-file
index, and the SourceSnippet reader.  Created by ``TraceDataset.load()``
and stored in ``TRACE_SESSION_CACHE`` keyed by ``trace_id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .csv_loader import load_trace_csv
from .elf_index import ElfIndex
from .source_index import SourceIndex
from .source_snippet import SourceSnippet


@dataclass
class TraceDataset:
    """One loaded trace session."""

    trace_id: str
    csv_path: str
    elf_path: str
    source_root: str | None
    extra_source_roots: list[str]
    label: str | None
    time_unit_ns: float | None
    snippet_window: int

    parent_df: pd.DataFrame = field(repr=False)
    details: list[list[dict[str, Any]]] = field(repr=False)
    elf: ElfIndex = field(repr=False)
    src: SourceIndex | None = field(repr=False, default=None)
    snippets: SourceSnippet = field(repr=False, default_factory=SourceSnippet)

    # Computed in __post_init__
    row_count: int = 0
    total_detail_count: int = 0
    cores: list[str] = field(default_factory=list)
    time_range_raw: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        self.row_count = len(self.parent_df)
        self.total_detail_count = sum(len(d) for d in self.details)
        if "core" in self.parent_df.columns:
            self.cores = sorted(self.parent_df["core"].dropna().unique().tolist())
        if "timestamp_int" in self.parent_df.columns:
            valid = self.parent_df["timestamp_int"].dropna()
            if not valid.empty:
                self.time_range_raw = (int(valid.min()), int(valid.max()))

    @classmethod
    def load(
        cls,
        *,
        trace_id: str,
        csv_path: str | Path,
        elf_path: str | Path,
        source_root: str | Path | None = None,
        extra_source_roots: list[str | Path] | None = None,
        label: str | None = None,
        time_unit_ns: float | None = None,
        snippet_window: int = 3,
    ) -> "TraceDataset":
        """Load and index a complete trace session from a CSV + ELF pair.

        Parameters
        ----------
        trace_id:
            Unique session identifier (caller-provided).
        csv_path:
            Path to the decoded Trace-view CSV.
        elf_path:
            Path to the ELF binary with DWARF debug info.
        source_root:
            Root of the user's project source tree (optional).
        extra_source_roots:
            Additional roots such as an SDK or shared library directory.
        label:
            Optional human-friendly session label shown in summaries.
        time_unit_ns:
            Multiplier to convert raw timestamp values to nanoseconds.
            Example: 1.0 if already in ns, 1000.0 if in us, etc.
        snippet_window:
            Default context lines above/below a matched source line.
        """
        parent_df, details = load_trace_csv(csv_path)
        elf_index = ElfIndex.from_file(elf_path)

        roots: list[str] = []
        if source_root:
            roots.append(str(source_root))
        for r in (extra_source_roots or []):
            roots.append(str(r))

        src_index: SourceIndex | None = SourceIndex.from_roots(roots) if roots else None

        return cls(
            trace_id=trace_id,
            csv_path=str(csv_path),
            elf_path=str(elf_path),
            source_root=str(source_root) if source_root else None,
            extra_source_roots=[str(r) for r in (extra_source_roots or [])],
            label=label,
            time_unit_ns=time_unit_ns,
            snippet_window=snippet_window,
            parent_df=parent_df,
            details=details,
            elf=elf_index,
            src=src_index,
            snippets=SourceSnippet(default_window=snippet_window),
        )

    def to_load_summary(self) -> dict[str, Any]:
        """Return a JSON-serializable summary for the load_trace response."""
        src_summary: dict[str, Any] = {"available": self.src is not None}
        if self.src is not None:
            src_summary["roots"] = self.src.roots
            src_summary["indexed_files"] = self.src.file_count

        return {
            "trace_id": self.trace_id,
            "label": self.label,
            "csv_path": self.csv_path,
            "elf_path": self.elf_path,
            "elf_arch": self.elf.arch,
            "parent_event_count": self.row_count,
            "total_detail_count": self.total_detail_count,
            "cores": self.cores,
            "time_range_raw": list(self.time_range_raw) if self.time_range_raw else None,
            "time_unit_ns": self.time_unit_ns,
            "source": src_summary,
            "snippet_window": self.snippet_window,
        }
