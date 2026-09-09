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
from nxp.mcp.compiler.handlers.action_handlers import handle_spt_execute


SPT_EXECUTE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="compiler.spt_execute",
        description=(
            "Execute any SPT3.8 toolchain binary (as-spt, objdump-spt, ...) "
            "with the given arguments. Use compiler.list_spt_tools first to discover "
            "the available toolchain_bin_dir and binary names. "
            "SPT3.8 only accepts SPT assembly source; there is no C/C++ compiler. "
            "Optionally provide inline SPT assembly source via input_code; "
            "the temp file is always written with a .spt extension and its path is "
            "automatically prepended to args. Each call runs in its own working directory "
            "so always use the returned artifact_path (absolute) when chaining calls."
        ),
        params=(
            ActionParameter(
                name="toolchain_bin_dir",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Absolute path to the SPT3.8 toolchain bin directory "
                        "(from compiler.list_spt_tools). "
                        "Example: C:/NXP/S32DS.3.6.7/S32DS/build_tools/SPT3.8/bin"
                    ),
                },
            ),
            ActionParameter(
                name="binary",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Binary name to run. "
                        "Examples: as-spt, objdump-spt"
                    ),
                },
            ),
            ActionParameter(
                name="args",
                required=True,
                schema={
                    "type": "string",
                    "description": "Arguments to pass to the binary.",
                },
            ),
            ActionParameter(
                name="input_code",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Optional SPT3.8 assembly source to write to a temp file before executing. "
                        "Always written with a .spt extension. "
                        "The temp file path is automatically prepended to args."
                    ),
                },
            ),
            ActionParameter(
                name="input_language",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Ignored for SPT3.8 - kept for API parity with GCC/LAX tools. "
                        "The temp file is always .spt regardless of this value."
                    ),
                    "default": "c",
                },
            ),
            ActionParameter(
                name="save_output",
                required=False,
                schema={
                    "type": "boolean",
                    "description": "If true, save stdout/stderr/command to the output directory.",
                    "default": True,
                },
            ),
            ActionParameter(
                name="timeout_sec",
                required=False,
                schema={
                    "type": "integer",
                    "description": "Seconds before the SPT3.8 assembler process is killed.",
                    "default": 120,
                },
            ),
        ),
        preconditions=("SPT3.8 toolchain must be installed and discoverable via compiler.list_spt_tools.",),
        workflow_hints=("Call compiler.list_spt_tools first to obtain toolchain_bin_dir and binary name.",),
        related_actions=("compiler.list_spt_tools",),
        category="spt",
    ),
    handler=handle_spt_execute,
)
