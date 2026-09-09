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

"""Source file index that resolves DWARF build-machine paths to local paths.

Resolution order for a DWARF path (e.g. 'C:/jenkins/ws/foo/src/drv.c'):
  1. DWARF path as-is (works when user built locally).
  2. Prefix remap - walk up the DWARF path and try successive tails under
     each source_root.  Example: try 'src/drv.c', then 'foo/src/drv.c'.
  3. Basename fallback - look up 'drv.c' in the basename index.  If exactly
     one match, return it.  If multiple, return all candidates.
  4. Miss - return resolved=False with the raw DWARF path.

Only files under the registered source roots are accessible through this
index (security boundary).
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# Extensions considered "source code" for snippet retrieval.
_SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {".c", ".h", ".cpp", ".cxx", ".cc", ".hpp", ".hh", ".s", ".S", ".asm"}
)


@dataclass
class ResolvedPath:
    resolved: bool
    local_path: str | None       # absolute local path, or None on miss
    candidates: list[str]        # non-empty only when multiple matches found
    dwarf_path: str              # original DWARF path (always present)


@dataclass
class SourceIndex:
    """Basename-keyed index of all source files under one or more roots.

    Parameters
    ----------
    roots:
        Absolute paths to the roots to index.  Safe boundary for all reads.
    extensions:
        Set of file extensions (with leading dot) to index.  Files with
        other extensions are ignored.
    """

    roots: list[str] = field(default_factory=list)
    extensions: frozenset[str] = _SOURCE_EXTENSIONS

    # basename_lower -> [absolute_path, ...]
    _basename_index: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list), init=False, repr=False)
    # canonical set of all indexed absolute paths (lowercased for cross-platform)
    _all_paths_lower: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        for root in self.roots:
            self._index_root(root)

    @classmethod
    def from_roots(
        cls,
        roots: list[str | Path],
        extensions: frozenset[str] | None = None,
    ) -> "SourceIndex":
        kw: dict = {"roots": [str(r) for r in roots]}
        if extensions is not None:
            kw["extensions"] = extensions
        return cls(**kw)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, dwarf_path: str) -> ResolvedPath:
        """Resolve a DWARF file path to a local absolute path."""
        if not dwarf_path:
            return ResolvedPath(resolved=False, local_path=None, candidates=[], dwarf_path=dwarf_path)

        # Step 1 - DWARF path as-is.
        if self._is_accessible(dwarf_path):
            return ResolvedPath(resolved=True, local_path=str(Path(dwarf_path)), candidates=[], dwarf_path=dwarf_path)

        # Step 2 - Prefix remap: walk up DWARF path tails.
        parts = Path(dwarf_path).parts
        for tail_start in range(1, len(parts)):
            tail = os.path.join(*parts[tail_start:])
            for root in self.roots:
                candidate = os.path.normpath(os.path.join(root, tail))
                if self._is_accessible(candidate):
                    return ResolvedPath(resolved=True, local_path=candidate, candidates=[], dwarf_path=dwarf_path)

        # Step 3 - Basename fallback.
        base = os.path.basename(dwarf_path).lower()
        matches = self._basename_index.get(base, [])
        if len(matches) == 1:
            return ResolvedPath(resolved=True, local_path=matches[0], candidates=[], dwarf_path=dwarf_path)
        if len(matches) > 1:
            return ResolvedPath(resolved=False, local_path=None, candidates=list(matches), dwarf_path=dwarf_path)

        # Step 4 - Miss.
        return ResolvedPath(resolved=False, local_path=None, candidates=[], dwarf_path=dwarf_path)

    def is_safe_path(self, path: str) -> bool:
        """Return True if ``path`` is under one of the registered roots."""
        canon = os.path.normcase(os.path.realpath(path))
        for root in self.roots:
            root_canon = os.path.normcase(os.path.realpath(root))
            if canon.startswith(root_canon + os.sep) or canon == root_canon:
                return True
        return False

    @property
    def file_count(self) -> int:
        return len(self._all_paths_lower)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _index_root(self, root: str) -> None:
        root_path = Path(root)
        if not root_path.is_dir():
            return
        for dirpath, _dirs, filenames in os.walk(root_path):
            for fname in filenames:
                ext = os.path.splitext(fname)[1]
                if ext not in self.extensions:
                    continue
                abs_path = os.path.normpath(os.path.join(dirpath, fname))
                self._basename_index[fname.lower()].append(abs_path)
                self._all_paths_lower.add(abs_path.lower())

    def _is_accessible(self, path: str) -> bool:
        """Return True only if the path exists AND is under a registered root."""
        if not os.path.isfile(path):
            return False
        return self.is_safe_path(path)
