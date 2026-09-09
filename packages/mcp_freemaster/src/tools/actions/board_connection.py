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

from .handlers.method_handler import build_rpc_handler

START_COMM = ExecutableAction(
    contract=ActionContract(
        name="rpc.StartComm",
        description="Open a connection to the target board.",
        params=[
            ActionParameter(
                name="name",
                required=True,
                schema={
                    "description": (
                        "Connection friendly name defined in the configuration file "
                        "or fully qualified FreeMASTER Lite connection string."
                    ),
                    "minLength": 1,
                    "type": "string"
                }
            ),
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
    handler=build_rpc_handler("StartComm")
)

STOP_COMM = ExecutableAction(
    contract=ActionContract(
        name="rpc.StopComm",
        description="Open a connection to the target board.",
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
    handler=build_rpc_handler("StopComm")
)

IS_COMM_PORT_OPEN = ExecutableAction(
    contract=ActionContract(
        name="rpc.IsCommPortOpen",
        description="Checks whether FreeMASTER connection is open. Use 'StartComm' first.",
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
    handler=build_rpc_handler("IsCommPortOpen")
)

IS_BOARD_CONNECTED = ExecutableAction(
    contract=ActionContract(
        name="rpc.IsBoardDetected",
        description="Checks whether FreeMASTER is connected to the board. Use 'StartComm' first.",
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
    handler=build_rpc_handler("IsBoardDetected")
)

GET_BOARD_INFO =ExecutableAction(
    contract=ActionContract(
        name="rpc.GetDetectedBoardInfo",
        description="Retrieves connected board information encoded in FreeMASTER Driver.",
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
    handler=build_rpc_handler("GetDetectedBoardInfo")
)
