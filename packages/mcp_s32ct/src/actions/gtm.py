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

"""GTM (Generic Timer Module) actions.

GTM gets three separate actions instead of one because the three operations
have genuinely different shapes: editing an existing configuration is a normal
launcher edit, listing use-cases is a pure read of the MCU data package that
needs no project at all, and bootstrapping from a use-case template is a
multi-step operation with its own required parameter set. Splitting them means
each one advertises exactly the parameters it needs.
"""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter

from nxp.mcp.s32ct.actions import _params as P
from nxp.mcp.s32ct.handlers.action_handlers import (
    gtm_create_from_usecase,
    gtm_edit,
    gtm_list_usecases,
)


GTM_EDIT_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.gtm_edit",
        description=(
            "Edit an existing GTM (Generic Timer Module) configuration through "
            "the headless CLI: apply a tool use-case, set or read individual "
            "GTM settings, and export the result. Operates on an existing .mex "
            "(project_path) or bootstraps an empty configuration "
            "(empty_config=true with mcu and sdk_version). To start from a "
            "predefined GTM use-case template instead, use "
            "s32ct.gtm_create_from_usecase. Returns "
            "{exit_code, command, stdout_tail, stderr_tail, values, summary}."
        ),
        params=(
            P.PROJECT_PATH,
            P.EMPTY_CONFIG,
            P.MCU,
            P.SDK_VERSION,
            P.CONFIG_NAME,
            P.ENABLE_TOOL,
            P.APPLY_USE_CASE,
            P.SET_VALUES,
            P.GET_VALUES,
            P.EXPORT_KIND,
            P.OUTPUT_DIR,
            *P.LAUNCHER_PARAMS,
        ),
        preconditions=(
            "An S32 Configuration Tools installation must be resolvable; check "
            "with s32ct.env_status.",
            "project_path and empty_config are mutually exclusive.",
            "The selected MCU must actually have a GTM module.",
        ),
        workflow_hints=(
            "Use s32ct.gtm_list_usecases to discover the predefined templates "
            "available for an MCU before applying one.",
        ),
        related_actions=(
            "s32ct.gtm_list_usecases",
            "s32ct.gtm_create_from_usecase",
            "s32ct.validate",
        ),
        category="gtm",
    ),
    handler=gtm_edit,
)


GTM_LIST_USECASES_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.gtm_list_usecases",
        description=(
            "List the predefined GTM use-case template names available for an "
            "MCU. Read-only discovery step: it inspects the MCU data package on "
            "disk and needs no project, only the MCU name. Feed a returned name "
            "to s32ct.gtm_create_from_usecase as its usecase parameter. Returns "
            "a sorted list of names, or an empty list when the MCU ships no GTM "
            "templates. Note that use-case templates are shipped only by the "
            "desktop S32CT distribution."
        ),
        params=(
            P.MCU_REQUIRED,
            P.MCU_DATA_ROOT,
            P.PLATFORM_SDK_DIR,
        ),
        preconditions=(
            "The MCU data package for mcu must be installed on this host.",
        ),
        workflow_hints=(
            "Always call this before s32ct.gtm_create_from_usecase rather than "
            "guessing a template name or a fixed on-disk layout.",
        ),
        related_actions=(
            "s32ct.gtm_create_from_usecase",
            "s32ct.gtm_edit",
            "s32ct.env_status",
        ),
        category="gtm",
    ),
    handler=gtm_list_usecases,
)


GTM_CREATE_FROM_USECASE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.gtm_create_from_usecase",
        description=(
            "Bootstrap a brand-new GTM configuration from a predefined use-case "
            "template. Creates an empty configuration for mcu and sdk_version, "
            "applies the named use-case .mex, and exports the generated code "
            "into output_dir. Discover valid usecase values with "
            "s32ct.gtm_list_usecases. Pass usecase_mex_path to apply a template "
            "from an explicit location instead of the MCU data package. Returns "
            "a human-readable summary of the bootstrap run."
        ),
        params=(
            P.MCU_REQUIRED,
            ActionParameter(
                name="sdk_version",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Platform SDK / RTD version to bind the new "
                        "configuration to."
                    ),
                },
            ),
            ActionParameter(
                name="usecase",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Use-case template name, as returned by "
                        "s32ct.gtm_list_usecases (no .mex extension)."
                    ),
                },
            ),
            P.OUTPUT_DIR_REQUIRED,
            ActionParameter(
                name="usecase_mex_path",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Apply this .mex template directly instead of resolving "
                        "usecase inside the MCU data package."
                    ),
                },
            ),
            ActionParameter(
                name="export_kind",
                required=False,
                schema={
                    "type": "string",
                    "description": "What to emit after applying the use-case.",
                    "enum": ["ExportAll", "ExportSrc", "ExportHTML", "ExportMEX"],
                    "default": "ExportAll",
                },
            ),
            ActionParameter(
                name="gtm_codegen",
                required=False,
                schema={
                    "type": "boolean",
                    "description": (
                        "Run GTM code generation as part of the bootstrap."
                    ),
                    "default": True,
                },
            ),
            P.CONFIG_NAME,
            P.MCU_DATA_ROOT,
            P.PLATFORM_SDK_DIR,
            P.S32CT_LAUNCHER,
            P.LAUNCHER_INI,
            P.TIMEOUT_S,
        ),
        preconditions=(
            "An S32 Configuration Tools installation must be resolvable; check "
            "with s32ct.env_status.",
            "usecase must name a template that exists for this MCU; list them "
            "with s32ct.gtm_list_usecases.",
        ),
        workflow_hints=(
            "Call s32ct.gtm_list_usecases first to get a valid usecase name.",
            "The exported .mex can be reopened later with s32ct.gtm_edit or fed "
            "to s32ct.generate_code for scoped regeneration.",
        ),
        related_actions=(
            "s32ct.gtm_list_usecases",
            "s32ct.gtm_edit",
            "s32ct.generate_code",
        ),
        category="gtm",
    ),
    handler=gtm_create_from_usecase,
)


GTM_ACTIONS: tuple[ActionExecutable, ...] = (
    GTM_EDIT_ACTION,
    GTM_LIST_USECASES_ACTION,
    GTM_CREATE_FROM_USECASE_ACTION,
)


__all__ = [
    "GTM_ACTIONS",
    "GTM_CREATE_FROM_USECASE_ACTION",
    "GTM_EDIT_ACTION",
    "GTM_LIST_USECASES_ACTION",
]
