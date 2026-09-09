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
from nxp.mcp.s32trace.handlers.action_handlers import performance_summary

PERFORMANCE_SUMMARY_ACTION = ActionExecutable(
    contract=ActionContract(
        name="performance.summary",
        description=(
            "Return overall performance statistics for a loaded session: total function "
            "and call counts, top-K functions by inclusive time, top-K by exclusive (self) "
            "time, and top-K by call count.\n\n"
            "INPUTS\n"
            "- session_id:        ID returned by performance.load.\n"
            "- core (optional):   Restrict to a single core (e.g. 'A53_0'). Omit for all cores.\n"
            "- top_k (optional):  How many entries per ranked list (default 10).\n\n"
            "RETURNS\n"
            "total_functions, total_calls, top_by_inclusive_time, "
            "top_by_exclusive_time, top_by_call_count."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from performance.load."},
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
            ActionParameter(
                name="top_k",
                required=False,
                schema={"type": "integer", "description": "Entries per ranked list (default 10)."},
            ),
        ),
        category="performance",
        workflow_hints=("Call performance.load first to obtain a session_id.",),
        related_actions=("performance.load", "performance.hotspots", "performance.function"),
    ),
    handler=performance_summary,
)
