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

"""``s32ct.sanitize`` - repair dangling cross-references in a spliced ``.mex``."""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter

from nxp.mcp.s32ct.actions import _params as P
from nxp.mcp.s32ct.handlers.action_handlers import sanitize


SANITIZE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.sanitize",
        description=(
            "Repair dangling cross-references in a freshly-spliced S32CT .mex so "
            "it can validate against a typical template project. When a driver "
            "instance block is grafted from an RTD example, it carries "
            "references that resolved in the example but not in the target - "
            "usually clock references into a McuClockReferencePoint the template "
            "does not expose, or references into an Mcl driver the project does "
            "not contain. Three idempotent sweeps fix them: redirect stray "
            "/Mcu/Mcu/McuModuleConfiguration references to the canonical clock "
            "reference point; self-close any array whose body references /Mcl/; "
            "and blank documented singleton *Ref settings that target an absent "
            "driver. Writes in place unless output_path is given. Safe to run "
            "repeatedly - a second run changes nothing. Returns counts and "
            "sample names per sweep so you can confirm what it touched."
        ),
        params=(
            P.PROJECT_PATH_REQUIRED,
            ActionParameter(
                name="output_path",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Write the sanitized project here instead of editing "
                        "project_path in place. Must end in .mex."
                    ),
                },
            ),
            ActionParameter(
                name="overwrite",
                required=False,
                schema={
                    "type": "boolean",
                    "description": (
                        "Allow output_path to be replaced when it already "
                        "exists."
                    ),
                    "default": False,
                },
            ),
            ActionParameter(
                name="canonical_clockref",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Override the clock reference point that stray Mcu "
                        "references are redirected to. Defaults to "
                        "McuClockReferencePoint_0 under "
                        "McuClockSettingConfig_0, which is what a typical "
                        "template exposes."
                    ),
                },
            ),
        ),
        preconditions=(
            "project_path must be an existing .mex file.",
            "output_path, when given, must have a .mex extension.",
        ),
        workflow_hints=(
            "Run immediately after splicing an example instance block into a "
            "project, and before s32ct.validate.",
            "Re-run s32ct.validate afterwards to confirm the 'value is not "
            "available' problems are gone.",
        ),
        related_actions=("s32ct.validate", "s32ct.inspect_xrefs"),
        category="sanitize",
    ),
    handler=sanitize,
)


__all__ = ["SANITIZE_ACTION"]
