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
from nxp.mcp.s32trace.handlers.action_handlers import performance_hotspots

PERFORMANCE_HOTSPOTS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="performance.hotspots",
        description=(
            "Return the top-K performance hotspots sorted by a chosen metric.\n\n"
            "INPUTS\n"
            "- session_id:          ID returned by performance.load.\n"
            "- sort_by (optional):  'inclusive' (default) | 'exclusive' | 'calls'.\n"
            "- top_k (optional):    Number of entries to return (default 10).\n"
            "- core (optional):     Restrict to a single core.\n\n"
            "RETURNS\n"
            "sort_by, items list with name, core, inclusive/exclusive time, call count, code_size."
        ),
        params=(
            ActionParameter(
                name="session_id",
                required=True,
                schema={"type": "string", "description": "Session ID from performance.load."},
            ),
            ActionParameter(
                name="sort_by",
                required=False,
                schema={
                    "type": "string",
                    "enum": ["inclusive", "exclusive", "calls"],
                    "description": "Sort metric: 'inclusive' (default), 'exclusive', or 'calls'.",
                },
            ),
            ActionParameter(
                name="top_k",
                required=False,
                schema={"type": "integer", "description": "Number of entries to return (default 10)."},
            ),
            ActionParameter(
                name="core",
                required=False,
                schema={"type": "string", "description": "Restrict to a single core name."},
            ),
        ),
        category="performance",
        workflow_hints=("Call performance.load first.",),
        related_actions=("performance.load", "performance.function", "performance.summary"),
    ),
    handler=performance_hotspots,
)
