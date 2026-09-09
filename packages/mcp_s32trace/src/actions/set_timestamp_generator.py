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
from nxp.mcp.s32trace.handlers.action_handlers import set_timestamp_generator


SET_TIMESTAMP_GENERATOR_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.set_timestamp_generator",
        description=(
            "Enable or disable the global timestamp generator in an existing S32Trace "
            "config file, and optionally configure its base address, frequency, "
            "halt-on-debug behaviour, and memory space."
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
                name="enabled",
                required=True,
                schema={
                    "type": "boolean",
                    "description": "Set to true to enable the timestamp generator, false to disable it.",
                },
            ),
            ActionParameter(
                name="module_base_address",
                required=False,
                schema={
                    "type": "string",
                    "description": "Module base address for the timestamp counter (e.g. '0x40380000').",
                },
            ),
            ActionParameter(
                name="counter_base_frequency",
                required=False,
                schema={
                    "type": "string",
                    "description": "Counter base frequency value.",
                },
            ),
            ActionParameter(
                name="halt_on_debug",
                required=False,
                schema={
                    "type": "boolean",
                    "description": "Whether to halt the timestamp counter when the core halts.",
                },
            ),
            ActionParameter(
                name="mem_space",
                required=False,
                schema={
                    "type": "string",
                    "description": "Memory space identifier for the timestamp generator.",
                },
            ),
        ),
        category="configurator",
        related_actions=(
            "configurator.create_from_template",
            "configurator.describe_trace_flow",
        ),
    ),
    handler=set_timestamp_generator,
)
