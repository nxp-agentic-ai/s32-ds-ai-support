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

"""
S32 Design Studio MCP tools - shared search-and-execute action surface.

The agent sees exactly two tools:

  1. search_actions(query, limit, strategy)   Discover actions by name/description.
  2. execute_action(action_name, params)      Invoke a discovered action.

The action catalog is hybrid:

  * ``start_tool`` is a STATIC action baked into this package. It is always
    available - even before the S32DS IDE is running - so the agent can bring
    the IDE up.
  * Every live S32DS IDE JSON-RPC method (``buildProject``, ``getProjectInfo``,
    ...) is DISCOVERED dynamically from the IDE's ``rpc.discover`` document and
    synthesized into an action. Discovered actions REPLACE a static action that
    shares its name.

The catalog is rebuilt on demand for each tool call, so newly discovered IDE
methods appear as soon as the IDE (and its RPC bridge) come up.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from nxp.mcp.shared import execute_action, search_actions

from nxp.mcp.s32ds.actions.dynamic import build_action_catalog
from nxp.mcp.s32ds.client.rpc_client import RpcClient, RpcError
from nxp.mcp.s32ds.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ds.tools.result_normalization import normalize_s32ds_execution_result

logger = logging.getLogger(MCP_SERVER_NAME)

DEFAULT_SEARCH_RESULTS = 5

SEARCH_ACTIONS_DESCRIPTION = (
    "Search available S32DS actions by action name and description. "
    "Use limit to control how many matching actions are returned. "
    "Optionally provide strategy='bm25' (default) or strategy='regex'. "
    "Returns matching actions together with their input schemas so the selected "
    "action can be called directly with execute_action. The catalog includes the "
    "static 'start_tool' action plus every live S32DS IDE method discovered from "
    "the running IDE. Optionally provide 'port' to repoint the client at a "
    "non-default S32DS IDE RPC port (default from the s32ds_rest_port config, "
    "8088); the port is sticky and persists for later calls until changed again. "
    "\n\n"
    "IMPORTANT - call this proactively: whenever the user asks something that "
    "could be answered by the live IDE runtime (e.g. installed toolchains/"
    "compilers, SDKs, debuggers, cores, processors, workspace projects, build "
    "configs, or debug/launch configurations), call search_actions FIRST to look "
    "for a matching live action - do not answer from memory before checking. If "
    "the catalog only contains 'start_tool' (no live IDE methods were "
    "discovered), the IDE is not reachable yet: call the 'start_tool' action via "
    "execute_action to bring it up, then call search_actions again. If the IDE "
    "still cannot be reached (start_tool reports status='failed'), tell the user "
    "the IDE could not be started and that runtime data is unavailable, then you "
    "may answer from general/training knowledge, clearly noting it is not live "
    "data from this environment."
)

EXECUTE_ACTION_DESCRIPTION = (
    "Execute an S32DS action. Provide the action name from search_actions and a "
    "params object that matches the returned input schema. 'start_tool' is served "
    "locally by the MCP server; all other actions are forwarded to the live S32DS "
    "IDE, so call start_tool first if the IDE is not running yet. Optionally "
    "provide 'port' to repoint the client at a non-default S32DS IDE RPC port "
    "(default from the s32ds_rest_port config, 8088); the port is sticky and "
    "persists for later calls until changed again. "
    "\n\n"
    "Flow for runtime questions (installed toolchains/compilers, SDKs, "
    "debuggers, cores, processors, projects, build/debug configs, etc.): after "
    "search_actions shows no live IDE action, execute 'start_tool' to attempt to "
    "bring the IDE up. If the result has status='already_running' or "
    "status='started', call search_actions again to pick up the newly "
    "discovered live actions. If the result has status='failed', do not retry "
    "silently - notify the user that the S32DS IDE could not be started (include "
    "the 'error' field) so they know the answer cannot come from live runtime "
    "data; you may then answer from general/training knowledge, clearly noting "
    "it is not live data from this environment."
)




def register_all_tools(server, config) -> None:
    """
    Register the S32DS action-catalog tool surface on the FastMCP server.

    Eagerly attempts ``rpc.discover`` so any contract mismatch surfaces at
    startup rather than at the first agent request. If the IDE is not running
    yet, the error is logged but the MCP server still starts; the static
    ``start_tool`` action remains available so the agent can bring the IDE up
    and retry.
    """
    client = RpcClient(port=config.settings.s32ds_rest_port)

    try:
        client.discover()
    except (ConnectionError, RpcError) as e:
        logger.warning(
            "Initial rpc.discover failed (%s). Only static actions are available "
            "until the IDE is up; the catalog is rebuilt on each tool call.",
            e,
        )

    def _current_catalog():
        # Rebuild on demand so discovered IDE methods appear once the IDE is up.
        return build_action_catalog(client)

    @server.tool(name="search_actions", description=SEARCH_ACTIONS_DESCRIPTION)
    async def search_actions_tool(
        query: Optional[str] = None,
        limit: int = DEFAULT_SEARCH_RESULTS,
        strategy: str = "bm25",
        port: Optional[int] = None,
    ) -> dict[str, Any]:
        # Sticky, idempotent port switch: repoints the client only when a
        # different port is supplied and persists for subsequent calls.
        client.set_port(port)
        action_catalog = _current_catalog()

        contracts = [executable.contract for executable in action_catalog.actions.values()]
        normalized_limit = max(1, min(limit, len(contracts))) if contracts else 1
        outcome = search_actions(
            contracts,
            query=query,
            limit=normalized_limit,
            strategy=strategy,
        )
        return outcome.to_response()

    @server.tool(name="execute_action", description=EXECUTE_ACTION_DESCRIPTION)
    async def execute_action_tool(
        action_name: str,
        params: Optional[dict[str, Any]] = None,
        port: Optional[int] = None,
    ) -> dict[str, Any]:
        # Sticky, idempotent port switch: repoints the client only when a
        # different port is supplied and persists for subsequent calls.
        client.set_port(port)
        action_catalog = _current_catalog()

        exec_outcome = await execute_action(
            action_name=action_name,
            params=params,
            action_catalog=action_catalog,
            component_logger=logger,
            result_normalizer=normalize_s32ds_execution_result,
        )
        return exec_outcome.to_response()
