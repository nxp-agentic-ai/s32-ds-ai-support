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

"""Handler that returns the S32 Flash Tool MCP version manifest."""

from __future__ import annotations

from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError
from nxp.mcp.s32flashtool.impl.handlers.versioning import build_version_manifest
from nxp.mcp.s32flashtool.impl.handlers._common import (
    S32FlashToolSessionManager,
    HANDLER_ERROR_CODE,
)

__all__ = ["get_mcp_version_handler"]


async def get_mcp_version_handler(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """Return the S32 Flash Tool MCP version manifest as structured JSON.

    The manifest carries mcp_server_name, mcp_server_version and
    target_tool_version. When an installation root is provided via the
    ``sft_folder`` param, the locally installed S32 Flash Tool version is also
    detected; if it differs from ``target_tool_version`` a warning is logged and
    documentation is preferentially served from the installed tool's local docs
    directory.

    Unlike ``cli_get_version_handler`` this handler never fails when no
    installation is configured: the manifest is still returned, only the
    ``installed_tool`` detection is skipped.

    Note: Unlike ``cli_get_version_handler``, this handler intentionally does
    NOT fall back to the session manager for the installation path. Installed-
    tool detection requires an explicit ``sft_folder`` param. This is by design:
    get_mcp_version_handler is a lightweight status check that must always return the
    manifest and should never block on, or implicitly depend on, a configured
    installation.
    """

    sft_folder = params.get("sft_folder")
    if not (isinstance(sft_folder, str) and sft_folder.strip()):
        sft_folder = None

    try:
        manifest = await build_version_manifest(sft_folder)
    except ActionExecutionError:
        raise
    except Exception as exc:
        raise ActionExecutionError(
            HANDLER_ERROR_CODE,
            "EXECUTION_FAILED",
            error_details={
                "message": f"Failed to build the S32FlashTool MCP version manifest: {exc}",
                "sft_folder": sft_folder,
            },
        ) from exc

    return {
        "status": 0,
        "status_text": "OK",
        "response": manifest.to_dict(),
    }
