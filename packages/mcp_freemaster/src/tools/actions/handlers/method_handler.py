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

def build_rpc_handler(name: str):

    async def call_method(params: dict[str, Any], session_manager: WsSessionManager | None = None) -> Any:
        """
        Send a JSON-RPC request to a connected FreeMASTER server and return the reply.

        Params:
        method:     JSON-RPC method name, e.g. "FreeMASTER.ReadVariable".
        params:     Optional dict of method parameters. Omit or pass {} for
                    methods that take no parameters.
        session_id: Optional opaque handle returned by connect (e.g. "fm-1a2b3c4d").
                    Selects which connected server to route this request to.
                    It may be omitted when exactly one session is active; when
                    multiple servers are connected it is required.

        Returns the full JSON-RPC response object, or a JSON object with an "error"
        field when routing or transport fails.
        """
        session_id = params.pop("session_id", None)
        rpc_method = name
        rpc_params = params

        try:
            client = session_manager.resolve(session_id)
        except KeyError as exc:
            return json.dumps({"error": str(exc)})

        try:
            response = client.call(rpc_method, rpc_params)
            return json.dumps(response)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    return call_method