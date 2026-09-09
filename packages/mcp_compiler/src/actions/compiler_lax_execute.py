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
from nxp.mcp.compiler.handlers.action_handlers import handle_lax_execute


LAX_EXECUTE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="compiler.lax_execute",
        description=(
            "Execute any LAX toolchain binary (laxcc, it3a-cc, it3a-as, it3a-ld, it3a-ds, ...) "
            "with the given arguments. Use compiler.list_lax_tools first to discover "
            "the available toolchain_bin_dir and binary names. "
            "Optionally provide inline source code via input_code; the temp file is "
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
                        "Absolute path to the LAX toolchain bin directory "
                        "(from compiler.list_lax_tools). "
                        "Example: C:/NXP/S32DS.3.6.7/S32DS/build_tools/LAX/bin"
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
                        "Examples: laxcc, it3a-cc, it3a-as, it3a-ld, it3a-ds"
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
                        "Optional source code to write to a temp file before executing. "
                        "The temp file path is automatically prepended to args."
                    ),
                },
            ),
            ActionParameter(
                name="input_language",
                required=False,
                schema={
                    "type": "string",
                    "description": "Language of input_code: c, c++, or asm. Determines the temp file extension.",
                    "enum": ["c", "c++", "asm"],
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
        ),
        preconditions=("LAX toolchain must be installed and discoverable via compiler.list_lax_tools.",),
        workflow_hints=("Call compiler.list_lax_tools first to obtain toolchain_bin_dir and binary name.",),
        related_actions=("compiler.list_lax_tools",),
        category="lax",
    ),
    handler=handle_lax_execute,
)
