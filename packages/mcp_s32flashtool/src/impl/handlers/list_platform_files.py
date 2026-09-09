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

"""Handler that lists installation content (targets, flash algorithms, docs, etc.)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError
from nxp.mcp.s32flashtool.impl.handlers._common import (
    S32FlashToolSessionManager,
    HANDLER_ERROR_CODE,
    INVALID_PARAMS_CODE,
    effective_sft_folder,
)


__all__ = ["list_platform_files_handler"]


async def list_platform_files_handler(
    params: dict[str, Any],
    session_manager: Optional[S32FlashToolSessionManager] = None,
) -> Any:
    """List installation content (targets, flash algorithms, supported-device docs, etc.).

    Mirrors the ``s32flashtool_list_available_platform_files`` tool: given the
    installation root (params.sft_folder, falling back to
    the session manager) and a ``bin_type``, return absolute paths / structured
    entries discovered under the installation.
    """

    from nxp.mcp.s32flashtool.impl.s32flashtool_utils import (
        list_available_supported_devices_text_files,
        list_available_test_blob_binaries,
        list_files_by_extension,
        list_pdfs_with_platform,
    )

    base_folder = params.get("sft_folder")
    if not (isinstance(base_folder, str) and base_folder.strip()):
        base_folder = effective_sft_folder(params, session_manager)

    bin_type = params.get("bin_type")
    if not isinstance(bin_type, str) or not bin_type.strip():
        raise ActionExecutionError(
            INVALID_PARAMS_CODE,
            "INVALID_PARAMS",
            error_details={
                "message": "'bin_type' must be one of: target, flash, supported, blob, example_pdf.",
                "required": ["bin_type"],
                "sft_folder": base_folder,
            },
        )

    try:
        if bin_type == "target":
            data = list_files_by_extension(base_folder, subfolder="targets", extension=".bin")
        elif bin_type == "flash":
            data = list_files_by_extension(base_folder, subfolder="flash", extension=".bin")
        elif bin_type == "blob":
            examples_dir = str(Path(base_folder) / "examples")
            data = list_available_test_blob_binaries(examples_dir)
        elif bin_type == "example_pdf":
            examples_dir = str(Path(base_folder) / "examples")
            data = list_pdfs_with_platform(examples_dir)
        elif bin_type == "supported":
            data = list_available_supported_devices_text_files(base_folder)
        else:
            raise ActionExecutionError(
                INVALID_PARAMS_CODE,
                "INVALID_PARAMS",
                error_details={
                    "message": f"Unrecognized bin_type: {bin_type}",
                    "bin_type": bin_type,
                    "sft_folder": base_folder,
                },
            )
    except ActionExecutionError:
        raise
    except Exception as exc:
        raise ActionExecutionError(
            HANDLER_ERROR_CODE,
            "EXECUTION_FAILED",
            error_details={
                "message": f"Failed to list platform files: {exc}",
                "bin_type": bin_type,
                "sft_folder": base_folder,
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
            "sft_folder": base_folder,
            "bin_type": bin_type,
            "filter": active_filter,
            "entries": data,
            "count": len(data) if isinstance(data, list) else None,
        },
    }
