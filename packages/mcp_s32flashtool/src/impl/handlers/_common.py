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

"""Shared state and helpers for S32FlashTool action handlers.

Holds the component session manager, the effective-folder resolver, the shared
logger, and the protocol-facing error codes that every individual handler
module reuses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError, errors
from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME


logger = logging.getLogger(MCP_SERVER_NAME)

# Protocol-facing error codes, sourced from the shared error registry so a
# single numeric code has exactly one meaning across the whole MCP layer.
# INVALID_PARAMS mirrors the JSON-RPC invalid-params code; the remaining
# handler/precondition/execution errors reuse the shared forward-error code.

INVALID_PARAMS_CODE = errors.INVALID_PARAMS
HANDLER_ERROR_CODE = errors.FORWARD_ERROR


@dataclass
class S32FlashToolSessionManager:
    """Optional runtime state for S32FlashTool action handlers.

    Lets the server pre-configure an installation folder and a GUI REST port so
    agents do not have to repeat them on every call. It is passed to handlers as
    the ``session_manager`` argument by the shared dispatcher.

    It also caches the action catalog built by ``search_actions`` so that
    ``execute_action`` can reuse it without rebuilding. The cache is keyed by the
    GUI RPC port (``None`` for the CLI-only / no-GUI case) since the set of
    discovered dynamic actions depends on the port.
    """

    sft_folder: Optional[str] = None
    gui_port: Optional[int] = None
    # Catalog cache keyed by port. Values are (catalog, dynamic_actions_error)
    # tuples as returned by the tool's ``_build_catalog`` helper. Excluded from
    # equality/repr so the session manager stays comparable/printable.
    _catalog_cache: dict = field(default_factory=dict, repr=False, compare=False)

    def get_cached_catalog(self, port: Optional[int]):
        """Return the cached (catalog, dynamic_actions_error) tuple, if any."""

        return self._catalog_cache.get(port)

    def set_cached_catalog(self, port: Optional[int], catalog, dynamic_actions_error: bool) -> None:
        """Store the built catalog for ``port`` so it can be reused later."""

        self._catalog_cache[port] = (catalog, dynamic_actions_error)


def effective_sft_folder(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> str:
    sft_folder = params.get("sft_folder")
    if isinstance(sft_folder, str) and sft_folder.strip():
        return sft_folder.strip()
    if (
        session_manager is not None
        and isinstance(session_manager.sft_folder, str)
        and session_manager.sft_folder.strip()
    ):
        return session_manager.sft_folder
    raise ActionExecutionError(
        HANDLER_ERROR_CODE,
        "PRECONDITION_FAILED",
        error_details={
            "message": "Missing 'sft_folder'. Provide it in params or configure it in the server session manager.",
            "required": ["sft_folder"],
        },
    )
