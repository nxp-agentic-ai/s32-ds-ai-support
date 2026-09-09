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

"""``s32ct.inspect_*`` - read-only structural queries over a ``.mex``.

All seven actions parse the project XML in-process and never spawn the
launcher, so they are fast and side-effect free. They are declared separately
rather than behind one ``kind`` discriminator so each one advertises only the
parameters it actually uses - ``inspect_pins`` needs just a project path, while
``inspect_clock_outputs`` also accepts a name filter.

Every action returns ``{kind, project_path, result}``.
"""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter

from nxp.mcp.s32ct.actions import _params as P
from nxp.mcp.s32ct.handlers import action_handlers

_NAME_FILTER = ActionParameter(
    name="name_filter",
    required=False,
    schema={
        "type": "string",
        "description": (
            "Case-insensitive substring; only entries whose name contains it "
            "are returned. Omit to return everything."
        ),
    },
)

_ROOT_FILTER = ActionParameter(
    name="root_filter",
    required=False,
    schema={
        "type": "string",
        "description": (
            "Restrict results to cross-references targeting this driver root, "
            "for example 'Mcu' or 'Mcl'. Omit to return every reference."
        ),
    },
)

# (action suffix, handler name, extra params, description).
_INSPECT_SPECS: tuple[tuple[str, str, tuple[ActionParameter, ...], str], ...] = (
    (
        "summary",
        "inspect_summary",
        (),
        "Digest of an S32 Configuration Tools .mex: which tools are present, "
        "how many driver instances, pins, clock outputs and cross-references it "
        "contains. Start here when you need to understand an unfamiliar project "
        "before editing it, then drill in with the other inspect actions.",
    ),
    (
        "instances",
        "inspect_instances",
        (),
        "Every <instance> block in a .mex with its name, type_id, mode and "
        "size. This is the driver inventory of the project - use it to confirm "
        "whether a driver such as Can, Adc or Mcl is configured at all.",
    ),
    (
        "pins",
        "inspect_pins",
        (),
        "Every <pin> entry configured in the Pins tool of a .mex, with its "
        "peripheral, signal and routed pin. Use it to confirm a pin muxing "
        "change landed, or to review the current pin assignment.",
    ),
    (
        "clock_points",
        "inspect_clock_points",
        (),
        "Every McuClockReferencePoint_* in a .mex and the clock output each one "
        "selects. These are the reference points other drivers point at, so "
        "this is the action to run when a clock cross-reference fails to "
        "resolve during validation.",
    ),
    (
        "clock_outputs",
        "inspect_clock_outputs",
        (_NAME_FILTER,),
        "Every <clock_output> in the Clocks tool of a .mex with its computed "
        "frequency. Use it to verify the clock tree produces the frequencies a "
        "peripheral needs. Pass name_filter to narrow to one clock family.",
    ),
    (
        "clock_settings",
        "inspect_clock_settings",
        (_NAME_FILTER,),
        "Every <setting> inside the Clocks tool block of a .mex, as raw "
        "name/value pairs. This is the low-level view behind the computed "
        "frequencies - useful for finding the exact setting id to pass to a "
        "configure action's set_values. Pass name_filter to narrow the list.",
    ),
    (
        "xrefs",
        "inspect_xrefs",
        (_ROOT_FILTER,),
        "Every cross-reference of the form value=\"/Driver/...\" in a .mex. Use "
        "it to find references that point into a driver the project does not "
        "actually contain, which is the usual root cause of a 'value is not "
        "available' validation problem. Pass root_filter to focus on one driver.",
    ),
)


def _build_inspect_action(
    suffix: str,
    handler_name: str,
    extra_params: tuple[ActionParameter, ...],
    description: str,
) -> ActionExecutable:
    """Assemble one ``s32ct.inspect_<suffix>`` action."""

    return ActionExecutable(
        contract=ActionContract(
            name=f"s32ct.inspect_{suffix}",
            description=(
                f"{description} Read-only: parses the .mex directly and never "
                f"invokes the launcher. Returns "
                f"{{kind, project_path, result}}."
            ),
            params=(P.PROJECT_PATH_REQUIRED, *extra_params),
            preconditions=("project_path must be an existing .mex file.",),
            workflow_hints=(
                "Run before an edit to capture the current state, and again "
                "afterwards to confirm the change landed as intended.",
            ),
            related_actions=(
                "s32ct.inspect_summary",
                "s32ct.validate",
                "s32ct.lookup_drivers",
            ),
            category="inspect",
        ),
        handler=getattr(action_handlers, handler_name),
    )


INSPECT_ACTIONS: tuple[ActionExecutable, ...] = tuple(
    _build_inspect_action(suffix, handler_name, extra_params, description)
    for suffix, handler_name, extra_params, description in _INSPECT_SPECS
)


__all__ = ["INSPECT_ACTIONS"]
