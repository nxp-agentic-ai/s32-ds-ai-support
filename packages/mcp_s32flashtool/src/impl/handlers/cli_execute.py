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

"""Handler that executes a raw S32FlashTool command string via the CLI client."""

from __future__ import annotations

from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError
# Import the module (not the class) so that runtime/test monkeypatching of
# ``s32flashtool_cli.FlashToolClient_CLI`` is honored: the class is resolved via
# attribute lookup at call time rather than bound once at import time.
from nxp.mcp.s32flashtool.impl import s32flashtool_cli
from nxp.mcp.s32flashtool.impl.handlers._common import (
    S32FlashToolSessionManager,
    INVALID_PARAMS_CODE,
    effective_sft_folder,
    logger,
)


__all__ = ["cli_execute_handler"]


async def cli_execute_handler(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """Execute a raw S32FlashTool command string through the CLI client."""

    sft_folder = effective_sft_folder(params, session_manager)
    command = params.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ActionExecutionError(
            INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "'command' must be a non-empty command string.",
                "required": ["command"],
            },
        )

    # Pass the installation folder positionally: the real client accepts it as
    # ``sft_folder`` while test doubles may name it differently.
    ft = s32flashtool_cli.FlashToolClient_CLI(sft_folder, logger=logger)
    result = await ft.run(command)
    return {
        "status": 0,
        "status_text": "OK" if result.get("status") == "ok" else "ERROR",
        "response": result,
    }
