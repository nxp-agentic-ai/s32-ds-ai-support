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

"""
Static ``start_tool`` handler for the S32DS MCP server.

Unlike live methods (``buildProject``, ``getProjectInfo``, ...) that require
the S32DS IDE and its RPC bridge to already be running, ``start_tool`` is
served entirely by the MCP server itself. This lets the agent bring the tool
up before issuing any live JSON-RPC calls.

Behaviour:
  * If the RPC bridge answers at ``host:port``, no-op and report
    ``status="already_running"``.
  * Otherwise, spawn the S32DS launcher detached, poll the RPC bridge until
    it answers or ``timeoutMs`` elapses, and report ``status="started"`` or
    ``status="failed"`` with the elapsed time and PID.

The handler and its OpenRPC-shaped parameter declaration are adapted into a
shared ``ActionExecutable`` in ``nxp.mcp.s32ds.actions.start_tool`` and merged
into the action catalog - see ``nxp.mcp.s32ds.actions.dynamic.build_action_catalog``.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request
from typing import Optional

from nxp.mcp.s32ds.metadata.server import MCP_SERVER_NAME

logger = logging.getLogger(MCP_SERVER_NAME)


_DEFAULT_TIMEOUT_MS = 60_000
_POLL_INTERVAL_S = 0.5

# Only these executable basenames are ever accepted as an S32DS launcher.
# This is what prevents a caller from pointing us at an arbitrary binary
# (e.g. "/etc/passwd", "..\\..\\bin\\evil.exe") via ``installationPath``
# or the ``S32DS_INSTALL_PATH`` environment variable.
_SAFE_LAUNCHER_NAMES = frozenset({"s32ds.exe", "s32ds"})


def _is_rpc_bridge_up(host: str, port: int, timeout_s: float = 1.0) -> bool:
	"""
	Return ``True`` if the S32DS RPC bridge answers ``rpc.discover`` at
	``host:port``. Any transport or JSON-RPC error is treated as "not up".
	"""
	url = f"http://{host}:{port}/rpc"
	body = json.dumps({
		"jsonrpc": "2.0",
		"method": "rpc.discover",
		"id": 0,
	}).encode("utf-8")
	req = urllib.request.Request(
		url, data=body, headers={"Content-Type": "application/json"}, method="POST",
	)
	try:
		with urllib.request.urlopen(req, timeout=timeout_s) as resp:
			resp.read()
		return True
	except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
		return False


def _resolve_launcher(installation_path: Optional[str]) -> Optional[str]:
	"""
	Best-effort *and* safety-checked resolution of the S32DS launcher.

	Order:
	  1. Explicit ``installation_path`` argument (folder containing
	     ``s32ds.exe`` / ``s32ds``, or a direct path to one of those files).
	  2. ``S32DS_INSTALL_PATH`` environment variable.
	  3. ``None`` - caller must fail with a clear error.

	Security:
	  * The input is canonicalised with ``pathlib.Path.resolve`` so any
	    ``..`` traversal is collapsed before we inspect the result.
	  * We refuse to execute anything whose basename is not in
	    :data:`_SAFE_LAUNCHER_NAMES` - a caller cannot coerce us into
	    spawning an arbitrary binary (e.g. ``/etc/passwd``, ``cmd.exe``,
	    ``malicious.exe``) by pointing ``installationPath`` at it.
	"""
	candidates: list[str] = []
	for candidate in (installation_path, os.environ.get("S32DS_INSTALL_PATH")):
		if not candidate:
			continue

		# Canonicalise first so any ``..`` segments are collapsed *before*
		# we look at the basename. ``strict=False`` lets us handle paths
		# whose final component may not yet exist (we check below).
		try:
			resolved = pathlib.Path(candidate).resolve(strict=False)
		except (ValueError, OSError) as e:
			logger.debug("start_tool: cannot resolve %r: %s", candidate, e)
			continue

		# Case A: caller pointed straight at a file. Accept it only if
		# its basename is a known S32DS launcher.
		if resolved.is_file():
			if resolved.name not in _SAFE_LAUNCHER_NAMES:
				logger.warning(
					"start_tool: refusing to execute non-launcher path %s "
					"(basename must be one of %s)",
					resolved, sorted(_SAFE_LAUNCHER_NAMES),
				)
				continue
			return str(resolved)

		# Case B: caller pointed at a folder. Look for a known launcher
		# name *inside* the resolved folder (joining after resolve keeps
		# us inside the intended directory).
		for name in _SAFE_LAUNCHER_NAMES:
			candidate_path = resolved / name
			candidates.append(str(candidate_path))
			if candidate_path.is_file():
				return str(candidate_path)
	if candidates:
		logger.debug("start_tool: none of the candidate launchers exist: %s", candidates)
	return None


def start_tool(
	*,
	installationPath: Optional[str] = None,
	timeoutMs: int = _DEFAULT_TIMEOUT_MS,
	host: str = "localhost",
	port: int = 8088,
) -> dict:
	"""
	Launch the S32DS IDE if its RPC bridge is not already answering.

	Args:
		installationPath: Optional override for the S32DS install directory or
			the launcher executable itself. When omitted, the handler falls
			back to the ``S32DS_INSTALL_PATH`` environment variable.
		timeoutMs: Maximum time to wait for the RPC bridge to come up after
			spawning the launcher. Defaults to 60 s.
		host: RPC bridge host to probe. Rarely changed.
		port: RPC bridge port to probe. Rarely changed.

	Returns:
		Dict with ``status`` in ``{"already_running", "started", "failed"}``,
		plus ``host``, ``port``, ``elapsedMs``, and (when applicable) ``pid``
		or ``error``.
	"""
	start = time.monotonic()

	# 1. Fast path - already up.
	if _is_rpc_bridge_up(host, port):
		return {
			"status": "already_running",
			"host": host,
			"port": port,
			"elapsedMs": int((time.monotonic() - start) * 1000),
		}

	# 2. Resolve the launcher.
	launcher = _resolve_launcher(installationPath)
	if launcher is None:
		return {
			"status": "failed",
			"host": host,
			"port": port,
			"elapsedMs": int((time.monotonic() - start) * 1000),
			"error": (
				"Could not locate the S32DS launcher. Pass 'installationPath' "
				"pointing at the S32DS install folder or the launcher executable, "
				"or set the S32DS_INSTALL_PATH environment variable."
			),
		}

	# 3. Spawn detached so the MCP server does not block on the IDE process.
	try:
		# On Windows we want the IDE fully detached from our console. On
		# POSIX, start_new_session gives us the same effect.
		popen_kwargs: dict = {"close_fds": True}
		if os.name == "nt":
			# CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
			popen_kwargs["creationflags"] = 0x00000200 | 0x00000008
		else:
			popen_kwargs["start_new_session"] = True
		proc = subprocess.Popen([launcher], **popen_kwargs)
	except OSError as e:
		return {
			"status": "failed",
			"host": host,
			"port": port,
			"launcher": launcher,
			"elapsedMs": int((time.monotonic() - start) * 1000),
			"error": f"Failed to spawn S32DS launcher: {e}",
		}

	# 4. Poll the RPC bridge until it answers or we time out.
	deadline = start + max(0, int(timeoutMs)) / 1000.0
	while time.monotonic() < deadline:
		if _is_rpc_bridge_up(host, port):
			return {
				"status": "started",
				"host": host,
				"port": port,
				"pid": proc.pid,
				"launcher": launcher,
				"elapsedMs": int((time.monotonic() - start) * 1000),
			}
		time.sleep(_POLL_INTERVAL_S)

	return {
		"status": "failed",
		"host": host,
		"port": port,
		"pid": proc.pid,
		"launcher": launcher,
		"elapsedMs": int((time.monotonic() - start) * 1000),
		"error": (
			f"S32DS launcher spawned (pid={proc.pid}) but its RPC bridge did not "
			f"start answering on {host}:{port} within {timeoutMs} ms."
		),
	}


# --- OpenRPC-shaped param declaration ---------------------------------------
#
# Same shape as items in a live method's ``params`` list. Consumed by the
# shared ``RpcClient._validate_params_from_list``.


START_TOOL_PARAMS: list[dict] = [
	{
		"name": "installationPath",
		"required": False,
		"schema": {
			"type": "string",
			"description": (
				"Optional S32DS install folder or launcher executable. Falls "
				"back to the S32DS_INSTALL_PATH environment variable."
			),
		},
		"summary": "S32DS install folder or launcher executable.",
	},
	{
		"name": "timeoutMs",
		"required": False,
		"schema": {
			"type": "integer",
			"minimum": 0,
			"description": (
				"Maximum time to wait for the RPC bridge to answer after "
				"spawning the launcher. Default 60000 ms."
			),
		},
		"summary": "Max wait for RPC bridge readiness, in milliseconds.",
	},
	{
		"name": "host",
		"required": False,
		"schema": {
			"type": "string",
			"description": "RPC bridge host to probe. Default 'localhost'.",
		},
		"summary": "RPC bridge host.",
	},
	{
		"name": "port",
		"required": False,
		"schema": {
			"type": "integer",
			"minimum": 1,
			"description": "RPC bridge port to probe. Default 8088.",
		},
		"summary": "RPC bridge port.",
	},
]
