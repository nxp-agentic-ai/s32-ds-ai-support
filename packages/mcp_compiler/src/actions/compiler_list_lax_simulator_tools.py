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

from nxp.mcp.shared import ActionContract, ActionExecutable
from nxp.mcp.compiler.handlers.action_handlers import handle_list_lax_simulator_tools


LIST_LAX_SIMULATOR_TOOLS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="compiler.list_lax_simulator_tools",
        description=(
            "Discover and list all LAX simulator binaries available under the "
            "configured LAX_Simulator directory (runsim, ccssim2, ...). "
            "Call this first before compiler.lax_simulator_execute to confirm "
            "runsim is present and to see what other simulator binaries are available."
        ),
        params=(),
        preconditions=("LAX Simulator must be installed under S32DS/tools/LAX_Simulator/.",),
        workflow_hints=("Call this before compiler.lax_simulator_execute to confirm runsim is present.",),
        related_actions=("compiler.lax_simulator_execute",),
        category="lax_simulator",
    ),
    handler=handle_list_lax_simulator_tools,
)
