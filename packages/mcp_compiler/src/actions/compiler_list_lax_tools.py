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
from nxp.mcp.compiler.handlers.action_handlers import handle_list_lax_tools


LIST_LAX_TOOLS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="compiler.list_lax_tools",
        description=(
            "Discover and list all LAX toolchains found under the configured root. "
            "Returns available toolchain bin directories and the binaries inside them. "
            "Call this before compiler.lax_execute to find the correct toolchain_bin_dir "
            "and binary name for NXP LAX vector signal processor targets."
        ),
        params=(),
        related_actions=("compiler.lax_execute",),
        category="lax",
    ),
    handler=handle_list_lax_tools,
)
