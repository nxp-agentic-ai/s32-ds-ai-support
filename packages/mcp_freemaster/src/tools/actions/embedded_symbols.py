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

READ_ELF = ExecutableAction(
    contract=ActionContract(
        name="rpc.ReadELF",
        description="Loads and parses symbolic information from an ELF file defined in the configuration file.",
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
    handler=build_rpc_handler("ReadELF")
)


READ_TSA = ExecutableAction(
    contract=ActionContract(
        name="rpc.ReadTSA",
        description="Loads symbolic information directly from a connected board via Target Side Addressing.",
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
    handler=build_rpc_handler("ReadTSA")
)
