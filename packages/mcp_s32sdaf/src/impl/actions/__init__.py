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

"""Canonical public manifest for S32SDAF action executables.

Each Volkano smart-card operation is authored as an ``ActionExecutable``
(contract + handler) and collected into the ``STATIC_ACTIONS`` tuple used to
build the active component action catalog exposed through the search-first
``search_actions`` / ``execute_action`` tools.
"""

from .volkano_actions import STATIC_ACTIONS

__all__ = ["STATIC_ACTIONS"]
