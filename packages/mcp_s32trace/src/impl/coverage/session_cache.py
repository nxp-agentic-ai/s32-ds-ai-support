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

"""Coverage session store.

Keeps up to _MAX_SESSIONS loaded CoverageDataset objects in server memory so
that subsequent coverage.* calls can reuse the already-parsed dataset without
re-reading and re-indexing the .flatprofiler file on every request.  When the
limit is reached the least recently used session is dropped automatically.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict

from nxp.mcp.s32trace.impl.coverage.coverage_dataset import CoverageDataset

_MAX_SESSIONS = 8


class CoverageSessionCache:

    def __init__(self, max_sessions: int = _MAX_SESSIONS) -> None:
        self._max = max_sessions
        self._store: OrderedDict[str, CoverageDataset] = OrderedDict()

    def new_id(self) -> str:
        return str(uuid.uuid4())

    def put(self, ds: CoverageDataset) -> None:
        if ds.session_id in self._store:
            self._store.move_to_end(ds.session_id)
        else:
            if len(self._store) >= self._max:
                self._store.popitem(last=False)
            self._store[ds.session_id] = ds

    def get(self, session_id: str) -> CoverageDataset:
        if session_id not in self._store:
            raise KeyError(
                f"Coverage session '{session_id}' not found. "
                "Call coverage.load first."
            )
        self._store.move_to_end(session_id)
        return self._store[session_id]

    def __len__(self) -> int:
        return len(self._store)


COVERAGE_SESSION_CACHE = CoverageSessionCache()
