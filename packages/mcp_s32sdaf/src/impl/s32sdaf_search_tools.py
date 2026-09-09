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

"""Search-first tool surface for the S32SDAF MCP server.

Exposes exactly three tools, mirroring the standardized pattern adopted across
the MCP:

- ``search_actions``  -- discover the standardized Volkano actions and their
  input schemas (BM25 by default, or regex).
- ``execute_action``  -- run a discovered action by name with a validated
  ``params`` object; every result is shaped into the uniform ``ActionOutcome``
  envelope (``{success, result}`` on success, ``{success,
  error:{code, message, details}}`` on failure).
- ``status``          -- a lightweight, always-present health probe that
  reports server config and the Volkano installation that will be used.
"""

import logging
from typing import Any, Optional

from nxp.mcp.shared import ActionCatalog, execute_action, search_actions
from nxp.mcp.s32sdaf.impl.actions import STATIC_ACTIONS
from nxp.mcp.s32sdaf.impl.handlers.action_handlers import S32SdafSessionManager
from nxp.mcp.s32sdaf.impl.result_normalization import normalize_s32sdaf_execution_result
from nxp.mcp.s32sdaf.impl import volkano_core as vc
from nxp.mcp.s32sdaf.metadata.server import (
    MCP_SERVER_NAME,
    MCP_SERVER_VERSION,
    MCP_SERVER_DESCRIPTION,
)

logger = logging.getLogger(MCP_SERVER_NAME)

DEFAULT_SEARCH_RESULTS = 5

SEARCH_ACTIONS_DESCRIPTION = (
    "Search standardized S32SDAF (Volkano smart-card) actions by action name and description. "
    "Use limit to control how many matching actions are returned. "
    "Optionally provide strategy='bm25' (default) or strategy='regex'. "
    "Returns matching actions together with their input schemas so the selected action "
    "can be called directly with execute_action."
)

EXECUTE_ACTION_DESCRIPTION = (
    "Execute a standardized S32SDAF (Volkano) action. Provide the fully qualified action name "
    "from search_actions and a params object that matches the returned input schema. "
    "Returns a uniform envelope: {success: true, result: ...} on success, or "
    "{success: false, error: {code, message, details}} on failure."
)

STATUS_DESCRIPTION = (
    "Health probe for the S32SDAF MCP server. Reports the server name/version, the configured "
    "installation_path, and the Volkano installation that will be used by default when "
    "volkano_folder is not supplied. Call this first to confirm the server is reachable."
)


def register_s32sdaf_search_tools(server, config) -> None:
    mcp = server

    configured_path = getattr(config.settings, "installation_path", None) or None

    # Session manager carrying optional pre-configured runtime state (the Volkano
    # installation folder), forwarded to handlers by the shared dispatcher.
    session_manager = S32SdafSessionManager(volkano_folder=configured_path)

    catalog = ActionCatalog(
        actions={action.contract.name: action for action in STATIC_ACTIONS},
    )

    @mcp.tool(
        name="search_actions",
        description=SEARCH_ACTIONS_DESCRIPTION,
    )
    async def search_actions_tool(
        query: Optional[str] = None,
        limit: int = DEFAULT_SEARCH_RESULTS,
        strategy: Optional[str] = None,
    ) -> dict[str, Any]:
        logger.info("search_actions query=%r limit=%d strategy=%r", query, limit, strategy)
        contracts = [
            action_executable.contract
            for action_executable in catalog.actions.values()
        ]
        normalized_limit = max(1, min(limit, len(contracts))) if contracts else 1
        search_outcome = search_actions(
            contracts,
            query=query,
            limit=normalized_limit,
            strategy=strategy,
        )
        return search_outcome.to_response()

    @mcp.tool(
        name="execute_action",
        description=EXECUTE_ACTION_DESCRIPTION,
    )
    async def execute_action_tool(
        action: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        logger.info("execute_action action=%s", action)
        exec_outcome = await execute_action(
            action_name=action,
            params=params,
            action_catalog=catalog,
            component_logger=logger,
            result_normalizer=normalize_s32sdaf_execution_result,
            session_manager=session_manager,
        )
        return exec_outcome.to_response()

    @mcp.tool(
        name="status",
        description=STATUS_DESCRIPTION,
    )
    def status() -> dict[str, Any]:
        logger.debug("status tool called")
        installations = []
        recommended = None
        try:
            found = vc.find_volkano_installations()
            installations = [
                {
                    "volkano_folder": c["volkano_folder"],
                    "install_root": c["install_root"],
                    "version": c["version_label"],
                }
                for c in found
            ]
            recommended = installations[0]["volkano_folder"] if installations else None
        except Exception as exc:  # noqa: BLE001 - status must never raise
            logger.warning("status: installation discovery failed: %s", exc)

        default_folder = configured_path or recommended
        return {
            "status": "ok",
            "server": {
                "name": MCP_SERVER_NAME,
                "version": MCP_SERVER_VERSION,
                "description": MCP_SERVER_DESCRIPTION,
            },
            "configured_installation_path": configured_path,
            "default_volkano_folder": default_folder,
            "installations": installations,
            "recommended": recommended,
        }
