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
from nxp.mcp.s32debugger.handlers.action_handlers import control_start_gdb


CONTROL_START_GDB_ACTION = ActionExecutable(
    contract=ActionContract(
        name='control.start_gdb',
        description='Start one interactive GDB client (with embedded JSON-RPC bridge) for a single-core or multicore S32Debugger session. Auto-starts the GTA server if it is not running.',
        params=(
            ActionParameter(
                name='gdb_client_id',
                required=True,
                schema={'description': 'Unique identifier to register this GDB client under.',
                        'minLength': 1,
                        'type': 'string'},
            ),
            ActionParameter(
                name='gdb_path',
                required=True,
                schema={'description': 'Absolute path to the GDB executable to launch.',
                        'minLength': 1,
                        'type': 'string'},
            ),
            ActionParameter(
                name='config_file',
                required=True,
                schema={'description': 'Path to the GDB configuration file (must embed the JSON-RPC bridge port).',
                        'minLength': 1,
                        'type': 'string'},
            ),
        ),
        preconditions=(
            'An effective installation path must be configured.',
        ),
        workflow_hints=(
            'Typical flow: generate.gdb_config_file -> control.start_gdb -> control.command.',
        ),
        related_actions=(
            'generate.gdb_config_file',
            'control.command',
            'control.stop_gdb',
        ),
        category='control',
    ),
    handler=control_start_gdb,
)
