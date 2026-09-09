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

"""Shared utility for probing the installed S32FlashTool CLI version.

This module is the single source of truth for the version-probe implementation.
It lives at the ``impl`` level (not inside a handler module) so that both the
``cli_get_version`` handler and the ``versioning`` manifest builder can import
it without either depending on the other. This keeps the dependency direction
correct: handlers and manifest builders both depend on this utility, never the
other way around.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, Optional

# NOTE: Import TypedDict from typing_extensions rather than typing.
# On Python < 3.12, pydantic (used by FastMCP to build tool schemas) rejects
# typing.TypedDict and raises PydanticUserError. typing_extensions provides a
# backport that pydantic accepts on all supported Python versions.
from typing_extensions import TypedDict

from nxp.mcp.s32flashtool.impl import s32flashtool_cli
from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME

__all__ = ["Status", "ToolResult", "s32flashtool_get_version_impl"]

logger = logging.getLogger(MCP_SERVER_NAME)

Status = Literal["ok", "error", "preview", "blocked"]


class ToolResult(TypedDict, total=False):
    status: Status          # machine-checkable outcome
    exit_code: int          # process/return code (-1 when no process ran)
    message: str            # human-readable summary (prose)
    data: Any               # machine-usable payload (stdout, file list, ...)
    command: str            # previewed/executed command line, when relevant


def _envelope(
    status: Status,
    *,
    exit_code: int = 0,
    message: str = "",
    data: Any = None,
    command: Optional[str] = None,
) -> ToolResult:
    """Build the uniform tool-result envelope as a native dict."""
    result: ToolResult = {"status": status, "exit_code": exit_code}
    if message:
        result["message"] = message
    if data is not None:
        result["data"] = data
    if command is not None:
        result["command"] = command
    return result


async def s32flashtool_get_version_impl(sft_folder: str) -> ToolResult:
    """Get the S32FlashTool version.

    Executes the S32FlashTool CLI executable with the ``-h`` parameter in the
    given folder and returns the first line of its banner output.
    """
    try:
        command = "-h"

        # Pass the installation folder positionally: the real client accepts it
        # as ``sft_folder`` while test doubles may name it differently.
        ft = s32flashtool_cli.FlashToolClient_CLI(sft_folder, logger=logger)
        result = await ft.run(command)

        first_line = result.get("output", "").split("\n")[0]
        exit_code = result.get("exit_code", 0)
        status = result.get("status", "ok")
        # get_version runs the S32FlashTool CLI with the "-h" (help/usage)
        # argument. In that mode the tool prints its version banner (like
        # "S32 Flash Tool 2.4.3. Build 260724. Copyright 2019 - 2026 NXP") on
        # the first line and may exit non-zero (observed exit code 4) simply
        # because no flash operation was requested - it is not a real failure.
        # As long as a version line was captured, normalize BOTH status and
        # exit_code to success so the probe reports "ok". If no output was
        # produced, preserve the original failure signal.
        if first_line:
            status = "ok"
            exit_code = 0
        return _envelope(status, exit_code=exit_code, data=first_line)

    except (OSError, ValueError) as e:
        return _envelope(
            "error",
            exit_code=-1,
            message=f"S32FlashTool is not reachable: {e}",
        )
