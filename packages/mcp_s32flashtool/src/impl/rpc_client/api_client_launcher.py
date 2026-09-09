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
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from nxp.mcp.s32flashtool.impl.constants import GUI_EXE_NAME
from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME


__all__ = ["ApiClientLauncher"]


logger = logging.getLogger(MCP_SERVER_NAME)


def _is_port_listening(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to ``host:port`` succeeds.

    Used to detect an S32FlashTool GUI instance that is already up and serving
    its local JSON-RPC API on ``port`` so the launcher can avoid spawning a
    duplicate process.
    """

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _hello_probe(host: str, port: int) -> bool:
    """Return True if a ``hello`` JSON-RPC call to ``host:port`` succeeds.

    Confirms that the process holding ``port`` is actually an S32FlashTool GUI
    serving its API, rather than an unrelated process that happens to occupy
    the same port. The probe never raises; any failure returns False.
    """

    try:
        from nxp.mcp.s32flashtool.impl.rpc_client.rpc_client import RpcClient

        client = RpcClient(port=port, host=host)
        client.call("hello")
        return True
    except Exception as exc:  # noqa: BLE001 - probe must never raise
        logger.warning(
            "Port %s:%d is in use but 'hello' probe failed: %s",
            host,
            port,
            exc,
        )
        return False


def _detect_x_display() -> str:
    """Return a usable DISPLAY value detected from live X server sockets.

    Inspects the X11 sockets under /tmp/.X11-unix (named X<n>) and returns the
    lowest display number that actually accepts a connection, formatted as
    ':<n>'. Returns an empty string when no socket is present. This avoids
    assuming ':0', which is wrong on remote-desktop or X11-forwarding
    sessions where the active display is typically ':10'.
    """

    socket_dir = Path("/tmp/.X11-unix")
    try:
        numbers = sorted(
            int(entry.name[1:])
            for entry in socket_dir.iterdir()
            if entry.name.startswith("X") and entry.name[1:].isdigit()
        )
    except OSError:
        return ""

    for number in numbers:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(str(socket_dir / f"X{number}"))
            sock.close()
            return f":{number}"
        except OSError:
            continue

    return f":{numbers[0]}" if numbers else ""


def _resolve_display_env() -> dict[str, str]:
    """Build a child environment with a usable X display for the GUI.

    On Windows and macOS the native windowing system is always used, so the
    parent environment is forwarded unchanged.

    On Linux/other, the Eclipse RCP GUI needs an X/Wayland display. The MCP
    server is spawned by VS Code as a stdio subprocess whose environment does
    not inherit ``DISPLAY``; launching the GUI in that state makes it die with
    "Cannot open display". To keep the GUI launchable in that context, when
    neither ``DISPLAY`` nor ``WAYLAND_DISPLAY`` is present we fall back to the
    conventional local display ``:0`` and, when available, point ``XAUTHORITY``
    at the invoking user's ``~/.Xauthority`` so the X server accepts the
    connection.
    """

    env = os.environ.copy()

    if sys.platform.startswith("win") or sys.platform == "darwin":
        return env

    display = env.get("DISPLAY", "").strip()
    wayland = env.get("WAYLAND_DISPLAY", "").strip()
    if display or wayland:
        return env

    # No display inherited (typical for a VS Code stdio subprocess). Detect the
    # X display that is actually running instead of assuming ':0', which fails
    # on remote-desktop / X11-forwarding setups (display ':10' and similar).
    env["DISPLAY"] = _detect_x_display() or ":0"

    if not env.get("XAUTHORITY", "").strip():
        xauth = Path.home() / ".Xauthority"
        if xauth.is_file():
            env["XAUTHORITY"] = str(xauth)

    logger.info(
        "No DISPLAY/WAYLAND_DISPLAY inherited; using DISPLAY=%s "
        "for the S32FlashTool GUI launch.",
        env["DISPLAY"],
    )
    return env


class ApiClientLauncher:

    """Launcher for the S32FlashTool GUI.

    Instances only remember the installation folder. The sole operation is
    :meth:`launch_gui`, which starts ``<folder>/GUI/s32ft[.exe]`` after probing
    for an already-running instance on the target host/port.
    """

    def __init__(self, s32flashtool_folder: str = "") -> None:
        self.s32flashtool_folder = s32flashtool_folder or ""

    def launch_gui(
        self,
        host: str = "localhost",
        port: Optional[int] = None,
    ) -> dict[str, Any]:
        """Launch the S32FlashTool GUI executable.

        When ``port`` is provided, first probe ``host:port`` for a GUI that is
        already listening; if one is found, do not spawn a duplicate and return
        an "already_running" result instead.

        Returns a result dict with ``status`` "ok" or "error".
        """

        # Probe for an already-running GUI before spawning a new process.
        if port is not None and port > 0 and _is_port_listening(host, port):
            # A process is holding the port. Send a "hello" JSON-RPC probe to
            # confirm it is actually an S32FlashTool GUI serving its API rather
            # than an unrelated process that happens to occupy the same port.
            if _hello_probe(host, port):

                logger.info(
                    "S32FlashTool GUI already listening on %s:%d; skipping launch.",
                    host,
                    port,
                )
                return {
                    "status": "ok",
                    "action": "gui_launch",
                    "launched": False,
                    "already_running": True,
                    "host": host,
                    "port": port,
                    "user_message": (
                        f"An S32FlashTool GUI application is already running and "
                        f"responding on {host}:{port}. Reusing it; no new "
                        f"instance was launched."
                    ),
                }

            return {
                "status": "error",
                "action": "gui_launch",
                "launched": False,
                "already_running": False,
                "host": host,
                "port": port,
                "error": (
                    f"Port {host}:{port} is already in use by a process that "
                    f"did not respond to the S32FlashTool 'hello' probe. "
                ),
            }

        raw_folder = self.s32flashtool_folder
        if not raw_folder or not str(raw_folder).strip():
            return {
                "status": "error",
                "action": "gui_launch",
                "launched": False,
                "error": "S32FlashTool folder is empty.",
            }

        # Resolve the folder and executable with strict=True so that any
        # symlinks along the path are actually followed before the containment
        # check runs. With strict=False, resolve() does not follow symlinks on
        # non-existent paths, so a crafted symlink at <base>/GUI/s32ft pointing
        # outside base could pass the relative_to() check. Resolving strictly
        # forces every component (including symlink targets) to exist and be
        # fully resolved, so the containment check sees the real target path.
        try:
            base = Path(raw_folder).resolve(strict=True)
            gui_dir = (base / "GUI").resolve(strict=True)
            exe = (gui_dir / GUI_EXE_NAME).resolve(strict=True)

            # Containment check: ensure the fully-resolved executable stays
            # under the resolved installation folder. Because every component
            # is symlink-resolved above, this catches symlink escapes.
            exe.relative_to(base)
        except (ValueError, OSError) as exc:
            return {
                "status": "error",
                "action": "gui_launch",
                "launched": False,
                "error": f"Invalid or unsafe S32FlashTool folder path: {exc}",
            }

        if not base.is_dir():
            return {
                "status": "error",
                "action": "gui_launch",
                "launched": False,
                "error": f"S32FlashTool folder not found: {self.s32flashtool_folder}",
            }

        if not exe.is_file():
            return {
                "status": "error",
                "action": "gui_launch",
                "launched": False,
                "error": f"GUI executable not found: {exe}",
            }

        # The Eclipse RCP GUI needs an X/Wayland display on Linux. The MCP
        # server is spawned by VS Code as a stdio subprocess whose environment
        # does not inherit DISPLAY, so without correction the GUI dies with
        # "Cannot open display". Resolve a usable display environment (falling
        # back to DISPLAY=:0 and ~/.Xauthority on POSIX) and forward it to the
        # child explicitly. On POSIX, start a new session so the GUI is fully
        # detached from the MCP server process group and survives independently.
        child_env = _resolve_display_env()
        logger.debug(child_env)
        popen_kwargs: dict[str, Any] = {
            "cwd": str(exe.parent),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "shell": False,
            "env": child_env,
        }
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True

        try:
            process = subprocess.Popen([str(exe)], **popen_kwargs)
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

        return {
                "status": "ok",
                "action": "gui_launch",
                "launched": True,
                "pid": process.pid,
                "exe": str(exe),
                "folder": str(base),
            }      
