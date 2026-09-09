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

"""Dynamic action synthesis from the S32DS IDE OpenRPC document.

The S32DS IDE advertises its live JSON-RPC surface (``buildProject``,
``getProjectInfo``, ...) via the reserved ``rpc.discover`` method. The generic
conversion of an OpenRPC Method Object into a forwarding
:class:`ActionExecutable` lives in :mod:`nxp.mcp.shared.action.synthesis`; this
module only wires the S32DS-specific client lifecycle (a persistent client
rebuilt into a catalog on demand) around it.

The resulting dynamic actions are merged on top of the package-local static
actions (see :mod:`nxp.mcp.s32ds.actions`). Per the agreed policy a discovered
method with the same name as a static action REPLACES the static one.
"""

from __future__ import annotations

import logging

from nxp.mcp.shared import (
    ActionCatalog,
    ActionExecutable,
    openrpc_method_to_executable_action,
)


from nxp.mcp.s32ds.actions import STATIC_ACTIONS
from nxp.mcp.s32ds.client.rpc_client import RpcClient, RpcError

from nxp.mcp.s32ds.metadata.server import MCP_SERVER_NAME

logger = logging.getLogger(MCP_SERVER_NAME)

# Human-readable label used in the fallback description of discovered methods.
_SOURCE_LABEL = "the S32DS IDE"


def _discovered_actions(client: RpcClient) -> list[ActionExecutable]:
    """Best-effort synthesis of dynamic actions from the IDE OpenRPC document.

    If the IDE is unreachable the discovery attempt is logged and an empty list
    is returned; the static actions (e.g. ``start_tool``) remain available so
    the agent can bring the IDE up and retry.
    """

    try:
        # list_methods() lazily triggers discovery if it has not run yet and
        # now returns the full OpenRPC Method Object for each entry, so no
        # per-method detail lookup is needed.
        methods = client.list_methods()
    except (ConnectionError, RpcError) as exc:
        logger.warning("S32DS discovery failed while building the action catalog (%s).", exc)
        return []

    executables: list[ActionExecutable] = []
    for method in methods:
        if not isinstance(method, dict):
            continue
        executable = openrpc_method_to_executable_action(client, method, source_label=_SOURCE_LABEL)
        if executable is not None:
            executables.append(executable)
    return executables



def build_action_catalog(client: RpcClient) -> ActionCatalog:
    """Build the hybrid S32DS action catalog (static + discovered).

    The catalog is seeded with the package-local static actions, then the
    discovered IDE actions are merged with ``duplicate_policy="replace"`` so a
    discovered method wins over a static action that shares its name.

    This is safe to call repeatedly: callers rebuild the catalog on demand so
    newly discovered IDE methods appear after the IDE comes up.
    """

    static_actions = list(STATIC_ACTIONS)

    catalog = ActionCatalog(
        actions={action.contract.name: action for action in static_actions},
    )
    catalog.merge_actions(_discovered_actions(client), duplicate_policy="replace")
    return catalog
