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
from nxp.mcp.s32debugger.handlers.action_handlers import inspect_installation_path


INSPECT_INSTALLATION_PATH_ACTION = ActionExecutable(
    contract=ActionContract(
        name='inspect.installation_path',
        description='Inspect the configured, runtime, and effective installation path state without requiring an active installation.',
        params=(
        ),
        related_actions=(
            'control.set_installation_path',
        ),
        category='inspect',
    ),
    handler=inspect_installation_path,
)
