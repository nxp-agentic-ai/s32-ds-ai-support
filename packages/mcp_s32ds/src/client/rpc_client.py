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
S32DS-specific JSON-RPC 2.0 client.

Thin subclass of :class:`nxp.mcp.shared.rpc.RpcClient` that adds the two
S32DS-specific behaviours:

	* The client logs through the S32DS MCP server logger so its startup
    ``rpc.discover`` message is grouped with the rest of the S32DS log
    stream and honours the level/handlers configured for that component.
  * The ``waitForJob`` method is held open by the server until the job ends
    or ``timeoutMs`` elapses; the socket timeout is extended accordingly.

The generic transport, discovery cache, parameter validation, and error
types live in ``nxp.mcp.shared.rpc``. See that module for the full API.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from nxp.mcp.shared.rpc import RpcClient as _SharedRpcClient
from nxp.mcp.shared.rpc import RpcError

from nxp.mcp.s32ds.metadata.server import MCP_SERVER_NAME

__all__ = ["RpcClient", "RpcError"]


class RpcClient(_SharedRpcClient):
	"""JSON-RPC client tailored to the S32DS embedded plugin."""

	def __init__(
		self,
		port: int = 8088,
		host: str = "localhost",
		timeout: int = 30,
	):
		super().__init__(
			port=port,
			host=host,
			timeout=timeout,
			path="/rpc",
			logger=logging.getLogger(MCP_SERVER_NAME),
		)

	def _effective_timeout(self, method: str, params: dict) -> int:
		# `waitForJob` is held open by the server until the job ends or
		# ``timeoutMs`` elapses; extend the socket timeout to outlast the
		# server-side wait.
		if method == "waitForJob":
			timeout_ms = params.get("timeoutMs") or 30000
			try:
				return max(self._timeout, int(timeout_ms) // 1000 + 5)
			except (TypeError, ValueError):
				return self._timeout
		return self._timeout
