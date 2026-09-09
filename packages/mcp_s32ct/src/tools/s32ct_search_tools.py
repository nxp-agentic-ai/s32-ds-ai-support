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

"""S32CT public MCP surface: ``search_actions`` + ``execute_action``.

These two tools replace the five ``action`` / ``kind`` / ``query``-routed
dispatchers (configure, inspect, validate, sanitize, env) that this server used
to expose. The capabilities are unchanged - every former mode is now a
first-class action in the catalog built from
:data:`nxp.mcp.s32ct.actions.ACTIONS`, with its own derived ``input_schema``,
so an agent sees only the parameters that actually apply to the operation it
picked instead of a ~50-parameter union.

Both tools are registered unconditionally, even when no S32 Configuration Tools
installation is resolvable. The read-only ``s32ct.env_*`` actions are the
documented way to diagnose exactly that situation, so they must stay reachable;
launcher-backed actions then fail with a structured precondition error.
"""

import logging
from typing import Any, Optional

from nxp.mcp.shared import ActionCatalog, execute_action, search_actions

from nxp.mcp.s32ct.actions import ACTIONS
from nxp.mcp.s32ct.handlers.action_handlers import S32CTSessionManager
from nxp.mcp.s32ct.impl.result_normalization import (
    normalize_s32ct_execution_result,
)
from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import S32CTContext

logger = logging.getLogger(MCP_SERVER_NAME)

DEFAULT_SEARCH_RESULTS = 5

SEARCH_ACTIONS_DESCRIPTION = (
    "Search standardized S32 Configuration Tools (S32CT) actions by name and "
    "description. Use this first to discover the right action for a task, then "
    "call execute_action with the name and an input_schema-conforming params "
    "object. Use limit to control how many matches are returned. Optionally "
    "provide strategy='bm25' (default, natural-language relevance) or "
    "strategy='regex' (exact / pattern lookup). Returns matching actions with "
    "their input schemas, preconditions and workflow hints so the selected "
    "action can be called directly. Action categories: configure (headless "
    ".mex edits, exports and code generation for Pins, Clocks, Peripherals, "
    "DCD, IVT, eFUSE, QuadSPI, FFC), gtm (Generic Timer Module edits and "
    "use-case bootstrap), inspect (read-only structural queries over a .mex), "
    "lookup (enumerate installed MCUs and their PlatformSDK/SDK versions, plus "
    "legal pins, drivers and enum values from the MCU data package), "
    "validate (Problems-View validation gate), sanitize (repair dangling "
    "cross-references after splicing), env (installation and version probes)."
)


EXECUTE_ACTION_DESCRIPTION = (
    "Execute a standardized S32 Configuration Tools action. Provide the fully "
    "qualified action name from search_actions and a params object matching the "
    "returned input_schema. Examples: s32ct.env_status, s32ct.inspect_summary, "
    "s32ct.configure_pins, s32ct.validate, s32ct.sanitize, "
    "s32ct.generate_code, s32ct.lookup_enum_values, "
    "s32ct.gtm_create_from_usecase. Params are validated against the schema "
    "before anything runs, so invalid input is reported without spawning the "
    "launcher."
)


def register_s32ct_search_tools(server, config) -> None:
    """Register ``search_actions`` and ``execute_action`` for this server.

    The catalog and the session manager are both built once here, at startup:
    the action manifest is static, and ``S32CTContext.from_settings`` performs
    filesystem discovery that should not be repeated on every tool call.
    """

    mcp = server

    ctx = S32CTContext.from_settings(config.settings)
    session_manager = S32CTSessionManager(ctx=ctx)

    action_catalog = ActionCatalog(
        actions={action.contract.name: action for action in ACTIONS},
    )

    if not ctx.is_selected:
        logger.warning(
            "No S32 Configuration Tools install resolved (reason=%s). The "
            "action surface is still registered; use s32ct.env_status to "
            "diagnose.",
            ctx.selection_reason,
        )

    logger.info(
        "S32CT action catalog ready: %d actions across categories %s",
        len(action_catalog.actions),
        ", ".join(action_catalog.categories),
    )

    @mcp.tool(
        name="search_actions",
        description=SEARCH_ACTIONS_DESCRIPTION,
    )
    async def search_actions_tool(
        query: Optional[str] = None,
        limit: int = DEFAULT_SEARCH_RESULTS,
        strategy: str = "bm25",
    ) -> dict[str, Any]:
        contracts = [
            executable.contract for executable in action_catalog.actions.values()
        ]
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
        logger.info("execute_action: %s", action_name)

        # A launcher run can legitimately take minutes (a chained 9-tool
        # validation especially), so the timeout comes from the server
        # configuration rather than a hardcoded constant. Without it a hung
        # launcher would block the tool call indefinitely; with it the caller
        # gets a structured ACTION_TIMEOUT instead.
        outcome = await execute_action(
            action_name=action_name,
            params=params,
            action_catalog=action_catalog,
            component_logger=logger,
            result_normalizer=normalize_s32ct_execution_result,
            session_manager=session_manager,
            timeout_seconds=float(ctx.timeout_s),
        )
        return outcome.to_response()
