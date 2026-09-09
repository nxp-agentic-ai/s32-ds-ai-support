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
from nxp.mcp.s32flashtool.impl.handlers import get_mcp_version_handler

__all__ = ["GET_MCP_VERSION_ACTION"]

GET_MCP_VERSION_ACTION = ActionExecutable(
    contract=ActionContract(
        name="get_runtime_info",
        description=(
            "Return the S32 Flash Tool MCP version manifest (runtime) as structured JSON: "
            "mcp_server_name, mcp_server_version (server code), and "
            "target_tool_version (the S32 Flash Tool release this MCP was "
            "validated against). When an installation root is provided via "
            "sft_folder, the locally installed S32 Flash Tool version is also "
            "detected using CLI; on a mismatch with target_tool_version a warning is "
            "logged and documentation is preferentially served from the "
            "installed tool's local docs directory."
        ),
        params=(
            ActionParameter(
                name="sft_folder",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Absolute path to the S32FlashTool installation root, "
                        "used to detect the locally installed tool version. "
                        "Falls back to the server runtime context when omitted. "
                        "When no installation is resolvable the manifest is "
                        "still returned without installed-tool detection."
                    ),
                },
            ),
        ),
        preconditions=(
            "None. The manifest is always returned; installed-tool detection "
            "is skipped when no installation root is resolvable.",
        ),
        related_actions=(
            "cli_get_version",
        ),
        category="discovery",
    ),
    handler=get_mcp_version_handler,
)
