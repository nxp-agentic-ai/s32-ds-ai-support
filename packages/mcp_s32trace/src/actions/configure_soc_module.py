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
from nxp.mcp.s32trace.handlers.action_handlers import configure_soc_module


CONFIGURE_SOC_MODULE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.configure_soc_module",
        description=(
            "Apply settings to one SoC module (funnel, replicator, or similar) in an "
            "existing S32Trace config file. Use this to enable or disable a module and "
            "to set its base address and memory space. "
            "module_name must match a block name under SoC Modules in the config "
            "(e.g. 'ARM Funnel 2')."
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
                name="module_name",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Name of the SoC module block to configure, e.g. 'ARM Funnel 2'. "
                        "Use configurator.describe_trace_flow to see available module names."
                    ),
                },
            ),
            ActionParameter(
                name="settings",
                required=True,
                schema={
                    "type": "object",
                    "description": (
                        "Module settings to apply. All keys are optional. "
                        "Supported keys: enabled (bool), module_base_address (str), "
                        "mem_space (str)."
                    ),
                },
            ),
        ),
        category="configurator",
        related_actions=(
            "configurator.describe_trace_flow",
            "configurator.configure_core",
            "configurator.create_from_template",
        ),
    ),
    handler=configure_soc_module,
)
