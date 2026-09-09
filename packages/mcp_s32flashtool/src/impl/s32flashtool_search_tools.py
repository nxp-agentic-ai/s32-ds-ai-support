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
from nxp.mcp.s32flashtool.impl.actions import STATIC_ACTIONS
from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32flashtool.impl.handlers import S32FlashToolSessionManager

from nxp.mcp.s32flashtool.impl.result_normalization import normalize_s32flashtool_execution_result


from nxp.mcp.s32flashtool.config.models import S32FlashToolMcpServerConfig
from nxp.mcp.s32flashtool.impl.actions.gui_rpc_dynamic import rpc_discover_executables
from nxp.mcp.s32flashtool.impl.rpc_client.rpc_client import DEFAULT_RPC_PORT


__all__ = ["register_s32flashtool_search_tools"]


logger = logging.getLogger(MCP_SERVER_NAME)

SEARCH_ACTIONS_DESCRIPTION = (
    """
    IMPORTANT: On first use in a session, you MUST read the MCP resource s32flashtool://nxp_s32flashtool/skills/index 
    and the two meta-skills it names (agent-rules-minimal, workflow-index) before executing any action, including discovery. 
    Always read the matching supported_<platform>_devices.txt before operating on a platform. 
    If the S32FlashTool installation path is unknown, use nxp_knowledge_kb_search (corpus s32flashtool).

    Search standardized S32FlashTool actions by action name and description.

Returns:
  - detailed=false (DEFAULT, PREFERRED): only { name, description } per match.
    Use this for discovery — to find WHICH action you need. Cheap; safe to use
    with larger `limit` values (e.g. 5–10).
  - detailed=true: adds the full JSON input_schema, preconditions, category,
    and related_actions for each match. Token-expensive. Only use once you
    already know the action name, and pair it with `limit=1` (or a query
    that uniquely matches one action) to avoid pulling schemas for actions
    you won't call.

Recommended flow:
  1. search_actions(query="...", detailed=false)         # find the name
  2. search_actions(query="<exact_name>", detailed=true, limit=1)  # get its schema
  3. execute_action(name, params)

Other parameters:
  - limit:    max matches to return (default 5).
  - strategy: 'bm25' (default, natural-language) or 'regex' (exact/pattern).
  - port:     leave as None for CLI operations; set to 51236 (or configured value) only for GUI operations.
    """
)

DEFAULT_SEARCH_RESULTS = 5

EXECUTE_ACTION_DESCRIPTION = (
    "Execute a standardized S32FlashTool action. Provide the fully qualified action name from search_actions "
    "and a params object that matches the returned input schema."
    "Port must be None if no GUI operations needed (for example in case of CLI operations). For GUI operations, default port is 51236."
)


def register_s32flashtool_search_tools(
    server,
    config : S32FlashToolMcpServerConfig
) -> None:
    mcp = server

    # Session manager carrying optional pre-configured runtime state (e.g. the
    # installation folder) forwarded to handlers by the shared dispatcher.
    session_manager = S32FlashToolSessionManager(
        sft_folder=getattr(config.settings, "project_path", None) or None,
    )

    def _build_catalog(port : Optional[int] = None) -> tuple[ActionCatalog, bool]:
        """Build the hybrid S32FlashTool action catalog (static + discovered).

        The catalog is seeded with the package-local static actions, then the
        discovered IDE actions are merged with ``duplicate_policy="replace"`` so a
        discovered method wins over a static action that shares its name.

        This is safe to call repeatedly: callers rebuild the catalog on demand so
        newly discovered IDE methods appear after the IDE comes up.

        Returns the catalog together with a boolean indicating whether any
        dynamic actions were discovered and merged from the GUI.
        """

        catalog = ActionCatalog(
            actions={action.contract.name: action for action in STATIC_ACTIONS},
        )
        dynamic_actions_error = False
        if (port is not None) and (port > 0):
            dynamic_actions = rpc_discover_executables(port)
            if dynamic_actions:
                catalog.merge_actions(dynamic_actions, duplicate_policy="replace")
                dynamic_actions_error = False
            else:
                dynamic_actions_error = True
        return catalog, dynamic_actions_error


 
    @mcp.tool(
        name="search_actions",
        description=SEARCH_ACTIONS_DESCRIPTION,
    )
    async def search_actions_tool(
        query: Optional[str] = None,
        limit: int = DEFAULT_SEARCH_RESULTS,
        strategy: Optional[str] = None,        
        port: Optional[int] = None,
        detailed: Optional[bool] = False
    ) -> dict[str, Any]:
        
        logger.info("search_actions for %d, query: %s", port if port is not None else -1, query)

        current_catalog, dynamic_actions_error = _build_catalog(port)
        # Cache the freshly built catalog on the session manager so a follow-up
        # execute_action call for the same port can reuse it without rebuilding.
        session_manager.set_cached_catalog(port, current_catalog, dynamic_actions_error)
        contracts = [action_executable.contract for action_executable in current_catalog.actions.values()]

        normalized_limit = max(1, min(limit, len(contracts))) if contracts else 1
        search_outcome = search_actions(
            contracts,
            query=query,
            limit=normalized_limit,
            strategy=strategy,
        )
        resp = search_outcome.to_response()

        # When detailed is False, strip every field from each found action
        # except its name and description to keep the response compact.
        if not detailed:
            resp["info"] = "For details about an action, call this tool again with `detailed` = True and use the action name for `query`" 
            result = resp.get("result")
            if isinstance(result, dict):
                actions = result.get("actions")
                if isinstance(actions, list):
                    result["actions"] = [
                        {
                            "name": action.get("name"),
                            "description": action.get("description"),
                        }
                        for action in actions
                        if isinstance(action, dict)
                    ]

        # Only hint about launching the GUI when no dynamic GUI actions were
        # discovered/merged into the catalog.
        if dynamic_actions_error:
            resp["warning"] = "S32FlashTool GUI not reachable. If GUI is needed, launch S32FlashTool GUI with action `gui_launch` with parameter s32flashtool folder."
            logger.info("S32FlashTool GUI not reachable; returning GUI-launch hint in search_actions response.")
        return resp


    @mcp.tool(
        name="execute_action",
        description=EXECUTE_ACTION_DESCRIPTION,
    )
    async def execute_action_tool(
        action: str,
        params: Optional[dict[str, Any]] = None,
        port: Optional[int] = None,
    ) -> dict[str, Any]:
        logger.info("execute_action for %s on port %d, %s", action, port if port is not None else -1, str(params))

        # Reuse the catalog built by a prior search_actions call for this port,
        # if available, to avoid re-running catalog discovery. Fall back to
        # building it on demand (and cache it) when there is no cached entry.
        cached = session_manager.get_cached_catalog(port)
        if cached is not None:
            active_catalog, dynamic_actions_error = cached
        else:
            active_catalog, dynamic_actions_error = _build_catalog(port)
            session_manager.set_cached_catalog(port, active_catalog, dynamic_actions_error)



        exec_outcome = await execute_action(
            action_name=action,
            params=params,
            action_catalog=active_catalog,
            component_logger=logger,
            result_normalizer=normalize_s32flashtool_execution_result,
            session_manager=session_manager,
        )

        return exec_outcome.to_response()
