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
from nxp.mcp.s32trace.handlers.action_handlers import describe_trace_flow


DESCRIBE_TRACE_FLOW_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.describe_trace_flow",
        description=(
            "Parse an S32Trace configuration XML (template or saved file) and return "
            "the complete trace pipeline in a human-readable structure.\n\n"
            "RETURNS\n"
            "{\n"
            "  'cores': [\n"
            "    {\n"
            "      'name': 'M7_0', 'enabled': true,\n"
            "      'flow': ['M7_0', 'ARM Funnel 2 Port 0', 'ARM Funnel 2', 'ETF 2'],\n"
            "      'sink': 'ETF 2', 'module_base_address': '0xe0041000', 'mem_space': 'ahb0'\n"
            "    }, ...\n"
            "  ],\n"
            "  'sinks': [\n"
            "    {'name': 'ETF 2', 'enabled_in_data_streams': true, 'buffer_mode': 'Internal', ...},\n"
            "    {'name': 'DDR',   'enabled_in_data_streams': false, 'trace_buffer_size': '0x4000', ...}\n"
            "  ],\n"
            "  'data_streams': {'trace_location': ['ETF 2'], 'continuous_collection': false},\n"
            "  'timestamp_generator': {'enabled': true, 'module_base_address': '0x80037000'},\n"
            "  'soc_modules': [{'name': 'ARM Funnel 2', 'enabled': true, ...}, ...]\n"
            "}\n\n"
            "USE CASES\n"
            "- 'Which ETF collects Core 0?' -> check cores[0].flow and cores[0].sink\n"
            "- 'Is DDR collection active?' -> check sinks[n].enabled_in_data_streams for DDR\n"
            "- 'Is timestamp enabled?' -> check timestamp_generator.enabled\n"
            "- Verify a config after configurator.create_from_template and configure_* calls by calling this action again"
        ),
        params=(
            ActionParameter(
                name="config_path",
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
            "Call on a template to answer 'which ETF collects Core N?' questions. "
            "Call again on the output_path after configurator.create_trace_configuration to verify patches.",
        ),
        related_actions=(
            "configurator.list_templates",
            "configurator.create_from_template",
            "configurator.inspect_template",
        ),
    ),
    handler=describe_trace_flow,
)
