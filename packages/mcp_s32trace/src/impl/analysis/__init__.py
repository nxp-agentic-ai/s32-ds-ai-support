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

"""Trace analysis subsystem for mcp_s32trace.

Provides read-only analysis of S32Trace decoded CSV exports combined with
ELF DWARF debug info and optional project source code.
"""

from .session_cache import TRACE_SESSION_CACHE
from .trace_dataset import TraceDataset
from .csv_loader import load_trace_csv
from .elf_index import ElfIndex
from .source_index import SourceIndex
from .source_snippet import SourceSnippet
from .queries import (
    query_summary,
    query_find_event,
    query_address_at,
    query_time_between,
    query_range_events,
    query_get_source,
)

__all__ = [
    "TRACE_SESSION_CACHE",
    "TraceDataset",
    "load_trace_csv",
    "ElfIndex",
    "SourceIndex",
    "SourceSnippet",
    "query_summary",
    "query_find_event",
    "query_address_at",
    "query_time_between",
    "query_range_events",
    "query_get_source",
]
