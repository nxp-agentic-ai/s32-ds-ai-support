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

"""Minimal launcher for the S32FlashTool GUI (Eclipse RCP).

The single responsibility of this module is to start the S32FlashTool GUI
executable from a given installation folder. All other GUI interaction (model
get/set, flash operations, connectivity probes) is handled elsewhere through
the JSON-RPC transport; this client does nothing but launch the process.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME

logger = logging.getLogger(MCP_SERVER_NAME)


class RestClient:

    """Launcher for the S32FlashTool GUI.

    Instances only remember the installation folder. The sole operation is
    :meth:`launch_gui`, which starts ``<folder>/GUI/s32ft.exe``.
    """

    def __init__(self, s32flashtool_folder: str = "") -> None:
        self.s32flashtool_folder = s32flashtool_folder or ""

    def launch_gui(self) -> Dict[str, Any]:
        """Launch the S32FlashTool GUI executable.

        Returns a result dict with ``status`` "ok" or "error".
        """

        base = Path(self.s32flashtool_folder)
        exe = base / "GUI" / "s32ft.exe"

        if not base.exists() or not base.is_dir():
            return {
                "status": "error",
                "action": "gui_launch",
                "launched": False,
                "error": f"S32FlashTool folder not found: {self.s32flashtool_folder}",
            }

        if not exe.exists() or not exe.is_file():
            return {
                "status": "error",
                "action": "gui_launch",
                "launched": False,
                "error": f"GUI executable not found: {exe}",
            }

        try:
            process = subprocess.Popen(
                [str(exe)],
                cwd=str(exe.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
            return {
                "status": "ok",
                "action": "gui_launch",
                "launched": True,
                "pid": process.pid,
                "exe": str(exe),
                "folder": str(base),
            }
        except Exception as exc:
            logger.exception("Failed to launch S32FlashTool GUI")
            return {
                "status": "error",
                "action": "gui_launch",
                "launched": False,
                "exe": str(exe),
                "folder": str(base),
                "error": str(exc),
            }
