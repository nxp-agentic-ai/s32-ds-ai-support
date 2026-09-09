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
from nxp.mcp.s32trace.handlers.action_handlers import create_from_template


CREATE_FROM_TEMPLATE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.create_from_template",
        description=(
            "Clone an S32Trace configurator template to a new config file without "
            "applying any edits. Returns the path of the created file so subsequent "
            "configurator actions can operate on it.\n\n"
            "Use configurator.list_templates first to discover the available templates "
            "and their paths."
        ),
        params=(
            ActionParameter(
                name="template_path",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Absolute path to a TEMPLATE*.xml file "
                        "(from configurator.list_templates)."
                    ),
                },
            ),
            ActionParameter(
                name="output_path",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Absolute destination path for the new config file. "
                        "When omitted the file is written to the platformConfig "
                        "directory of the newest S32DS workspace."
                    ),
                },
            ),
        ),
        category="configurator",
        workflow_hints=(
            "Call this action after configurator.list_templates to obtain a config "
            "file path, then pass that path to the configurator.configure_* or "
            "configurator.set_* actions.",
        ),
        related_actions=(
            "configurator.list_templates",
            "configurator.set_output_folder",
            "configurator.set_target_access",
            "configurator.configure_core",
            "configurator.configure_sink",
            "configurator.configure_data_streams",
        ),
    ),
    handler=create_from_template,
)
