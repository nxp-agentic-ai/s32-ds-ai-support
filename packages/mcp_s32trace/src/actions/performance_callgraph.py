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
from nxp.mcp.s32trace.handlers.action_handlers import performance_callgraph

PERFORMANCE_CALLGRAPH_ACTION = ActionExecutable(
    contract=ActionContract(
        name="performance.callgraph",
        description=(
            "Return a nested call-graph tree rooted at a given function.\n\n"
            "direction='callees' (default): shows what the root function calls (downward tree).\n"
            "direction='callers': shows who calls the root function (upward tree).\n\n"
            "Each node includes: name, num_calls, pct_inclusive, pct_exclusive, and a "
            "children list.  Cycles and nodes beyond 'depth' are marked truncated=true.\n\n"
            "INPUTS\n"
            "- session_id:           ID returned by performance.load.\n"
            "- root:                 Function name to use as root.\n"
            "- depth (optional):     Maximum tree depth (default 3).\n"
            "- direction (optional): 'callees' (default) or 'callers'.\n"
            "- core (optional):      Restrict to a single core."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from performance.load."},
            ),
            ActionParameter(
                name="root",
                required=True,
                schema={"type": "string", "description": "Root function name."},
            ),
            ActionParameter(
                name="depth",
                required=False,
                schema={"type": "integer", "description": "Maximum tree depth (default 3)."},
            ),
            ActionParameter(
                name="direction",
                required=False,
                schema={
                    "type": "string",
                    "enum": ["callees", "callers"],
                    "description": "'callees' (default) or 'callers'.",
                },
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
        ),
        category="performance",
        workflow_hints=("Call performance.load first. Use performance.hotspots to find a good root.",),
        related_actions=("performance.load", "performance.function", "performance.hotspots"),
    ),
    handler=performance_callgraph,
)
