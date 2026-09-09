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

"""Windowed source-file snippet reader with safety guardrails.

Returns a context window around a target line:
  {
    file:        absolute path,
    target_line: 1-based line number,
    window_start: 1-based line number of first line returned,
    window_end:   1-based line number of last line returned,
    lines: [
      {"n": <1-based>, "text": "<content>", "is_target": <bool>},
      ...
    ]
  }

Guardrails:
  - window parameter is capped at HARD_MAX_WINDOW (50 lines each side).
  - files are only read when callers have already verified the path via
    SourceIndex.is_safe_path(); SourceSnippet itself does not re-check.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_WINDOW = 3
HARD_MAX_WINDOW = 50


@dataclass
class SourceSnippet:
    """Read a windowed snippet from a source file.

    Parameters
    ----------
    default_window:
        Default number of context lines to include above and below the
        target line.
    """

    default_window: int = DEFAULT_WINDOW

    def read(
        self,
        file_path: str,
        target_line: int,
        window: int | None = None,
    ) -> dict[str, Any] | None:
        """Return a snippet dict, or None if the file cannot be read.

        Parameters
        ----------
        file_path:
            Absolute path to the source file.
        target_line:
            1-based line number to center the window on.
        window:
            Number of context lines above and below ``target_line``.
            Defaults to ``self.default_window``; capped at HARD_MAX_WINDOW.
        """
        w = min(window if window is not None else self.default_window, HARD_MAX_WINDOW)
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        all_lines = content.splitlines()
        total = len(all_lines)

        start = max(1, target_line - w)
        end = min(total, target_line + w)

        result_lines = []
        for ln in range(start, end + 1):
            result_lines.append(
                {
                    "n": ln,
                    "text": all_lines[ln - 1],
                    "is_target": ln == target_line,
                }
            )

        return {
            "file": str(path),
            "target_line": target_line,
            "window_start": start,
            "window_end": end,
            "lines": result_lines,
        }
