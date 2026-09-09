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

"""``s32ct.configure_cli`` - full-surface headless CLI across all 9 tools.

This is the escape hatch. The per-subsystem ``s32ct.configure_*`` actions cover
the common cases with a tight, self-documenting schema; this action exposes the
complete documented CLI grammar for workflows that need a flag combination the
focused actions do not model, or that must target a tool explicitly.
"""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter

from nxp.mcp.s32ct.actions import _params as P
from nxp.mcp.s32ct.actions._configure_factory import (
    _DCD_PARAMS,
    _EFUSE_PARAMS,
    _FFC_PARAMS,
    _IMPORT_C_PARAMS,
    _IVT_PARAMS,
    _PERIPHERALS_PARAMS,
    _CODEGEN_FRAMEWORK_PARAMS,
)
from nxp.mcp.s32ct.handlers.action_handlers import configure_cli


def _dedupe(params: tuple[ActionParameter, ...]) -> tuple[ActionParameter, ...]:
    """Drop repeated parameter names, keeping first occurrence order.

    Several subsystem groups legitimately share a flag (``import_bin`` is used
    by DCD, IVT and QuadSPI), and a JSON Schema ``properties`` map must not
    declare the same key twice.
    """

    seen: set[str] = set()
    unique: list[ActionParameter] = []
    for param in params:
        if param.name in seen:
            continue
        seen.add(param.name)
        unique.append(param)
    return tuple(unique)


CONFIGURE_CLI_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.configure_cli",
        description=(
            "Run the S32 Configuration Tools headless CLI with the full "
            "documented flag surface, against any of the 9 tools (Pins, Clocks, "
            "Peripherals, DCD, IVT, eFUSE, GTM, QuadSPI, FFC) selected via "
            "tool_name. Supports any documented chain: -Load <mex> or "
            "-EmptyConfig with -MCU and -SDKVersion; -HeadlessTool / -Enable / "
            "-ApplyUseCase / -SetValue / -GetValue / -ImportC; -ImportBin / "
            "-ImportBlob / -ImportAB / -ImportDDRC / -ImportARXML / -ImportJSON; "
            "the IVT pointer and raw-binary arguments; the eFUSE and FFC flags; "
            "-Validate; and every export verb. Prefer the focused "
            "s32ct.configure_<subsystem> actions when one of them fits - they "
            "expose a smaller, clearer schema. Portable across both "
            "distributions: the launcher prefix is selected automatically "
            "(desktop uses toolsc.exe; the S32DS-integrated variant uses "
            "s32dsc.exe with a mandatory -data workspace). Returns "
            "{exit_code, command, stdout_tail, stderr_tail, values, summary}."
        ),
        params=_dedupe(
            (
                # Mode.
                P.PROJECT_PATH,
                P.EMPTY_CONFIG,
                P.MCU,
                P.SDK_VERSION,
                P.CONFIG_NAME,
                # Tool selection - explicit here, unlike the focused actions.
                P.TOOL_NAME,
                P.ENABLE_TOOL,
                # Generic edits and reads.
                P.APPLY_USE_CASE,
                P.SET_VALUES,
                P.GET_VALUES,
                # Every subsystem-specific group, deduplicated.
                *_IMPORT_C_PARAMS,
                *_PERIPHERALS_PARAMS,
                *_CODEGEN_FRAMEWORK_PARAMS,
                *_DCD_PARAMS,
                *_IVT_PARAMS,
                *_EFUSE_PARAMS,
                *_FFC_PARAMS,
                # Validation and export.
                ActionParameter(
                    name="validate",
                    required=False,
                    schema={
                        "type": "boolean",
                        "description": (
                            "Pass -Validate. The launcher always exits 0, so "
                            "use s32ct.validate when you need a trustworthy "
                            "pass/fail verdict."
                        ),
                        "default": False,
                    },
                ),
                P.EXPORT_KIND,
                P.OUTPUT_DIR,
                # Launcher overrides.
                *P.LAUNCHER_PARAMS,
            )
        ),
        preconditions=(
            "An S32 Configuration Tools installation must be resolvable; check "
            "with s32ct.env_status.",
            "project_path and empty_config are mutually exclusive; exactly one "
            "is required.",
            "empty_config=true additionally requires mcu and sdk_version.",
            "output_dir is required whenever export_kind is set.",
        ),
        workflow_hints=(
            "Most flags require -HeadlessTool, so set tool_name unless you are "
            "only loading and exporting a project.",
            "Call s32ct.validate afterwards - the launcher exit code is not a "
            "reliable success signal.",
        ),
        related_actions=(
            "s32ct.configure_pins",
            "s32ct.configure_clocks",
            "s32ct.configure_peripherals",
            "s32ct.generate_code",
            "s32ct.validate",
        ),
        category="configure",
    ),
    handler=configure_cli,
)


__all__ = ["CONFIGURE_CLI_ACTION"]
