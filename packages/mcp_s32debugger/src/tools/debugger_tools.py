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

from nxp.mcp.shared import ActionCatalog, execute_action, search_actions
from nxp.mcp.s32debugger.actions import ACTIONS
from nxp.mcp.s32debugger.server.s32debugger_session_manager import S32DebuggerSessionManager
from nxp.mcp.s32debugger.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32debugger.tools.result_normalization import normalize_s32debugger_execution_result

logger = logging.getLogger(MCP_SERVER_NAME)

SEARCH_ACTIONS_DESCRIPTION = (
    "Search standardized S32Debugger actions by action name and description. "
    "Use limit to control how many matching actions are returned; the default returns most of the "
    "small catalog, and limit can be raised to list every available action. Passing an exact, fully "
    "qualified action name returns just that single action. "
    "Optionally provide strategy='bm25' (default) or strategy='regex'. "
    "Returns matching actions together with their input schemas so the selected action can be called directly with execute_action."
)

# The S32Debugger catalog is small (12 actions), so default to returning most of
# it rather than a narrow top-5; callers can still raise limit to list them all.
DEFAULT_SEARCH_RESULTS = 8


EXECUTE_ACTION_DESCRIPTION = (
    "Execute a standardized S32Debugger action. Provide the fully qualified action name from search_actions "
    "and a params object that matches the returned input schema."
)


def register_debugger_tools(server, config):
    """Register search-first S32Debugger tools with the MCP server."""
    configured_installation_path = (config.settings.installation_path or "").strip() or None
    logger.info("Registering S32Debugger tools at: %s", configured_installation_path)

    # The session manager owns all in-memory session state (GTA/CCS/GDB
    # processes and installation paths) and is passed to every action handler.
    session_manager = S32DebuggerSessionManager(
        configured_installation_path=configured_installation_path,
    )

    mcp = server
    # Build the active catalog as a mapping from public action name to
    # its corresponding ActionExecutable object.
    action_catalog = ActionCatalog(actions={action.contract.name: action for action in ACTIONS})

    @mcp.tool(
        name="search_actions",
        description=SEARCH_ACTIONS_DESCRIPTION,
    )
    async def search_actions_tool(
        query: Optional[str] = None,
        limit: int = DEFAULT_SEARCH_RESULTS,
        strategy: str = "bm25",
    ) -> dict[str, Any]:
        contracts = [action_executable.contract for action_executable in action_catalog.actions.values()]
        normalized_limit = max(1, min(limit, len(contracts))) if contracts else 1
        outcome = search_actions(
            contracts,
            query=query,
            limit=normalized_limit,
            strategy=strategy,
        )
        return outcome.to_response()

    @mcp.tool(
        name="execute_action",
        description=EXECUTE_ACTION_DESCRIPTION,
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
            result_normalizer=normalize_s32debugger_execution_result,
            session_manager=session_manager,
            # timeout_seconds=30.0, optional parameter for timeout per action.
        )
        return exec_outcome.to_response()