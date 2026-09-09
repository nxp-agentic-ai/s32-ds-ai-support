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

"""Handler that builds an S32FlashTool CLI command string from a cli_request."""

from __future__ import annotations

from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError
from nxp.mcp.s32flashtool.impl.s32flashtool_cli_builder import (
    build_s32flashtool_command_string,
)
from nxp.mcp.s32flashtool.impl.handlers._common import (
    S32FlashToolSessionManager,
    INVALID_PARAMS_CODE,
    effective_sft_folder,
)


__all__ = ["cli_build_command_handler"]


async def cli_build_command_handler(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """Build an S32FlashTool CLI command string from a structured cli_request."""

    sft_folder = effective_sft_folder(params, session_manager)
    cli_request = params.get("cli_request")

    if not isinstance(cli_request, dict):
        raise ActionExecutionError(
            INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "'cli_request' must be an object containing an 'operation' and its 'input' payload.",
                "required": ["cli_request"],
            },
        )

    payload = {
        "action": "cli_build_command",
        "msg_id": params.get("msg_id", "1"),
        "input": {
            "sft_folder": sft_folder,
            "cli_request": cli_request,
        },
    }

    try:
        command_string = build_s32flashtool_command_string(payload)
    except Exception as exc:
        raise ActionExecutionError(
            INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": f"Failed to build S32FlashTool command: {exc}",
                "operation": cli_request.get("operation"),
            },
        ) from exc

    return {
        "status": 0,
        "status_text": "OK",
        "response": {
            "command": command_string,
            "sft_folder": sft_folder,
            "operation": cli_request.get("operation"),
        },
    }
