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
from nxp.mcp.compiler.handlers.action_handlers import handle_lax_simulator_execute


LAX_SIMULATOR_EXECUTE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="compiler.lax_simulator_execute",
        description=(
            "Execute a LAX simulator binary (typically runsim) on a compiled LAX "
            "executable (.eld file). Simulator flags (device model, verbosity, tracing, "
            "output redirection) go in args before the .eld; the resolved .eld path is "
            "appended automatically when executable_file is provided. "
            "Use compiler.list_lax_simulator_tools first to confirm runsim is present. "
            "Only .eld files (linked LAX executables produced by laxcc) are accepted."
        ),
        params=(
            ActionParameter(
                name="binary",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Simulator binary to run. "
                        "Examples: runsim, ccssim2"
                    ),
                },
            ),
            ActionParameter(
                name="args",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Simulator flags to pass before the .eld file. "
                        "Examples: '-d vspa3_16au -t', '-d vspa3_64au -showregs', "
                        "'-d vspa3_16au -redir sim_stdout.txt'. "
                        "Always specify a device with -d vspa3_{2,16,64}au for reproducible results."
                    ),
                },
            ),
            ActionParameter(
                name="executable_file",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Path to the compiled LAX .eld file to run. "
                        "Relative paths are resolved against the S32DS base directory. "
                        "Must end with .eld - object files (.eln), source (.c, .sl), "
                        "or any other extension are not accepted."
                    ),
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
        preconditions=(
            "LAX Simulator must be installed (compiler.list_lax_simulator_tools confirms runsim is present).",
            "executable_file must be a linked LAX executable with .eld extension.",
        ),
        workflow_hints=(
            "Call compiler.list_lax_simulator_tools first to confirm runsim is present.",
            "Always pass -d vspa3_{2,16,64}au to select a device model explicitly.",
            "Use -t to get cycle counts, -showpc for program flow, -showregs for register trace.",
        ),
        related_actions=("compiler.list_lax_simulator_tools", "compiler.lax_execute"),
        category="lax_simulator",
    ),
    handler=handle_lax_simulator_execute,
)
