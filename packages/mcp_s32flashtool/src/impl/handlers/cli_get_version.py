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

"""Handler that retrieves the installed S32FlashTool CLI version."""

from __future__ import annotations

from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError
from nxp.mcp.s32flashtool.impl.handlers._common import (
    HANDLER_ERROR_CODE,
    S32FlashToolSessionManager,
    effective_sft_folder,
)

# The version-probe implementation now lives in the shared impl-level utility
# module so handlers and the manifest builder both depend on it (correct
# dependency direction) rather than importing from a handler module. Consumers
# needing ``s32flashtool_get_version_impl`` or ``ToolResult`` should import them
# from ``version_probe`` directly; this handler no longer re-exports them.
from nxp.mcp.s32flashtool.impl.version_probe import s32flashtool_get_version_impl

__all__ = ["cli_get_version_handler"]


async def cli_get_version_handler(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """Return the installed S32FlashTool CLI version string.

    ``sft_folder`` is effectively required even though the schema marks it
    optional: the session manager acts as the fallback source.
    ``effective_sft_folder`` reads ``params["sft_folder"]`` first and falls
    back to the session manager, raising ``ActionExecutionError`` when neither
    supplies a usable folder.
    """
    sft_folder = effective_sft_folder(params, session_manager)

    try:
        res = await s32flashtool_get_version_impl(sft_folder)
        if res["status"] != "ok":
            raise ActionExecutionError(
                HANDLER_ERROR_CODE,
                "EXECUTION_FAILED",
                error_details={
                    "message": f"Failed to retrieve the s32flashtool version: {res['status']}",
                    "sft_folder": sft_folder,
                },
            )
        version = res["data"]
    except ActionExecutionError:
        raise
    except Exception as exc:
        raise ActionExecutionError(
            HANDLER_ERROR_CODE,
            "EXECUTION_FAILED",
            error_details={
                "message": f"Failed to retrieve the s32flashtool version: {exc}",
                "sft_folder": sft_folder,
            },
        ) from exc

    return {
        "status": 0,
        "status_text": "OK",
        "response": {
            "sft_folder": sft_folder,
            "version": version,
        },
    }
