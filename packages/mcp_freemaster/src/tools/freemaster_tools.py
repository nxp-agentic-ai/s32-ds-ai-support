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

import logging
from typing import Any, Optional
from fastmcp import FastMCP

from nxp.mcp.shared import ActionCatalog, execute_action, search_actions

from .actions import ACTIONS
from nxp.mcp.freemaster.metadata import MCP_SERVER_NAME
from nxp.mcp.freemaster.config import FreeMASTERMcpServerConfig
from nxp.mcp.freemaster.rpc import WsSessionManager


def register_freemaster_tools(mcp: FastMCP, cfg: FreeMASTERMcpServerConfig) -> None:

    logger = logging.getLogger(MCP_SERVER_NAME)
    action_catalog = ActionCatalog(actions={action.contract.name: action for action in ACTIONS})
    session_manager = WsSessionManager(cfg)

    @mcp.tool(
        name="search_actions",
        description=(
            "Search the catalog of available FreeMASTER actions. This is the entry point "
            "for discovering what the FreeMASTER MCP server can do: use it to list or "
            "find actions before running them. Provide an optional query to narrow results; "
            "omit the query to browse the catalog. Use limit to control how many matching "
            "actions are returned, and raise it to list every available action. Optionally "
            "provide strategy='bm25' (default) or strategy='regex'. Returns matching actions "
            "together with their input schemas so a selected action can be invoked via execute_action."
        ),
    )
    async def search_actions_tool(
        query: Optional[str] = None,
        limit: int = 2,
        strategy: str = "bm25",
    ) -> dict[str, Any]:
        action_contracts = [action.contract for action in action_catalog.actions.values()]
        limit = max(1, min(limit, len(action_contracts)))
        outcome = search_actions(
            action_contracts,
            query=query,
            limit=limit,
            strategy=strategy,
        )
        return outcome.to_response()

    @mcp.tool(
        name="execute_action",
        description=(
            "Execute a FreeMASTER action discovered via search_actions. Provide the "
            "fully qualified action_name returned by search_actions and a params object "
            "that matches that action's input schema (omit params for actions that take "
            "none). Returns the normalized result of the executed action."
        ),
    )
    async def execute_action_tool(
        action_name: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        exec_outcome = await execute_action(
            action_name=action_name,
            params=params,
            action_catalog=action_catalog,
            component_logger=logger,
            session_manager=session_manager
        )
        return exec_outcome.to_response()