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

"""In-memory LRU session cache for TimelineDataset instances."""

from __future__ import annotations

import uuid
from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .timeline_dataset import TimelineDataset

_MAX_SESSIONS = 8


class TimelineSessionCache:
    """LRU-bounded cache of TimelineDataset instances keyed by session_id.

    At most ``max_sessions`` datasets are kept in memory.  When the limit is
    reached the least-recently-used entry is evicted before the new one is
    inserted.
    """

    def __init__(self, max_sessions: int = _MAX_SESSIONS) -> None:
        self._max = max_sessions
        self._store: "OrderedDict[str, TimelineDataset]" = OrderedDict()

    def new_id(self) -> str:
        return str(uuid.uuid4())

    def put(self, ds: "TimelineDataset") -> None:
        if ds.session_id in self._store:
            self._store.move_to_end(ds.session_id)
        else:
            if len(self._store) >= self._max:
                self._store.popitem(last=False)
        self._store[ds.session_id] = ds

    def get(self, session_id: str) -> "TimelineDataset":
        try:
            ds = self._store[session_id]
        except KeyError:
            raise KeyError(
                f"Timeline session '{session_id}' not found. Call timeline.load first."
            )
        self._store.move_to_end(session_id)
        return ds

    def remove(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def list_sessions(self) -> list[dict]:
        return [
            {
                "session_id": ds.session_id,
                "label": ds.label,
                "sources": ds.source_names,
                "function_count": ds.function_count,
            }
            for ds in self._store.values()
        ]


TIMELINE_SESSION_CACHE = TimelineSessionCache()
