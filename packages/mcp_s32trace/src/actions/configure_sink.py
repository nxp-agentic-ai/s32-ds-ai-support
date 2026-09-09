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
from nxp.mcp.s32trace.handlers.action_handlers import configure_sink


CONFIGURE_SINK_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.configure_sink",
        description=(
            "Apply settings to one ETF or DDR trace sink in an existing S32Trace config "
            "file. Use this to set buffer size, buffer mode, base address, collection "
            "mode, scatter-gather, and other sink-level attributes for a named sink "
            "such as 'ETF 2' or 'DDR'."
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
                name="sink_name",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Name of the sink block to configure, e.g. 'ETF 2' or 'DDR'. "
                        "Use configurator.describe_trace_flow to see available sink names."
                    ),
                },
            ),
            ActionParameter(
                name="settings",
                required=True,
                schema={
                    "type": "object",
                    "description": (
                        "Sink settings to apply. All keys are optional. "
                        "Supported keys: enable_buffer (bool), buffer_mode (str), "
                        "module_base_address (str), mem_space (str), "
                        "trace_buffer_size (str), trace_buffer_base_address (str), "
                        "trace_collection_mode (str), scatter_gather (bool), "
                        "upload_manually (bool), raw_trace_path (str)."
                    ),
                },
            ),
        ),
        category="configurator",
        related_actions=(
            "configurator.configure_data_streams",
            "configurator.describe_trace_flow",
            "configurator.create_from_template",
        ),
    ),
    handler=configure_sink,
)
