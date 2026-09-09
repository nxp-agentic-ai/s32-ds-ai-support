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

"""Code-coverage analysis subsystem for mcp_s32trace.

Provides read-only analysis of S32DS Flat Profiler .flatprofiler exports
combined with ELF DWARF debug info and project source code.
"""

from .session_cache import COVERAGE_SESSION_CACHE
from .coverage_dataset import CoverageDataset
from .flatprofiler_loader import load_flatprofiler
from .queries import (
    query_coverage_summary,
    query_coverage_function,
    query_coverage_file,
    query_coverage_uncovered,
    query_coverage_hotspots,
    query_coverage_get_source,
)

__all__ = [
    "COVERAGE_SESSION_CACHE",
    "CoverageDataset",
    "load_flatprofiler",
    "query_coverage_summary",
    "query_coverage_function",
    "query_coverage_file",
    "query_coverage_uncovered",
    "query_coverage_hotspots",
    "query_coverage_get_source",
]
