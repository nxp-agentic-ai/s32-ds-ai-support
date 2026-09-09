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

"""Shared, dependency-free constants for the S32FlashTool MCP implementation.

This module holds low-level constants (such as the platform-appropriate
executable names) so that utility, client and builder modules can share them
without importing each other. Keeping these values here avoids cross-module
coupling and the circular-import risk that arises when a utility module imports
from a client implementation module purely to reach a constant.
"""

from __future__ import annotations

import os

# On Windows the executables carry a ".exe" suffix; on other platforms they do
# not. Evaluated once at import time.
_EXE_SUFFIX = ".exe" if os.name == "nt" else ""

# Command-line interface executable (``.../bin/S32FlashTool[.exe]``).
CLI_EXE_NAME = f"S32FlashTool{_EXE_SUFFIX}"

# GUI (Eclipse RCP) executable (``.../GUI/s32ft[.exe]``).
GUI_EXE_NAME = f"s32ft{_EXE_SUFFIX}"

__all__ = ["CLI_EXE_NAME", "GUI_EXE_NAME"]
