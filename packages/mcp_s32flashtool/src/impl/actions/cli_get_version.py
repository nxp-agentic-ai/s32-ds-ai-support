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
from nxp.mcp.s32flashtool.impl.handlers import cli_get_version_handler

__all__ = ["CLI_GET_VERSION_ACTION"]

CLI_GET_VERSION_ACTION = ActionExecutable(
    contract=ActionContract(
        name="cli_get_version",
        description=(
            "Return the raw S32FlashTool CLI banner string. "
            "Prefer `get_runtime_info` for most workflows — it returns the same "
            "banner plus MCP identity and a version-match verdict at identical cost. "
            "Use this action only when isolating the CLI layer for debugging."
        ),
        params=(
            ActionParameter(
                name="sft_folder",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Absolute path to the S32FlashTool installation root. "
                        "Falls back to the server runtime context when omitted."
                    ),
                },
            ),
        ),
        preconditions=(
            "An installation root must be resolvable (params.sft_folder).",
        ),
        related_actions=(
            "cli_build_ping",
            "get_runtime_info",
        ),
        category="discovery",
    ),
    handler=cli_get_version_handler,
)
