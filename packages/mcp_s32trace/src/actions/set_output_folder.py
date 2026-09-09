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
from nxp.mcp.s32trace.handlers.action_handlers import set_output_folder


SET_OUTPUT_FOLDER_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.set_output_folder",
        description=(
            "Set the output folder where S32Trace will write captured trace data. "
            "This edits the Results > Output Folder attribute in an existing config file."
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
                name="output_folder",
                required=True,
                schema={
                    "type": "string",
                    "description": "Absolute path to the folder where trace results will be saved.",
                },
            ),
        ),
        category="configurator",
        related_actions=(
            "configurator.create_from_template",
            "configurator.describe_trace_flow",
        ),
    ),
    handler=set_output_folder,
)
