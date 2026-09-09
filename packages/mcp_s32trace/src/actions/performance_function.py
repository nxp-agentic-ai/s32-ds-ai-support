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
from nxp.mcp.s32trace.handlers.action_handlers import performance_function

PERFORMANCE_FUNCTION_ACTION = ActionExecutable(
    contract=ActionContract(
        name="performance.function",
        description=(
            "Return detailed performance metrics for a specific function: inclusive/exclusive "
            "time, call count, percentage of total, list of callees (with per-call-site metrics "
            "and call-site address), and list of callers.\n\n"
            "INPUTS\n"
            "- session_id:       ID returned by performance.load.\n"
            "- name:             Exact function name (e.g. 'slow_mid1', 'crc16_step_0x33d843b0').\n"
            "- core (optional):  Restrict to a single core."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from performance.load."},
            ),
            ActionParameter(
                name="name",
                required=True,
                schema={"type": "string", "description": "Exact function/symbol name."},
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
        ),
        category="performance",
        workflow_hints=("Call performance.load first. Use performance.hotspots to discover names.",),
        related_actions=("performance.load", "performance.hotspots", "performance.callgraph", "performance.get_source"),
    ),
    handler=performance_function,
)
