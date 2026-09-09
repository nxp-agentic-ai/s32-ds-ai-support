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

"""Handler that launches the S32FlashTool GUI (Eclipse RCP)."""

from __future__ import annotations

from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError
from nxp.mcp.s32flashtool.impl.rpc_client import ApiClientLauncher
from nxp.mcp.s32flashtool.impl.rpc_client.rpc_client import DEFAULT_RPC_PORT
from nxp.mcp.s32flashtool.impl.handlers._common import (
    S32FlashToolSessionManager,
    HANDLER_ERROR_CODE,
    INVALID_PARAMS_CODE,
    effective_sft_folder,
)

__all__ = ["local_api_command_handler"]


async def local_api_command_handler(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """Launch the S32FlashTool GUI (Eclipse RCP).

    The action to invoke is carried in the structured ``api_request`` object as
    ``api_request.action``. Only the ``launch`` action is supported; it starts
    the GUI executable from the installation folder (top-level ``sft_folder``
    param, falling back to the server session manager).
    """

    api_request = params.get("api_request")
    if not isinstance(api_request, dict):
        raise ActionExecutionError(
            INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "'api_request' must be an object containing an 'action'.",
                "required": ["api_request"],
            },
        )

    action = api_request.get("action")
    if not isinstance(action, str) or not action.strip():
        raise ActionExecutionError(
            INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "'api_request.action' must be a non-empty string.",
                "required": ["api_request.action"],
            },
        )

    if action != "launch":
        raise ActionExecutionError(
            HANDLER_ERROR_CODE,
            "METHOD_NOT_SUPPORTED",
            error_details={
                "message": (
                    f"Action '{action}' is not supported. "
                    "Use 'gui_launch' to launch the GUI."
                ),
                "action": action,
                "supported_actions": ["launch"],
            },
        )

    sft_folder = effective_sft_folder(params, session_manager)

    # Resolve the host/port used to probe for an already-running GUI. The port
    # falls back to the session manager's configured GUI port, then to the
    # S32FlashTool default RPC port, so the probe works even when the caller
    # omits it.
    host = params.get("host")
    if not isinstance(host, str) or not host.strip():
        host = "localhost"

    port = params.get("port")
    if not isinstance(port, int):
        port = getattr(session_manager, "gui_port", None) if session_manager else None
    if not isinstance(port, int):
        port = DEFAULT_RPC_PORT

    client = ApiClientLauncher(s32flashtool_folder=sft_folder)
    result = client.launch_gui(host=host, port=port)

    ok = result.get("status") == "ok"
    return {
        "status": 0 if ok else 1,
        "status_text": "OK" if ok else "ERROR",
        "response": result,
    }
