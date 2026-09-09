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

"""Canonical public manifest for S32FlashTool action executables.

Each action is authored as an explicit ``ActionExecutable`` in its own module
(the direct-executable pattern used by the S32FlashTool component). This module
collects them into the canonical ``STATIC_ACTIONS`` tuple used to build the active
component action catalog. Individual action constants remain module-level
implementation details.
"""

from .cli_execute import CLI_EXECUTE_ACTION
from .cli_build_all import *
from .list_platform_files import LIST_PLATFORM_FILES_ACTION
from .gui_launch_actions import GUI_LAUNCH_ACTIONS
from .cli_get_version import CLI_GET_VERSION_ACTION
from .mcp_get_version import GET_MCP_VERSION_ACTION

STATIC_ACTIONS = (
    CLI_EXECUTE_ACTION,
    CLI_BUILD_PING_ACTION,
    CLI_BUILD_MCUID_ACTION,
    CLI_BUILD_FID_ACTION,
    CLI_BUILD_FREAD_ACTION,
    CLI_BUILD_FWRITE_ACTION,
    CLI_BUILD_FERASE_ACTION,
    CLI_BUILD_FPROGRAM_ACTION,
    CLI_BUILD_FVERIFY_ACTION,
    CLI_BUILD_BOOT_ACTION,
    CLI_BUILD_DCD_ACTION,
    CLI_BUILD_FCRC_ACTION,
    CLI_BUILD_LIST_INTERFACES_ACTION,
    LIST_PLATFORM_FILES_ACTION,
    CLI_GET_VERSION_ACTION,
    GET_MCP_VERSION_ACTION,
    *GUI_LAUNCH_ACTIONS,
)

__all__ = ["STATIC_ACTIONS"]
