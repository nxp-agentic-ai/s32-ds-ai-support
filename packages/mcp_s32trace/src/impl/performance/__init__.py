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

"""Performance analysis subsystem for mcp_s32trace.

Provides read-only analysis of S32DS Performance View .perf exports
combined with optional ELF DWARF debug info and project source code.
"""

from .session_cache import PERFORMANCE_SESSION_CACHE
from .performance_dataset import PerformanceDataset
from .perf_loader import load_perf
from .queries import (
    query_performance_summary,
    query_performance_hotspots,
    query_performance_function,
    query_performance_callgraph,
    query_performance_get_source,
)

__all__ = [
    "PERFORMANCE_SESSION_CACHE",
    "PerformanceDataset",
    "load_perf",
    "query_performance_summary",
    "query_performance_hotspots",
    "query_performance_function",
    "query_performance_callgraph",
    "query_performance_get_source",
]
