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
from nxp.mcp.s32debugger.handlers.action_handlers import control_set_installation_path


CONTROL_SET_INSTALLATION_PATH_ACTION = ActionExecutable(
    contract=ActionContract(
        name='control.set_installation_path',
        description='Set or replace the runtime S32Debugger installation path after validating the expected folder layout.',
        params=(
        ActionParameter(
            name='installation_path',
            required=True,
            schema={'description': 'Absolute S32Debugger installation root path.',
                     'minLength': 1,
                     'type': 'string'},
        ),
        ),
        example={'params': {'installation_path': 'C:/NXP/S32DBG.3.6.8'}},
        workflow_hints=(
            'Call this first when settings.installation_path is not configured in the server YAML.',
        ),
        related_actions=(
            'control.get_installation_path',
            'inspect.installation',
        ),
        category='control',
    ),
    handler=control_set_installation_path,
)




