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

"""Dynamic action synthesis from the S32 Flash Tool GUI OpenRPC document.

The S32 Flash Tool GUI advertises its live JSON-RPC surface (...) via the
reserved ``rpc.discover`` method. The generic conversion of an OpenRPC Method
Object into a forwarding :class:`ActionExecutable` lives in
:mod:`nxp.mcp.shared.action.synthesis`; this module only wires the
S32FlashTool-specific client lifecycle (a fresh client created per requested
port) around it.

The resulting dynamic actions are merged on top of the package-local static
actions (see :mod:`actions`). Per the agreed policy a discovered method with the
same name as a static action REPLACES the static one.
"""

from __future__ import annotations

import logging
from typing import Optional

from nxp.mcp.shared import (
    ActionExecutable,
    openrpc_method_to_executable_action,
)

from nxp.mcp.s32flashtool.impl.rpc_client.rpc_client import RpcClient, RpcError
from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME

__all__ = ["rpc_discover_executables"]

logger = logging.getLogger(MCP_SERVER_NAME)

# Human-readable label used in the fallback description of discovered methods.
_SOURCE_LABEL = "the S32 Flash Tool GUI"


def rpc_discover_executables(port: Optional[int] = None) -> list[ActionExecutable]:
    """Best-effort synthesis of dynamic actions from the IDE OpenRPC document.

    If the IDE is unreachable the discovery attempt is logged and an empty list
    is returned; the static actions (e.g. ``start_tool``) remain available so
    the agent can bring the IDE up and retry.
    """

    if port is None:
        return []
    if port < 1:
        return []

    client = RpcClient(port)

    try:
        client.discover()
    except (ConnectionError, RpcError) as e:
        logger.warning(
            "Initial rpc.discover failed (%s). Only static actions are available "
            "until the IDE is up; the catalog is rebuilt on each tool call.",
            e,
        )

    try:
        # list_methods() lazily triggers discovery if it has not run yet and
        # returns the full OpenRPC Method Object for each entry, so no
        # per-method detail lookup is needed.
        catalogue = client.list_methods()
    except (ConnectionError, RpcError) as exc:
        logger.warning("S32FlashTool discovery failed while building the action catalog (%s).", exc)
        return []

    executables: list[ActionExecutable] = []
    for detail in catalogue:
        if not isinstance(detail, dict):
            continue
        executable = openrpc_method_to_executable_action(client, detail, source_label=_SOURCE_LABEL)
        if executable is not None:
            executables.append(executable)
    return executables
