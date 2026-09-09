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

"""Timeline analysis subsystem for mcp_s32trace.

Provides read-only analysis of S32DS Timeline view .timeline exports
combined with an optional ELF DWARF index and project source code.
"""

from .session_cache import TIMELINE_SESSION_CACHE
from .timeline_dataset import TimelineDataset
from .timeline_loader import load_timeline
from .queries import (
    query_timeline_summary,
    query_timeline_hotspots,
    query_timeline_function,
    query_timeline_source,
    query_timeline_window,
    query_timeline_call_sequence,
)

__all__ = [
    "TIMELINE_SESSION_CACHE",
    "TimelineDataset",
    "load_timeline",
    "query_timeline_summary",
    "query_timeline_hotspots",
    "query_timeline_function",
    "query_timeline_source",
    "query_timeline_window",
    "query_timeline_call_sequence",
]
