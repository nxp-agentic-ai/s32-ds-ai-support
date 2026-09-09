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
from nxp.mcp.s32debugger.handlers.action_handlers import inspect_debug_processes


INSPECT_DEBUG_PROCESSES_ACTION = ActionExecutable(
    contract=ActionContract(
        name='inspect.debug_processes',
        description=(
            'Discover running S32Debugger-related processes (GDB clients, GTA server, CCS) on the host. '
            'If processes are found but this server has no active managed session tracking them, the '
            'result sets "orphaned_processes": true and includes a "warning" so stale/pre-existing '
            'processes are surfaced before a new debug session is started.'
        ),
        params=(
        ),
        preconditions=(
            'An effective installation path must be configured.',
        ),
        related_actions=(
            'inspect.gdb_server',
            'inspect.gdb_client_status',
        ),
        category='inspect',
    ),
    handler=inspect_debug_processes,
)
