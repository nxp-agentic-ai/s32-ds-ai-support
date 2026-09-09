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

from nxp.mcp.shared.action import (
    ActionExecutable as ExecutableAction,
    ActionContract,
    ActionParameter
)

from .handlers.session_handler import get_session, close_session

WS_CONNECT = ExecutableAction(
    contract=ActionContract(
        name="ws.connect",
        description="Open a websocket connection to FreeMASTER server.",
        params=[
            ActionParameter(
                name="host",
                required=True,
                schema={
                    "description": "Hostname of the FreeMASTER server.",
                    "minLength": 1,
                    "type": "string"
                },
            ),
            ActionParameter(
                name="port",
                required=True,
                schema={
                    "description": "Port number of the FreeMASTER server.",
                    "minLength": 1,
                    "type": "string"
                }
            )
        ]
    ),
    handler=get_session
)

WS_DISCONNECT = ExecutableAction(
    contract=ActionContract(
        name="ws.disconnect",
        description="Closes a websocket connection to FreeMASTER server.",
        params=[
            ActionParameter(
                name="session_id",
                required=False,
                schema={
                    "description": "Websocket session identifier. Is optional in case of single session.",
                    "minLength": 1,
                    "type": "string"
                }
            )
        ]
    ),
    handler=close_session
)
