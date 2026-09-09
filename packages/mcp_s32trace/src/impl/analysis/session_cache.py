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

"""In-process session cache keyed by trace_id.

Stores TraceDataset instances for the lifetime of the MCP server process.
Uses a plain dict protected by a lock.  No eviction is applied; typical
sessions involve at most a few loaded traces.
"""

from __future__ import annotations

import threading
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .trace_dataset import TraceDataset


class _TraceSessionCache:

    def __init__(self) -> None:
        self._store: dict[str, "TraceDataset"] = {}
        self._lock = threading.Lock()

    def new_id(self) -> str:
        return str(uuid.uuid4())

    def put(self, dataset: "TraceDataset") -> None:
        with self._lock:
            self._store[dataset.trace_id] = dataset

    def get(self, trace_id: str) -> "TraceDataset":
        with self._lock:
            ds = self._store.get(trace_id)
        if ds is None:
            raise KeyError(
                f"trace_id '{trace_id}' not found. "
                "Call analysis.load_trace first."
            )
        return ds

    def list_ids(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def remove(self, trace_id: str) -> bool:
        with self._lock:
            return self._store.pop(trace_id, None) is not None


TRACE_SESSION_CACHE = _TraceSessionCache()
