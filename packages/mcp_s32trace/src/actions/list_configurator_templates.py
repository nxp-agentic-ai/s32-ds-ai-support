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
from nxp.mcp.s32trace.handlers.action_handlers import list_configurator_templates


LIST_CONFIGURATOR_TEMPLATES_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.list_templates",
        description=(
            "List all S32Trace configurator template XML files available in the "
            "S32 Design Studio installation. Each entry shows the board/SoC name, "
            "the absolute path to the template, a short description, and the UI "
            "names of the cores that can be traced (e.g. M7_0, M7_RFE_1).\n\n"
            "Use this action FIRST to discover which board template matches the "
            "target hardware before calling configurator.create_trace_configuration "
            "or configurator.describe_trace_flow."
        ),
        params=(
            ActionParameter(
                name="s32ds_installation_path",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Absolute path to the S32 Design Studio installation root "
                        "(e.g. C:/NXP/S32DS.3.6.9 or /usr/local/NXP/S32DS.3.6.9). "
                        "Optional -- when omitted the server uses the path resolved at "
                        "startup from the YAML config or from auto-discovery."
                    ),
                },
            ),
        ),
        category="configurator",
        workflow_hints=(
            "Call this action first to obtain template_path and the list of valid core UI names.",
        ),
        related_actions=(
            "configurator.describe_trace_flow",
            "configurator.inspect_template",
            "configurator.create_from_template",
        ),
    ),
    handler=list_configurator_templates,
)
