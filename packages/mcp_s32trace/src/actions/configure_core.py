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
from nxp.mcp.s32trace.handlers.action_handlers import configure_core


CONFIGURE_CORE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.configure_core",
        description=(
            "Apply settings to one trace generator core in an existing S32Trace config "
            "file. Use this to enable or disable a core, set its trace scenario "
            "(e.g. ProgramTrace, DataValue), toggle timestamps and cycle counting, "
            "set ELF image paths, and configure the core's base address. "
            "core_name must match the UI Name shown by configurator.describe_trace_flow "
            "(e.g. 'M7_0', 'M7_1', 'A53_0')."
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
                name="core_name",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "UI name of the core to configure, e.g. 'M7_0' or 'A53_0'. "
                        "Use configurator.list_templates or configurator.describe_trace_flow "
                        "to find valid core names for your board."
                    ),
                },
            ),
            ActionParameter(
                name="settings",
                required=True,
                schema={
                    "type": "object",
                    "description": (
                        "Core settings to apply. All keys are optional. "
                        "Supported keys: enabled (bool), timestamp (bool), "
                        "start_on_launch (bool), cycle_counting (bool), "
                        "trace_scenario (str or list[str]), "
                        "module_base_address (str), mem_space (str), "
                        "elf_images (str or list[str])."
                    ),
                },
            ),
        ),
        category="configurator",
        related_actions=(
            "configurator.configure_data_streams",
            "configurator.describe_trace_flow",
            "configurator.list_templates",
            "configurator.create_from_template",
        ),
    ),
    handler=configure_core,
)
