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

DEFINE_VARIABLE = ExecutableAction(
    contract=ActionContract(
        name="rpc.DefineVariable",
        description="Defines a project variable.",
        params=[
            ActionParameter(
                name="variable",
                required=True,
                schema={
                    "description": "Definition of a project variable to be created.",
                    "type": "object",
                    "properties": {
                        "name": {
                            "description": "Non-empty variable name.",
                            "type": "string",
                            "minLength": 1
                        },
                        "addr": {
                            "description": (
                                "Variable address. Either a 32-bit integer "
                                "address or a string representing a symbol name."
                            ),
                            "oneOf": [
                                {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 4294967295
                                },
                                {
                                    "type": "string",
                                    "minLength": 1
                                }
                            ]
                        },
                        "type": {
                            "description": "Variable data type.",
                            "type": "string",
                            "enum": ["int", "uint", "float", "double"]
                        },
                        "size": {
                            "description": "Variable size in bytes.",
                            "type": "integer",
                            "enum": [1, 2, 4, 8]
                        }
                    },
                    "required": ["name", "addr", "type", "size"]
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
    handler=build_rpc_handler("DefineVariable")
)

GET_VARIABLE_INFO = ExecutableAction(
    contract=ActionContract(
        name="rpc.GetVariableInfo",
        description="Retrieves a project variable information.",
        params=[
            ActionParameter(
                name="name",
                required=True,
                schema={
                    "description": "Project variable name.",
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
    handler=build_rpc_handler("GetVariableInfo")
)

DELETE_VARIABLE = ExecutableAction(
    contract=ActionContract(
        name="rpc.DeleteVariable",
        description="Deletes a project variable information.",
        params=[
            ActionParameter(
                name="name",
                required=True,
                schema={
                    "description": "Project variable name.",
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
    handler=build_rpc_handler("DeleteVariable")
)

READ_VARIABLE = ExecutableAction(
    contract=ActionContract(
        name="rpc.ReadVariable",
        description="Reads a project variable value. Variable should be defined either in the configuration file or via 'DefineVariable' action.",
        params=[
            ActionParameter(
                name="name",
                required=True,
                schema={
                    "description": "Project variable name.",
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
    handler=build_rpc_handler("ReadVariable")
)

WRITE_VARIABLE = ExecutableAction(
    contract=ActionContract(
        name="rpc.WriteVariable",
        description="Writes a value into a project variable. Variable should be defined either in the configuration file or via 'DefineVariable' action.",
        params=[
            ActionParameter(
                name="name",
                required=True,
                schema={
                    "description": "Project variable name.",
                    "minLength": 1,
                    "type": "string"
                }
            ),
            ActionParameter(
                name="value",
                required=True,
                schema={
                    "description": "Numeric value.",
                    "type": "number"
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
    handler=build_rpc_handler("WriteVariable")
)