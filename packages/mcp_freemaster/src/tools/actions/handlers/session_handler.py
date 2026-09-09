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

import json
from typing import Any

from nxp.mcp.freemaster.rpc import WsSessionManager


async def get_session(params: dict[str, Any], session_manager: WsSessionManager | None = None) -> Any:
    """
    Initialize (or re-initialize) the FreeMASTER JSON-RPC WebSocket client.

     Params:
          host:     JSON-RPC server host name.
          port:     JSON-RPC server port number.

    host and port default to the values from the server configuration file
    (ws_host / ws_port under settings). Call this tool before using
    call_method(). It is safe to call again to reconnect or change target.

    Returns a JSON object with "status" and "session_id". The
    "session_id" is an opaque handle (e.g. "fm-1a2b3c4d") the AI agent passes
    back on subsequent commands to route them to this connection. It is stable
    across transparent reconnects to the same endpoint.
    """
    host = params.get("host") or session_manager.server_cfg.settings.ws_host
    port = params.get("port") or session_manager.server_cfg.settings.ws_port

    try:
        session_id, _ = session_manager.get_client(host, port)
        return json.dumps({"success": "true", "session_id": session_id})
    except ConnectionError as exc:
        return json.dumps({"success": "false", "error": str(exc)})


async def close_session(params: dict[str, Any], session_manager: WsSessionManager | None = None) -> Any:
    """
    Close the FreeMASTER JSON-RPC WebSocket connection for a given session id.

     Params:
          session_id:   Opaque session handle (e.g. "fm-1a2b3c4d") returned by
                        get_session, identifying the connection to close.

    Closes and evicts the matching client from the session registry. Returns a
    JSON object with "success" and the "session_id" that was targeted. If no
    client is registered for the provided session id, "success" is "false".
    """
    session_id = params.get("session_id")

    if not session_id:
        return json.dumps({"success": "false", "error": "session_id is required"})

    removed = session_manager.remove_client(session_id)
    if removed:
        return json.dumps({"success": "true", "session_id": session_id})
    return json.dumps({
        "success": "false",
        "error": f"Unknown or already closed session id: {session_id}",
    })
