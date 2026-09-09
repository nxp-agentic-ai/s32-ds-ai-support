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

from nxp.mcp.shared import ActionContract, ActionParameter
from nxp.mcp.shared import ActionExecutable
from nxp.mcp.s32debugger.handlers.action_handlers import control_run_ccs_tcl


CONTROL_RUN_CCS_TCL_ACTION = ActionExecutable(
    contract=ActionContract(
        name='control.run_ccs_tcl',
        description='Run a TCL script through the CCS executable (ccs.exe on Windows, ccs on Linux) as "<ccs> -script <tcl_script_path>" and capture its console (puts/display) output. The CCS executable is resolved relative to the effective installation path. The invocation is OS-aware: on Windows ccs.exe is a GUI-subsystem binary, so the script is run via "-script" with console output captured to a temp file; on Linux the script is piped into "ccs -nogfx" and stdout is captured directly. Both paths are bounded by a timeout so a stuck CCS process cannot block forever.',
        params=(
            ActionParameter(
                name='tcl_script_path',
                required=True,
                schema={'description': 'Absolute path to the .tcl script to execute via CCS.',
                         'minLength': 1,
                         'type': 'string'},
            ),
        ),
        preconditions=(
            'An effective installation path must be configured.',
        ),
        related_actions=(
            'control.start_gdb',
        ),
        category='control',
    ),
    handler=control_run_ccs_tcl,
)
