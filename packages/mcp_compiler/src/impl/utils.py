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

# utils.py
# ----------------------------
# Generic utilities — no toolchain-specific imports
# ----------------------------

import time
from pathlib import Path


# ----------------------------
# Path Utilities
# ----------------------------

def create_timestamped_dir(base_dir: Path, prefix: str) -> Path:
    """
    Create directory with timestamp suffix.

    Args:
        base_dir: Parent directory
        prefix: Directory name prefix (e.g., "compile", "sim")

    Returns:
        Created directory path
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    work_dir = base_dir / f"{prefix}_{timestamp}"
    work_dir.mkdir(exist_ok=True)
    return work_dir
