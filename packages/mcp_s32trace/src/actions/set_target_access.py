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
from nxp.mcp.s32trace.handlers.action_handlers import set_target_access


SET_TARGET_ACCESS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.set_target_access",
        description=(
            "Configure the Target Access block in an existing S32Trace config file. "
            "This sets the GTA/CCS server address, port, launch name, and related "
            "connection settings used when the configurator connects to the target."
        ),
        params=(
            ActionParameter(
                name="config_path",
                required=True,
                schema={
                    "type": "string",
                    "description": "Absolute path to the config XML file to edit.",
                },
            ),
            ActionParameter(
                name="settings",
                required=True,
                schema={
                    "type": "object",
                    "description": (
                        "Target Access settings to apply. All keys are optional. "
                        "Supported keys: server_address (str), server_port (str), "
                        "launch_name (str), target_access_method (str), "
                        "reset_before_config (bool), sync_server_port (bool), "
                        "enable_user_code (bool), endianness (str)."
                    ),
                },
            ),
        ),
        category="configurator",
        related_actions=(
            "configurator.create_from_template",
            "configurator.describe_trace_flow",
        ),
    ),
    handler=set_target_access,
)
