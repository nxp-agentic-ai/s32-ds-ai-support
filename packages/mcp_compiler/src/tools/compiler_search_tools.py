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

"""Compiler MCP public tool surface: search_actions + execute_action.

This module registers exactly two MCP tools that replace the previous six
individual tools (list_gcc_compiler_tools, gcc_execute, list_lax_compiler_tools,
lax_execute, list_spt_compiler_tools, spt_execute).

The active action catalog is built dynamically at startup from the per-family
action tuples, including only the families whose toolchain folders exist on the
current host. The two public tools are always registered regardless of which
toolchains are available - search_actions will simply return no results for
families that are not installed.
"""

import logging
from typing import Any, Optional

from nxp.mcp.shared import ActionCatalog, execute_action, search_actions
from nxp.mcp.compiler.metadata.server import MCP_SERVER_NAME
from nxp.mcp.compiler.handlers.action_handlers import CompilerInstallManager

logger = logging.getLogger(MCP_SERVER_NAME)

SEARCH_ACTIONS_DESCRIPTION = (
    "Search standardized compiler actions by action name and description. "
    "Use limit to control how many matching actions are returned. "
    "Optionally provide strategy='bm25' (default) or strategy='regex'. "
    "Returns matching actions together with their input schemas so the selected "
    "action can be called directly with execute_action. "
    "Available action categories: gcc, lax, lax_simulator, spt (depending on installed toolchains)."
)

DEFAULT_SEARCH_RESULTS = 5

EXECUTE_ACTION_DESCRIPTION = (
    "Execute a standardized compiler action. Provide the fully qualified action name "
    "from search_actions and a params object that matches the returned input schema. "
    "Examples: compiler.gcc_execute, compiler.lax_execute, compiler.lax_simulator_execute, "
    "compiler.spt_execute, compiler.list_gcc_tools, compiler.list_lax_tools, "
    "compiler.list_lax_simulator_tools, compiler.list_spt_tools."
)


def register_compiler_search_tools(
    server,
    install,
    gcc_present: bool = False,
    lax_present: bool = False,
    lax_simulator_present: bool = False,
    spt_present: bool = False,
) -> None:
    """Register search_actions and execute_action for the compiler MCP server.

    Args:
        server:                 The FastMCP server instance.
        install:                Resolved CompilerInstallInfo (may be None if no install found).
        gcc_present:            True if the GCC toolchain folder exists on this host.
        lax_present:            True if the LAX toolchain folder exists on this host.
        lax_simulator_present:  True if the LAX simulator folder exists on this host.
        spt_present:            True if the SPT3.8 toolchain folder exists on this host.
    """
    from nxp.mcp.compiler.actions import GCC_ACTIONS, LAX_ACTIONS, LAX_SIMULATOR_ACTIONS, SPT_ACTIONS

    mcp = server

    # Build the catalog dynamically from the families that are actually installed.
    active_actions: tuple = ()
    if gcc_present:
        active_actions += GCC_ACTIONS
    if lax_present:
        active_actions += LAX_ACTIONS
    if lax_simulator_present:
        active_actions += LAX_SIMULATOR_ACTIONS
    if spt_present:
        active_actions += SPT_ACTIONS

    action_catalog = ActionCatalog(
        actions={action.contract.name: action for action in active_actions}
    )

    # Session manager carries the resolved install info so handlers can
    # access toolchain paths without relying on module-level globals.
    session_manager = CompilerInstallManager(install=install) if install else None

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
            action_executable.contract
            for action_executable in action_catalog.actions.values()
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
        exec_outcome = await execute_action(
            action_name=action_name,
            params=params,
            action_catalog=action_catalog,
            component_logger=logger,
            session_manager=session_manager,
        )
        return exec_outcome.to_response()
