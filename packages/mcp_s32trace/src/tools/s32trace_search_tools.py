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
from nxp.mcp.s32trace.actions import ACTIONS
from nxp.mcp.s32trace.handlers.action_handlers import S32TraceSessionManager
from nxp.mcp.s32trace.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32trace.tools.result_normalization import normalize_s32trace_execution_result

logger = logging.getLogger(MCP_SERVER_NAME)

SEARCH_ACTIONS_DESCRIPTION = (
    "Search standardized S32Trace configurator actions by action name and description. "
    "Use limit to control how many matching actions are returned. "
    "Optionally provide strategy='bm25' (default) or strategy='regex'. "
    "Returns matching actions together with their input schemas so the selected "
    "action can be called directly with execute_action."
)

DEFAULT_SEARCH_RESULTS = 5

EXECUTE_ACTION_DESCRIPTION = (
    "Execute a standardized S32Trace configurator action. Provide the fully qualified "
    "action name from search_actions and a params object that matches the returned "
    "input schema."
)


def register_s32trace_search_tools(server, config, install_ctx: dict) -> None:
    """Register search_actions and execute_action tools on the FastMCP server."""
    mcp = server

    selected = install_ctx.get("selected")
    reason = install_ctx.get("selection_reason", "unknown")

    if selected is not None:
        installation_path: str | None = str(selected.path)
        logger.info(
            "S32Trace using S32DS %s at %s (reason=%s)",
            selected.version_label, installation_path, reason,
        )
    else:
        installation_path = None
        logger.warning(
            "No S32DS install with S32Trace configurator found (reason=%s). "
            "Set s32trace.settings.installation_path in the YAML, or install "
            "S32DS under one of the standard scan roots (e.g. C:/NXP/S32DS.x.y.z).",
            reason,
        )

    # Build the active catalog as a mapping from public action name to its
    # corresponding ActionExecutable object.
    action_catalog = ActionCatalog(actions={action.contract.name: action for action in ACTIONS})

    # S32Trace session context: carries the resolved installation path so handlers
    # can fall back to it when no per-call override is provided.
    session_manager = S32TraceSessionManager(installation_path=installation_path)

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
            result_normalizer=normalize_s32trace_execution_result,
            session_manager=session_manager,
        )
        return exec_outcome.to_response()
