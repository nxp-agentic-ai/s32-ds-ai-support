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
from nxp.mcp.s32debugger.handlers.action_handlers import control_command


CONTROL_COMMAND_ACTION = ActionExecutable(
    contract=ActionContract(
        name='control.command',
        description='Execute a GDB command on a running GDB client through its interactive JSON-RPC bridge and return the response.',

        params=(
            ActionParameter(
                name='gdb_client_id',
                required=True,
                schema={'description': 'Identifier of the GDB client whose bridge should execute the command.',
                        'minLength': 1,
                        'type': 'string'},
            ),
            ActionParameter(
                name='command',
                required=True,
                schema={'description': 'GDB command to execute through the bridge.',
                        'minLength': 1,
                        'type': 'string'},
            ),
        ),
        preconditions=(
            'An effective installation path must be configured.',
            'The GDB client must be running with an active JSON-RPC bridge.',
        ),
        related_actions=(
            'control.interrupt',
            'control.transcript',
            'control.start_gdb',
        ),
        category='control',
    ),
    handler=control_command,
)
