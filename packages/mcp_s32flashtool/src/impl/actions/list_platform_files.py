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

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter
from nxp.mcp.s32flashtool.impl.handlers import list_platform_files_handler


__all__ = ["LIST_PLATFORM_FILES_ACTION"]


LIST_PLATFORM_FILES_ACTION = ActionExecutable(
    contract=ActionContract(
        name="list_platform_files",
        description=(
            "Discover installation content: target binaries, flash algorithms, "
            "supported-device docs, example blobs, and example PDFs. Use this "
            "before flash operations to find valid target/algorithm paths."
        ),
        params=(
            ActionParameter(
                name="sft_folder",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Absolute path to the S32FlashTool installation root. "
                        "Falls back to the server runtime context when omitted."
                    ),
                },
            ),
            ActionParameter(
                name="bin_type",
                required=True,
                schema={
                    "type": "string",
                    "enum": ["target", "flash", "supported", "blob", "example_pdf"],
                    "description": (
                        "Which installation content to list: 'target' (targets/*.bin), "
                        "'flash' (flash/*.bin algorithms), 'supported' (supported_*.txt device docs), "
                        "'blob' (example blob binaries), 'example_pdf' (example board PDFs)."
                    ),
                },
            ),
            ActionParameter(
                name="filter",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Optional case-insensitive substring filter applied to each entry "
                        "after the list is built. Only entries whose string form contains "
                        "the given text are kept. When omitted or empty, no filtering is applied."
                    ),
                },
            ),
        ),
        preconditions=(
            "An installation root must be resolvable (params.sft_folder, or the server runtime context).",
        ),
        related_actions=(
            "cli_build_ping",
            "cli_build_fprogram",
        ),
        category="discovery",
    ),
    handler=list_platform_files_handler,
)
