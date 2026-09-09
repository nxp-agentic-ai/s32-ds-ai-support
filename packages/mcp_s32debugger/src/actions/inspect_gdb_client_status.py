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
from nxp.mcp.s32debugger.handlers.action_handlers import inspect_gdb_client_status


INSPECT_GDB_CLIENT_STATUS_ACTION = ActionExecutable(
    contract=ActionContract(
        name='inspect.gdb_client_status',
        description='Report the status of a single registered GDB client, including its PID, bridge port, and running state.',
        params=(
        ActionParameter(
            name='gdb_client_id',
            required=True,
            schema={'description': 'Identifier of the GDB client to inspect.',
                     'minLength': 1,
                     'type': 'string'},
        ),
        ),
        preconditions=(
            'An effective installation path must be configured.',
        ),
        related_actions=(
            'inspect.gdb_server',
            'inspect.debug_processes',
        ),
        category='inspect',
    ),
    handler=inspect_gdb_client_status,
)
