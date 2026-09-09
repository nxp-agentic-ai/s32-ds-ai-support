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

import asyncio
import json
import threading
from typing import Any

from fastmcp import FastMCP
import websockets

from ..config.models import FreeMASTERMcpServerConfig

# ── WebSocket JSON-RPC client ─────────────────────────────────────────────────

class _WsJsonRpcClient:
    """
    Thin synchronous wrapper around a persistent WebSocket connection.

    A background asyncio event loop (running in a daemon thread) handles all
    async I/O so that MCP tools can call .call() synchronously without
    interfering with FastMCP's own event loop.
    """

    def __init__(self, host: str, port: int) -> None:
        self.uri = f"ws://{host}:{port}"
        self._ws = None
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, daemon=True, name="freemaster-ws-loop"
        )
        self._thread.start()
        self._id_lock = threading.Lock()
        self._next_id: int = 0

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def connect(self, timeout: float = 10.0) -> None:
        """Open the WebSocket connection (blocking, raises on failure)."""
        future = asyncio.run_coroutine_threadsafe(self._open(), self._loop)
        future.result(timeout=timeout)

    async def _open(self) -> None:
        self._ws = await websockets.connect(self.uri)

    def is_connected(self) -> bool:
        """Return True if the WebSocket connection is currently open."""
        import websockets.connection
        return (
            self._ws is not None
            and self._ws.state == websockets.connection.State.OPEN
        )

    def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        if self._ws is not None:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
            self._ws = None

    # ── RPC ───────────────────────────────────────────────────────────────────

    def call(self, method: str, params: dict, timeout: float = 10.0) -> dict:
        """Send a JSON-RPC 2.0 request and return the full response dict."""
        with self._id_lock:
            self._next_id += 1
            rpc_id = self._next_id

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": rpc_id,
        }
        if params:
            payload["params"] = params
        future = asyncio.run_coroutine_threadsafe(self._send(payload), self._loop)
        return future.result(timeout=timeout)

    async def _send(self, payload: dict) -> dict:
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected.")
        await self._ws.send(json.dumps(payload))
        raw = await self._ws.recv()
        return json.loads(raw)


# ── module-level client state ─────────────────────────────────────────────────

_ws_client: _WsJsonRpcClient | None = None

# ── tool registration ─────────────────────────────────────────────────────────

def register_freemaster_client_tools(mcp: FastMCP, cfg: FreeMASTERMcpServerConfig) -> None:

    # ── WebSocket tools ───────────────────────────────────────────────────────

    @mcp.tool(name="connect")
    def freemaster_connect(
        host: str = cfg.settings.ws_host,
        port: int = cfg.settings.ws_port,
    ) -> str:
        """
        Initialize (or re-initialize) the FreeMASTER JSON-RPC WebSocket client.

        host and port default to the values from the server configuration file
        (ws_host / ws_port under settings). Call this tool before using
        freemaster_call(). It is safe to call again to reconnect or change target.

        Returns a JSON object with "status" and "uri".
        """
        global _ws_client

        requested_uri = f"ws://{host}:{port}"

        # Reuse existing connection if same target and still alive
        if _ws_client is not None and _ws_client.uri == requested_uri and _ws_client.is_connected():
            return json.dumps({"status": "already_connected", "uri": _ws_client.uri})

        # Close stale or different connection
        if _ws_client is not None:
            try:
                _ws_client.close()
            except Exception:
                pass
            _ws_client = None

        client = _WsJsonRpcClient(host, port)
        try:
            client.connect(timeout=10.0)
            _ws_client = client
            return json.dumps({"status": "connected", "uri": client.uri})
        except Exception as exc:
            return json.dumps({"status": "error", "detail": str(exc)})

    @mcp.tool(name="api_call")
    def freemaster_api_call(method: str, params: dict[str, Any] | list[Any] | None = None) -> str:
        """
        Send a JSON-RPC request to FreeMASTER over the active WebSocket connection
        and return the server reply.

        method: JSON-RPC method name, e.g. "FreeMASTER.ReadVariable"
        params: dict of method parameters, e.g. {"name": "myVar"}.
                Omit or pass {} for methods that take no parameters.

        Returns the full JSON-RPC response object (contains "result" on success
        or "error" on failure). Requires freemaster_connect() to have been called
        first.
        """
        if _ws_client is None:
            return json.dumps(
                {"error": "Not connected. Call freemaster_connect() first."}
            )
        try:
            response = _ws_client.call(method, params)
            return json.dumps(response)
        except Exception as exc:
            return json.dumps({"error": str(exc)})
