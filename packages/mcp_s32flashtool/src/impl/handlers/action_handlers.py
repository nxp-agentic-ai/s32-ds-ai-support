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

"""Component-local action handlers for the S32FlashTool search-first surface.

These handlers follow the shared action mechanism from ``nxp.mcp.shared.action``:
each handler receives a validated ``params`` object and an optional component
``session_manager``, and returns a plain result payload. Business logic (CLI
string building and process execution) stays local to this component; the shared
layer only provides validation, dispatch, search, and outcome shaping.

Handler signatures follow the shared contract: ``handler(params)`` or
``handler(params, session_manager)``. The dispatcher inspects the handler
arity and supplies the ``session_manager`` when the handler accepts it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError
from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32flashtool.impl.s32flashtool_cli import FlashToolClient_CLI
from nxp.mcp.s32flashtool.impl.s32flashtool_cli_builder import (
    build_s32flashtool_command_string,
)
from nxp.mcp.s32flashtool.impl.rest_client import RestClient



logger = logging.getLogger(MCP_SERVER_NAME)

# Protocol-facing error codes (aligned with the shared JSON-RPC error model).
# INVALID_PARAMS mirrors the JSON-RPC invalid-params code; the remaining
# handler/precondition/execution errors reuse a component handler code.
_INVALID_PARAMS_CODE = -32602
_HANDLER_ERROR_CODE = -32002


@dataclass(frozen=True)
class S32FlashToolSessionManager:
    """Optional runtime state for S32FlashTool action handlers.

    Lets the server pre-configure an installation folder and a GUI REST port so
    agents do not have to repeat them on every call. It is passed to handlers as
    the ``session_manager`` argument by the shared dispatcher.
    """

    sft_folder: Optional[str] = None
    gui_port: Optional[int] = None


def _effective_sft_folder(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> str:
    sft_folder = params.get("sft_folder")
    if isinstance(sft_folder, str) and sft_folder.strip():
        return sft_folder
    if (
        session_manager is not None
        and isinstance(session_manager.sft_folder, str)
        and session_manager.sft_folder.strip()
    ):
        return session_manager.sft_folder
    raise ActionExecutionError(
        _HANDLER_ERROR_CODE,
        "PRECONDITION_FAILED",
        error_details={
            "message": "Missing 'sft_folder'. Provide it in params or configure it in the server session manager.",
            "required": ["sft_folder"],
        },
    )


async def cli_execute(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """Execute a raw S32FlashTool command string through the CLI client."""

    sft_folder = _effective_sft_folder(params, session_manager)
    command = params.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ActionExecutionError(
            _INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "'command' must be a non-empty command string.",
                "required": ["command"],
            },
        )

    ft = FlashToolClient_CLI(base_folder=sft_folder, logger=logger)
    result = await ft.run(command)
    return {
        "status": 0,
        "status_text": "OK" if result.get("status") == "ok" else "ERROR",
        "response": result,
    }


async def cli_build_command(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """Build an S32FlashTool CLI command string from a structured cli_request."""

    sft_folder = _effective_sft_folder(params, session_manager)
    cli_request = params.get("cli_request")
    if not isinstance(cli_request, dict):
        raise ActionExecutionError(
            _INVALID_PARAMS_CODE,
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
            _INVALID_PARAMS_CODE,
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


async def list_platform_files(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """List installation content (targets, flash algorithms, supported-device docs, etc.).

    Mirrors the ``s32flashtool_list_available_platform_files`` tool: given the
    installation root (params.base_folder or params.sft_folder, falling back to
    the session manager) and a ``bin_type``, return absolute paths / structured
    entries discovered under the installation.
    """

    from nxp.mcp.s32flashtool.impl.s32flashtool_utils import (
        list_available_supported_devices_text_files,
        list_available_test_blob_binaries,
        list_files_by_extension,
        list_pdfs_with_platform,
    )

    base_folder = params.get("base_folder")
    if not (isinstance(base_folder, str) and base_folder.strip()):
        base_folder = _effective_sft_folder(params, session_manager)

    bin_type = params.get("bin_type")
    if not isinstance(bin_type, str) or not bin_type.strip():
        raise ActionExecutionError(
            _INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "'bin_type' must be one of: target, flash, supported, blob, example_pdf.",
                "required": ["bin_type"],
            },
        )

    try:
        if bin_type == "target":
            data = list_files_by_extension(base_folder, subfolder="targets", extension=".bin")
        elif bin_type == "flash":
            data = list_files_by_extension(base_folder, subfolder="flash", extension=".bin")
        elif bin_type == "blob":
            data = list_available_test_blob_binaries(str(Path(base_folder) / "examples"))
        elif bin_type == "example_pdf":
            data = list_pdfs_with_platform(str(Path(base_folder) / "examples"))
        elif bin_type == "supported":
            data = list_available_supported_devices_text_files(base_folder)
        else:
            raise ActionExecutionError(
                _INVALID_PARAMS_CODE,
                "INVALID_PARAMS",
                error_details={
                    "message": f"Unrecognized bin_type: {bin_type}",
                    "bin_type": bin_type,
                },
            )
    except ActionExecutionError:
        raise
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "EXECUTION_FAILED",
            error_details={
                "message": f"Failed to list platform files: {exc}",
                "bin_type": bin_type,
                "base_folder": base_folder,
            },
        ) from exc

    # Optional case-insensitive substring filter over the built list.
    # Applied after the list is created; empty/missing filter -> no-op.
    filter_text = params.get("filter")
    active_filter = None
    if isinstance(filter_text, str) and filter_text.strip() and isinstance(data, list):
        active_filter = filter_text.strip()
        needle = active_filter.lower()
        data = [entry for entry in data if needle in str(entry).lower()]

    return {
        "status": 0,
        "status_text": "OK",
        "response": {
            "base_folder": base_folder,
            "bin_type": bin_type,
            "filter": active_filter,
            "entries": data,
            "count": len(data) if isinstance(data, list) else None,
        },
    }

async def rest_api_command(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """Launch the S32FlashTool GUI (Eclipse RCP).

    The action to invoke is carried in the structured ``rest_request`` object as
    ``rest_request.action``. Only the ``launch`` action is supported; it starts
    the GUI executable from the installation folder (top-level ``sft_folder``
    param, falling back to the server session manager).
    """

    rest_request = params.get("rest_request")
    if not isinstance(rest_request, dict):
        raise ActionExecutionError(
            _INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "'rest_request' must be an object containing an 'action'.",
                "required": ["rest_request"],
            },
        )

    action = rest_request.get("action")
    if not isinstance(action, str) or not action.strip():
        raise ActionExecutionError(
            _INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "'rest_request.action' must be a non-empty string.",
                "required": ["rest_request.action"],
            },
        )

    if action != "launch":
        raise ActionExecutionError(
            _INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "Only the 'launch' action is supported by this handler.",
                "action": action,
            },
        )


    sft_folder = _effective_sft_folder(params, session_manager)

    client = RestClient(s32flashtool_folder=sft_folder)
    result = client.launch_gui()

    ok = result.get("status") == "ok"
    return {
        "status": 0 if ok else 1,
        "status_text": "OK" if ok else "ERROR",
        "response": result,
    }



