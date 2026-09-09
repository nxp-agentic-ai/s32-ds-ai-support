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
WebSocket JSON-RPC 2.0 client.

Provides :class:`WsJsonRpcClient`, a thin synchronous wrapper around a
persistent WebSocket connection. A background asyncio event loop (running in a
daemon thread) handles all async I/O so that MCP tools can issue JSON-RPC
requests synchronously via :meth:`WsJsonRpcClient.call` without interfering
with FastMCP's own event loop. Connection lifecycle is managed explicitly
through :meth:`connect`, :meth:`is_connected`, and :meth:`close`; higher-level
pooling of one client per endpoint is handled by the session manager.
"""
import asyncio
import json
import threading
import websockets


class WsJsonRpcClient:
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

    # -- lifecycle --------------------------------------------------------------

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

    # -- RPC -------------------------------------------------------------------

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