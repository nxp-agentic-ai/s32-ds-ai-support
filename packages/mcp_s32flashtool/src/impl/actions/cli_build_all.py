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

from nxp.mcp.s32flashtool.impl.actions._cli_build_factory import make_cli_build_action

# Explicit public manifest so `from .cli_build_all import *` exports only the
# generated action constants and does not leak the `make_cli_build_action`
# factory (or any future imports) into the importing namespace.
__all__ = [
    "CLI_BUILD_BOOT_ACTION",
    "CLI_BUILD_DCD_ACTION",
    "CLI_BUILD_FCRC_ACTION",
    "CLI_BUILD_FERASE_ACTION",
    "CLI_BUILD_FID_ACTION",
    "CLI_BUILD_FPROGRAM_ACTION",
    "CLI_BUILD_FREAD_ACTION",
    "CLI_BUILD_FVERIFY_ACTION",
    "CLI_BUILD_FWRITE_ACTION",
    "CLI_BUILD_MCUID_ACTION",
    "CLI_BUILD_PING_ACTION",
    "CLI_BUILD_LIST_INTERFACES_ACTION",
]


CLI_BUILD_BOOT_ACTION = make_cli_build_action("boot_cli")
CLI_BUILD_DCD_ACTION = make_cli_build_action("dcd_cli")
CLI_BUILD_FCRC_ACTION = make_cli_build_action("fcrc_cli")
CLI_BUILD_FERASE_ACTION = make_cli_build_action("ferase_cli")
CLI_BUILD_FID_ACTION = make_cli_build_action("fid_cli")
CLI_BUILD_FPROGRAM_ACTION = make_cli_build_action("fprogram_cli")
CLI_BUILD_FREAD_ACTION = make_cli_build_action("fread_cli")
CLI_BUILD_FVERIFY_ACTION = make_cli_build_action("fverify_cli")
CLI_BUILD_FWRITE_ACTION = make_cli_build_action("fwrite_cli")
CLI_BUILD_MCUID_ACTION = make_cli_build_action("mcuid_cli")
CLI_BUILD_PING_ACTION = make_cli_build_action("ping_cli")
CLI_BUILD_LIST_INTERFACES_ACTION = make_cli_build_action("list_interfaces_cli")
