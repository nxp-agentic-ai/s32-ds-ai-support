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

"""``s32ct.generate_code`` - emit driver sources from an existing ``.mex``."""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter

from nxp.mcp.s32ct.actions import _params as P
from nxp.mcp.s32ct.handlers.action_handlers import generate_code


GENERATE_CODE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.generate_code",
        description=(
            "Generate code from an existing S32 Configuration Tools .mex for a "
            "single tool, without changing the configuration. Use this when the "
            ".mex is already correct and you only need the artifacts refreshed - "
            "it has a much smaller schema than the configure actions. "
            "export_kind selects what is produced: ExportSrc for driver .c/.h, "
            "ExportAll for sources plus reports, ExportHTML / ExportCSV for "
            "human-readable reports, ExportRegisters for the register dump, "
            "ExportMEX to rewrite the .mex itself. Returns a human-readable "
            "summary of the launcher run."
        ),
        params=(
            P.PROJECT_PATH_REQUIRED,
            P.TOOL_NAME_REQUIRED,
            P.OUTPUT_DIR_REQUIRED,
            ActionParameter(
                name="export_kind",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "What to emit. ExportSrc writes driver sources only; "
                        "ExportAll adds the reports."
                    ),
                    "enum": list(P.CODEGEN_EXPORT_KINDS),
                    "default": "ExportAll",
                },
            ),
            ActionParameter(
                name="enable_if_disabled",
                required=False,
                schema={
                    "type": "boolean",
                    "description": (
                        "Pass -Enable so generation still runs when the tool is "
                        "switched off in the project."
                    ),
                    "default": True,
                },
            ),
            P.SDK_VERSION,
            P.S32CT_LAUNCHER,
            P.LAUNCHER_INI,
            P.TIMEOUT_S,
        ),
        preconditions=(
            "project_path must be an existing .mex file.",
            "An S32 Configuration Tools installation must be resolvable; check "
            "with s32ct.env_status.",
        ),
        workflow_hints=(
            "Validate with s32ct.validate before generating - generation from an "
            "invalid model produces sources that will not compile.",
            "Run s32ct.sanitize first when the .mex was produced by splicing an "
            "example instance block into a template.",
        ),
        related_actions=(
            "s32ct.validate",
            "s32ct.sanitize",
            "s32ct.configure_cli",
        ),
        category="configure",
    ),
    handler=generate_code,
)


__all__ = ["GENERATE_CODE_ACTION"]
