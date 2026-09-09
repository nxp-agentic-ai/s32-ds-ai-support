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

"""Reusable ``ActionParameter`` definitions for the S32CT action catalog.

S32CT actions share a large amount of parameter surface: every launcher-backed
action accepts the same override trio (``s32ct_launcher`` / ``launcher_ini`` /
``timeout_s``), every ``.mex`` editing action accepts the same project-mode
pair, and the export verbs repeat across subsystems. Declaring each of those
once here keeps the per-action modules focused on what is actually distinctive
about the action, and guarantees an identical description / schema wherever a
parameter appears.

The enum lists deliberately mirror the ``ALLOWED_*`` sets in
:mod:`nxp.mcp.s32ct.tools.launcher`, which remain the runtime source of truth.
Declaring them in the schema as well lets the shared dispatcher reject a bad
value before a launcher process is ever spawned.
"""

from nxp.mcp.shared import ActionParameter

# The 9 tools S32CT exposes through -HeadlessTool.
TOOL_NAMES: tuple[str, ...] = (
    "Pins", "Clocks", "Peripherals", "DCD", "IVT",
    "eFUSE", "GTM", "QuadSPI", "FFC",
)

# Export verbs accepted by -Export*. Kept in sync with launcher.ALLOWED_EXPORTS.
EXPORT_KINDS: tuple[str, ...] = (
    "ExportAll", "ExportSrc", "ExportHTML", "ExportCSV",
    "ExportRegisters", "ExportMEX",
    "ExportBin", "ExportC", "ExportBlob", "ExportAB",
    "ExportPointers", "ExportDDRC", "ExportFssFw",
    "ExportConfig", "ExportELF",
    "ExportARXML", "ExportJSON",
)

# Export verbs meaningful for plain source generation from an existing .mex.
CODEGEN_EXPORT_KINDS: tuple[str, ...] = (
    "ExportAll", "ExportSrc", "ExportHTML", "ExportCSV",
    "ExportRegisters", "ExportMEX",
)


def _p(name: str, description: str, *, required: bool = False, **schema) -> ActionParameter:
    """Build one ``ActionParameter`` with a string schema by default."""

    return ActionParameter(
        name=name,
        required=required,
        schema={"type": schema.pop("type", "string"), "description": description, **schema},
    )


# ---------------------------------------------------------------------------
# Project mode
# ---------------------------------------------------------------------------

PROJECT_PATH = _p(
    "project_path",
    "Absolute path to an existing .mex project file to load and edit.",
)

PROJECT_PATH_REQUIRED = _p(
    "project_path",
    "Absolute path to an existing .mex project file.",
    required=True,
)

EMPTY_CONFIG = _p(
    "empty_config",
    "Bootstrap a brand-new configuration instead of loading a .mex. "
    "Mutually exclusive with project_path; requires mcu and sdk_version.",
    type="boolean",
    default=False,
)

MCU = _p("mcu", "MCU part name, for example S32K344 or S32S247TV.")
MCU_REQUIRED = _p(
    "mcu", "MCU part name, for example S32K344 or S32S247TV.", required=True,
)

SDK_VERSION = _p(
    "sdk_version",
    "Platform SDK / RTD version string to bind the configuration to.",
)

CONFIG_NAME = _p(
    "config_name",
    "Name for the generated configuration (used as the .mex stem).",
)


# ---------------------------------------------------------------------------
# Tool selection and generic edits
# ---------------------------------------------------------------------------

TOOL_NAME = _p(
    "tool_name",
    "Which S32CT tool to drive with -HeadlessTool.",
    enum=list(TOOL_NAMES),
)

TOOL_NAME_REQUIRED = _p(
    "tool_name",
    "Which S32CT tool to generate sources for.",
    required=True,
    enum=list(TOOL_NAMES),
)

ENABLE_TOOL = _p(
    "enable_tool",
    "Pass -Enable so the tool is switched on if the project has it disabled.",
    type="boolean",
)

APPLY_USE_CASE = _p(
    "apply_use_case",
    "Name of a predefined tool use-case to apply (-ApplyUseCase).",
)

SET_VALUES = _p(
    "set_values",
    "One or more '<setting-id>=<value>' assignments applied via -SetValue.",
    type="array",
    items={"type": "string"},
)

GET_VALUES = _p(
    "get_values",
    "One or more setting ids to read back via -GetValue. Returned under the "
    "'values' key of the response.",
    type="array",
    items={"type": "string"},
)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

EXPORT_KIND = _p(
    "export_kind",
    "Export verb to run after the edits. Requires output_dir.",
    enum=list(EXPORT_KINDS),
)

OUTPUT_DIR = _p(
    "output_dir",
    "Directory that receives exported artifacts. Required whenever "
    "export_kind is set.",
)

OUTPUT_DIR_REQUIRED = _p(
    "output_dir",
    "Directory that receives the generated artifacts.",
    required=True,
)


# ---------------------------------------------------------------------------
# Launcher / runtime overrides - accepted by every launcher-backed action
# ---------------------------------------------------------------------------

S32CT_LAUNCHER = _p(
    "s32ct_launcher",
    "Override the launcher binary (toolsc.exe for the desktop distribution, "
    "s32dsc.exe for the S32DS-integrated one). Defaults to the install "
    "selected at server startup.",
)

LAUNCHER_INI = _p(
    "launcher_ini",
    "Override the launcher .ini (tools.ini or s32ds.ini). Defaults to the "
    "install selected at server startup.",
)

TIMEOUT_S = _p(
    "timeout_s",
    "Per-call launcher timeout in seconds. Defaults to the server-configured "
    "s32ct.settings.timeout_s.",
    type="integer",
    minimum=1,
)

DATA_DIR = _p(
    "data_dir",
    "Eclipse workspace passed as -data. Mandatory for the S32DS-integrated "
    "distribution; a per-session workspace is used when omitted.",
)

EXTRA_ARGS = _p(
    "extra_args",
    "Additional raw launcher arguments appended verbatim. Escape hatch for "
    "flags this action does not model explicitly.",
    type="array",
    items={"type": "string"},
)

LAUNCHER_PARAMS: tuple[ActionParameter, ...] = (
    DATA_DIR,
    EXTRA_ARGS,
    S32CT_LAUNCHER,
    LAUNCHER_INI,
    TIMEOUT_S,
)


# ---------------------------------------------------------------------------
# MCU data package location
# ---------------------------------------------------------------------------

MCU_DATA_ROOT = _p(
    "mcu_data_root",
    "Override the MCU data root (the mcu_data folder). Defaults to whatever "
    "the selected install advertises.",
)


PLATFORM_SDK_DIR = _p(
    "platform_sdk_dir",
    "Override the PlatformSDK_* folder under the MCU directory. Auto-detected "
    "when omitted.",
)
