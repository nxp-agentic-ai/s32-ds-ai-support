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

"""Public search entry points for the shared action package.

Only the generic search API is exported here. BM25, regex, and text helpers
remain internal implementation details behind ``search_actions``.
"""

from .search import search_actions

__all__ = [
    "search_actions",
]
