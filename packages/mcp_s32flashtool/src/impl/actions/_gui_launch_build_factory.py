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

from __future__ import annotations
from typing import Any
from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter
from nxp.mcp.s32flashtool.impl.handlers import (
    local_api_command_handler,
)

# ---------------------------------------------------------------------------
# Launch GUI action.
#
# The launch action is a lifecycle action: it launches the S32FlashTool GUI and
# its local API server. It routes through the shared local_api_command_handler handler
# with an api_request pinned to action="launch". This is the only GUI lifecycle
# action, so its metadata is defined inline as module constants (no lookup
# table). The launcher first probes the target host/port for an already-running
# GUI; if one is listening it is reused (no duplicate process is spawned),
# otherwise a new GUI process is started.
# ---------------------------------------------------------------------------

# The single supported GUI lifecycle action name pinned into the api_request.
_LAUNCH_ACTION = "launch"
_LAUNCH_NAME = "gui_launch"
_LAUNCH_DESCRIPTION = (
    "Launch the S32FlashTool GUI and its local API server. First probes the "
    "target host/port for an already-running GUI: if one is listening it is "
    "reused and a user message is returned (no duplicate process is spawned); "
    "otherwise a new GUI process is started. Execute `search_actions` after "
    "this, to retrieve the actions exposed by the S32FlashTool GUI. The agent "
    "should expect several seconds startup time when a new instance is launched"
)


_LAUNCH_RELATED_ACTIONS: tuple[str, ...] = ("search_actions",)



# Connection/session params shared by every GUI API action.
_API_COMMON_PARAMS: tuple[ActionParameter, ...] = (
    ActionParameter(
        name="sft_folder",
        required=False,
        schema={
            "type": "string",
            "description": "Absolute path to the S32FlashTool folder. Falls back to the server runtime context when omitted.",
        },
    ),
    ActionParameter(
        name="host",
        required=False,
        schema={
            "type": "string",
            "description": "API server host. Defaults to localhost.",
        },
    ),
    ActionParameter(
        name="port",
        required=False,
        schema={
            "type": "integer",
            "description": "API server port. Resolved from the installation configuration when omitted.",
        },
    ),
    ActionParameter(
        name="timeout",
        required=False,
        schema={
            "type": "integer",
            "description": "Request/launch timeout in seconds. Defaults to 30.",
        },
    ),
)


def _api_request_param(
    api_action: str,
    params_schema: dict[str, Any] | None = None,
) -> ActionParameter:
    """Build the api_request param with its action name pinned via a const."""

    effective_params_schema = params_schema or {
        "type": "object",
        "description": "Optional action parameters.",
        "additionalProperties": True,
    }

    return ActionParameter(
        name="api_request",
        required=True,
        schema={
            "type": "object",
            "description": f"Structured request for the '{api_action}' S32FlashTool GUI API action.",
            "properties": {
                "action": {
                    "type": "string",
                    "const": api_action,
                    "description": "Pinned S32FlashTool GUI API action for this executable.",
                },
                "params": effective_params_schema,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    )


def make_launch_action(gui_action: str = _LAUNCH_ACTION) -> ActionExecutable:
    """Build the S32FlashTool GUI ``launch`` lifecycle ActionExecutable.

    ``launch`` is the only supported GUI lifecycle action; ``gui_action`` is
    kept as a parameter for call-site clarity but must equal ``"launch"``.
    """

    if gui_action != _LAUNCH_ACTION:
        raise ValueError(
            f"Unknown GUI launch action: {gui_action!r}. Supported: [{_LAUNCH_ACTION!r}]"
        )

    preconditions = (
        "An effective installation path must be configured (params.sft_folder or the server runtime context).",
        f"request.action must be '{gui_action}'. The next actions have to get the appropriate `port` to be executed against S32FlashTool GUI",
    )

    return ActionExecutable(
        contract=ActionContract(
            name=_LAUNCH_NAME,
            description=(
                f"Drive the S32FlashTool GUI API '{gui_action}' action "
                f"({_LAUNCH_DESCRIPTION})."
            ),
            params=_API_COMMON_PARAMS + (_api_request_param(gui_action),),
            preconditions=preconditions,
            related_actions=_LAUNCH_RELATED_ACTIONS,
            category="launch_api",
        ),
        handler=local_api_command_handler,
    )


