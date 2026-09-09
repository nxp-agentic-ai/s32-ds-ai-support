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
from nxp.mcp.s32trace.handlers.action_handlers import configure_data_streams


CONFIGURE_DATA_STREAMS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="configurator.configure_data_streams",
        description=(
            "Set the active trace sinks (TraceLocation) in an existing S32Trace config "
            "file and optionally toggle continuous collection mode. "
            "trace_location controls which sinks (e.g. 'ETF 2', 'DDR') are active."
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
                name="trace_location",
                required=True,
                schema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of sink names to activate, e.g. ['ETF 2'] or ['DDR']. "
                        "Use configurator.describe_trace_flow to see available sink names."
                    ),
                },
            ),
            ActionParameter(
                name="continuous_collection",
                required=False,
                schema={
                    "type": "boolean",
                    "description": "When true, trace collection continues until stopped manually.",
                },
            ),
        ),
        category="configurator",
        related_actions=(
            "configurator.create_from_template",
            "configurator.configure_sink",
            "configurator.describe_trace_flow",
        ),
    ),
    handler=configure_data_streams,
)
