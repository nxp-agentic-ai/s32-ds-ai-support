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
from nxp.mcp.s32debugger.handlers.action_handlers import inspect_installed_gdbs


INSPECT_INSTALLED_GDBS_ACTION = ActionExecutable(
    contract=ActionContract(
        name='inspect.installed_gdbs',
        description='List the GDB executables available in the configured installation, one per known architecture variant.',
        params=(
        ),
        preconditions=(
            'An effective installation path must be configured.',
        ),
        related_actions=(
            'control.start_gdb',
        ),
        category='inspect',
    ),
    handler=inspect_installed_gdbs,
)
