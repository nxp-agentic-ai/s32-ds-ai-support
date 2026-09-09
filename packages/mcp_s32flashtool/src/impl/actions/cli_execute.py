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

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter
from nxp.mcp.s32flashtool.impl.handlers import cli_execute_handler


__all__ = ["CLI_EXECUTE_ACTION"]


CLI_EXECUTE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="cli_execute",
        description="Execute a raw S32FlashTool command string through the CLI.",
        params=(
            ActionParameter(
                name="sft_folder",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Absolute path to the S32FlashTool folder. Callers should always "
                        "provide it. If the server runtime context has one configured it is "
                        "used as a fallback, but agents must not rely on that."
                    ),
                },
            ),
            ActionParameter(
                name="command",
                required=True,
                schema={
                    "type": "string",
                    "minLength": 1,
                    "description": "Raw S32FlashTool command string to execute.",
                },
            ),
        ),
        preconditions=(
            "An effective installation path must be configured (params.sft_folder or the server runtime context).",
        ),
        related_actions=(
            "cli_build_command",
        ),
        category="cli",
    ),
    handler=cli_execute_handler,
)
