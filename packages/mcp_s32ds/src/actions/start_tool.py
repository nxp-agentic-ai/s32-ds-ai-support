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

"""Static ``start_tool`` action for the S32DS MCP server.

Unlike the dynamic actions that are synthesized from the S32DS IDE's
``rpc.discover`` document, ``start_tool`` is served entirely by the MCP server
itself. It brings the IDE (and therefore its RPC bridge) up so that subsequent
live actions can reach it. This action is always present in the catalog even
when the IDE is offline.

The underlying implementation and its OpenRPC-shaped parameter declaration live
in ``nxp.mcp.s32ds.actions.handlers.start_tool_handler``; this module only
adapts them to the shared ``ActionExecutable`` model.
"""

from __future__ import annotations

import asyncio
from typing import Any

from nxp.mcp.shared import (
    ActionContract,
    ActionExecutable,
    action_parameters_from_openrpc,
)

from nxp.mcp.s32ds.actions.handlers.start_tool_handler import (
    START_TOOL_PARAMS,
    start_tool,
)


async def _start_tool_handler(params: dict[str, Any]) -> Any:
    """Adapt the shared ``(params)`` handler signature to ``start_tool(**kwargs)``.

    ``start_tool`` performs blocking work (spawning the launcher and polling the
    RPC bridge), so it runs in a worker thread to avoid stalling the event loop.
    """

    return await asyncio.to_thread(lambda: start_tool(**(params or {})))


START_TOOL_ACTION = ActionExecutable(
    contract=ActionContract(
        name="start_tool",
        description=(
            "Launch the S32DS IDE if its RPC bridge is not already up. Brings "
            "the IDE up so subsequent live actions can reach its RPC bridge. If "
            "the bridge already answers this is a no-op. Served locally by the "
            "MCP server; does not require the IDE to already be running."
        ),
        params=action_parameters_from_openrpc(START_TOOL_PARAMS),

        category="lifecycle",
        workflow_hints=(
            "Call start_tool first so the IDE RPC bridge is up; then "
            "search_actions will surface the live IDE actions.",
        ),
    ),
    handler=_start_tool_handler,
)
