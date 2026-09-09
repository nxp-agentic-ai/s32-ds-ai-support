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
from nxp.mcp.s32trace.handlers.action_handlers import inspect_configurator_template


INSPECT_CONFIGURATOR_TEMPLATE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.inspect_template",
        description=(
            "Show every configurable attribute inside a specific S32Trace template "
            "or saved configuration XML file. Returns a nested structure that mirrors "
            "the ConfigBlock hierarchy, with each attribute showing its type, current "
            "default value, and (for enum attributes) the set of allowed values.\n\n"
            "Use this action when you need to browse all available settings for a "
            "template, discover valid enum values, or verify the current state of a "
            "saved configuration.\n\n"
            "For a higher-level view of the trace pipeline (which ETF/DDR sink "
            "collects each core, base addresses, buffer sizes) use "
            "configurator.describe_trace_flow instead."
        ),
        params=(
            ActionParameter(
                name="template_path",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Absolute path to an S32Trace configurator template or saved "
                        "configuration XML file. Obtain from configurator.list_templates "
                        "or from a previous configurator.create_trace_configuration result."
                    ),
                },
            ),
        ),
        category="configurator",
        workflow_hints=(
            "Use only when you need to browse all available settings or verify enum values. "
            "For a high-level pipeline overview prefer configurator.describe_trace_flow.",
        ),
        related_actions=(
            "configurator.list_templates",
            "configurator.describe_trace_flow",
        ),
    ),
    handler=inspect_configurator_template,
)
