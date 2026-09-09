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
Session manager for WebSocket JSON-RPC clients.

Keeps a registry of :class:`WsJsonRpcClient` instances, one live client per
(host, port) endpoint, each addressable by a stable, opaque ``fm-<hex>`` session
id derived deterministically from the endpoint so the same endpoint always yields
the same id and the id doubles as the registry key. MCP tools obtain a connection
via :meth:`WsSessionManager.get_client` (which reuses, transparently reconnects,
or creates the client) and resolve one from a session id, or the single active
session, via :meth:`WsSessionManager.resolve`. The manager is thread-safe.
"""

import hashlib
import logging
import threading
from typing import Optional

from nxp.mcp.freemaster.config import FreeMASTERMcpServerConfig

from .client import WsJsonRpcClient

# Session id prefix and hash width (hex chars) for endpoint-derived ids.
_SID_PREFIX = "fm-"
_SID_HEX_WIDTH = 8


class WsSessionManager:
    """
    Registry of WebSocket JSON-RPC clients, one per (host, port) endpoint,
    addressable by a stable opaque ``fm-`` session id derived from the endpoint.

    Thread-safe: all registry mutations are guarded by a re-entrant lock,
    consistent with the background-loop threading model of WsJsonRpcClient.
    """

    def __init__(self, server_cfg: FreeMASTERMcpServerConfig, logger_override: Optional[logging.Logger] = None) -> None:
        self.server_cfg: FreeMASTERMcpServerConfig = server_cfg
        self._logger = logger_override or logging.getLogger(__name__)
        self._lock = threading.RLock()
        # One live client per endpoint, keyed by the derived session id.
        self._clients: dict[str, WsJsonRpcClient] = {}

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _key(host: str, port: int) -> str:
        """
        Return the stable ``fm-`` session id for an endpoint.

        The id is a deterministic function of ``host:port`` (a truncated SHA-256
        digest), so the same endpoint always resolves to the same id. This makes
        the id reproducible and lets it double as the registry key, avoiding any
        endpoint <-> id bookkeeping.
        """
        endpoint = f"{host}:{int(port)}"
        digest = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
        return f"{_SID_PREFIX}{digest[:_SID_HEX_WIDTH]}"

    def _prune_if_dead(self, session_id: str) -> None:
        """Evict a cached client for session id if its connection is no longer open."""
        client = self._clients.get(session_id)
        if client is None:
            return
        if not client.is_connected():
            self._logger.info(
                "Pruning closed WebSocket client for %s", client.uri
            )
            try:
                client.close()
            except Exception:
                pass
            self._clients.pop(session_id, None)

    # -- public API ------------------------------------------------------------

    def get_client(
        self,
        host: str,
        port: int,
        timeout: float = 10.0,
    ) -> tuple[str, WsJsonRpcClient]:
        """
        Return ``(session_id, client)`` for the given endpoint.

        Reuses an existing live client for (host, port). If a cached client's
        connection was closed by the server, it is evicted and a fresh client
        is created and connected. If no client exists yet, one is created and
        connected. The endpoint's stable ``fm-`` session id is the same on
        every call for the same endpoint.

        Raises:
          ConnectionError: the endpoint could not be connected. The registry
                           is left unchanged (no half-open client is stored).
        """
        session_id = self._key(host, port)
        with self._lock:
            # Drop a stale/closed client so we reopen the connection below.
            self._prune_if_dead(session_id)

            existing = self._clients.get(session_id)
            if existing is not None and existing.is_connected():
                return session_id, existing

            client = WsJsonRpcClient(host, int(port))
            try:
                client.connect(timeout=timeout)
            except Exception as exc:
                # Do not store a client that failed to connect; make sure any
                # partially-opened resources are released.
                try:
                    client.close()
                except Exception:
                    pass
                self._logger.error(
                    "Failed to connect WebSocket client to %s: %s",
                    client.uri, exc,
                )
                raise ConnectionError(
                    f"Could not connect to JSON-RPC endpoint {client.uri}: {exc}"
                ) from exc

            self._clients[session_id] = client
            self._logger.info(
                "Opened WebSocket client for %s (session %s)", client.uri, session_id
            )
            return session_id, client

    def resolve(self, session_id: Optional[str] = None) -> WsJsonRpcClient:
        """
        Resolve a live client from a session id, with a single-session fallback.

        - If ``session_id`` is given, the matching client is returned. Raises
          KeyError if the id is unknown or its connection is closed.
        - If ``session_id`` is ``None`` and exactly one live session exists,
          that client is returned.
        - If ``session_id`` is ``None`` and there are zero or multiple live
          sessions, a KeyError is raised describing the ambiguity.
        """
        with self._lock:
            if session_id is not None:
                if session_id not in self._clients:
                    raise KeyError(f"Unknown session id: {session_id!r}")
                self._prune_if_dead(session_id)
                client = self._clients.get(session_id)
                if client is None:
                    raise KeyError(
                        f"Session {session_id!r} is no longer connected; reconnect first."
                    )
                return client

            # No session id given: fall back only if exactly one is live.
            live = [
                (sid, c) for sid, c in self._clients.items() if c.is_connected()
            ]
            if len(live) == 1:
                return live[0][1]
            if not live:
                raise KeyError(
                    "No active session; call connect first."
                )
            raise KeyError(
                "session_id required: multiple active sessions "
                f"({len(live)}). Provide one of: {self.list_sessions()}"
            )

    def list_sessions(self) -> list[str]:
        """Return the session ids of all currently live sessions."""
        with self._lock:
            return [
                sid for sid, client in self._clients.items()
                if client.is_connected()
            ]

    def has_client(self, session_id: str) -> bool:
        """Return True if a live client is registered for the session id."""
        with self._lock:
            self._prune_if_dead(session_id)
            return session_id in self._clients

    def remove_client(self, session_id: str) -> bool:
        """
        Close and evict the client for a single session.

        Returns True if a client was present and removed, False otherwise.
        """
        with self._lock:
            client = self._clients.pop(session_id, None)
            if client is None:
                return False
            try:
                client.close()
            except Exception:
                pass
            self._logger.info(
                "Removed WebSocket client for %s (session %s)", client.uri, session_id
            )
            return True

    def close_all(self) -> None:
        """Close and clear every registered client (clean shutdown)."""
        with self._lock:
            for client in self._clients.values():
                try:
                    client.close()
                except Exception:
                    pass
            self._clients.clear()
            self._logger.info("Closed all WebSocket clients")
