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

"""Factory for the per-subsystem ``s32ct.configure_*`` actions.

The eight subsystem actions (Pins, Clocks, Peripherals, DCD, IVT, eFUSE,
QuadSPI, FFC) all drive the same launcher entry point with ``tool_name``
pre-filled. What differs between them is only:

* the action name and the human-readable description;
* which subsystem-specific flags are relevant (IVT has a dozen boot-image
  parameters that mean nothing to Pins; FFC has ARXML/JSON import flags; and
  so on).

Rather than copy a ~40-line contract eight times, this module declares the
common core once and lets each subsystem contribute only its own extra
parameters. That keeps the eight contracts genuinely consistent and makes
adding a flag a one-line change in a single place.
"""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter

from nxp.mcp.s32ct.handlers import action_handlers
from nxp.mcp.s32ct.actions import _params as P


def _p(name: str, description: str, **schema) -> ActionParameter:
    """Build one optional ``ActionParameter``, string-typed by default."""

    return ActionParameter(
        name=name,
        required=False,
        schema={
            "type": schema.pop("type", "string"),
            "description": description,
            **schema,
        },
    )


# ---------------------------------------------------------------------------
# Subsystem-specific parameter groups
# ---------------------------------------------------------------------------

# Pins / Peripherals: import existing hand-written C configuration back into
# the model so the tool becomes the source of truth going forward.
_IMPORT_C_PARAMS: tuple[ActionParameter, ...] = (
    _p(
        "import_c",
        "One or more existing .c/.h files to import into the configuration "
        "(-ImportC).",
        type="array",
        items={"type": "string"},
    ),
)

_PERIPHERALS_PARAMS: tuple[ActionParameter, ...] = (
    _p("import_project", "Path to another project to import settings from."),
    _p("sdk_path", "Path to the SDK whose sources should back the import."),
    _p(
        "overwrite_with_sdk_sources",
        "Replace project sources with the SDK versions during the import.",
        type="boolean",
        default=False,
    ),
    _p(
        "migrate_to_toolchain_version",
        "Migrate the imported configuration to the toolchain's SDK version.",
        type="boolean",
        default=False,
    ),
    _p(
        "migrate_to_highest_version",
        "Migrate the imported configuration to the highest available version.",
        type="boolean",
        default=False,
    ),
)

# Code-generation framework knobs - accepted by any tool that emits sources.
_CODEGEN_FRAMEWORK_PARAMS: tuple[ActionParameter, ...] = (
    _p("custom_copyright", "Path to a file whose text replaces the generated copyright header."),
    _p("output_path_overrides", "Per-file output path overrides for generated sources."),
)

# DCD / QuadSPI / IVT binary import.
_IMPORT_BIN_PARAM = _p(
    "import_bin", "Binary image to import into the configuration (-ImportBin).",
)

_IVT_PARAMS: tuple[ActionParameter, ...] = (
    _IMPORT_BIN_PARAM,
    _p("import_blob", "Boot blob to import (-ImportBlob)."),
    _p("import_ab", "A/B swap image to import (-ImportAB)."),
    _p("import_ddrc", "DDR controller configuration to import (-ImportDDRC)."),
    _p("auto_align", "Automatic payload alignment policy for the emitted image."),
    _p("custom_pointers_addrs", "Explicit addresses for custom IVT pointers."),
    _p("start_pointer_addr", "Address written into the IVT start pointer."),
    _p("entry_pointer_addr", "Address written into the IVT entry pointer."),
    _p("raw_binary", "Raw binary payload to embed in the image."),
    _p("clock_config_data", "Clock configuration data blob to embed."),
    _p("mini_paco_structure", "Mini-PaCo structure to embed in the image."),
    _p("pre_defined_data", "Pre-defined data block to embed in the image."),
    _p("boot_device_id", "Target boot device identifier."),
    _p("ivt_start_addr", "Base address the IVT itself is placed at."),
    _p(
        "update_filepaths",
        "How embedded payload paths are rewritten when the .mex is saved.",
        enum=["relativeToCurrentMex", "absolute", "keepExisting"],
    ),
    _p(
        "ivt_filter",
        "Restrict which IVT pointers -ExportPointers reports.",
        enum=["UnresolvedCustomPointers", "All"],
    ),
    _p(
        "include_marker",
        "Include the boot marker in the exported image.",
        type="boolean",
        default=False,
    ),
)

_EFUSE_PARAMS: tuple[ActionParameter, ...] = (
    _p(
        "include_serial_boot_header",
        "Prepend the serial-boot header to the exported eFUSE image.",
        type="boolean",
        default=False,
    ),
)

_FFC_PARAMS: tuple[ActionParameter, ...] = (
    _p(
        "import_arxml",
        "One or more AUTOSAR ARXML (.ecvd) files to import (-ImportARXML).",
        type="array",
        items={"type": "string"},
    ),
    _p("import_json", "JSON configuration file to import (-ImportJSON)."),
    _p(
        "file_type",
        "Restrict the FFC export to one firmware file type.",
        enum=["all", "Fss_Rem_Pm", "Fss_Btm"],
    ),
    _p(
        "default_containers",
        "Emit the default FFC containers.",
        type="boolean",
        default=False,
    ),
)

_QUADSPI_PARAMS: tuple[ActionParameter, ...] = (_IMPORT_BIN_PARAM,)
_DCD_PARAMS: tuple[ActionParameter, ...] = (_IMPORT_BIN_PARAM,)


# Per-subsystem: (tool_name, extra_params, focus sentence for the description).
SUBSYSTEMS: tuple[tuple[str, tuple[ActionParameter, ...], str], ...] = (
    (
        "Pins",
        _IMPORT_C_PARAMS + _CODEGEN_FRAMEWORK_PARAMS,
        "Configure pin muxing and electrical properties, import existing pin "
        "definitions from .c sources, and emit Siul2_Port_Ip_Cfg sources.",
    ),
    (
        "Clocks",
        _CODEGEN_FRAMEWORK_PARAMS,
        "Configure the clock tree (sources, PLLs, dividers, clock outputs) and "
        "emit Clock_Ip_Cfg / Mcu_Cfg sources.",
    ),
    (
        "Peripherals",
        _IMPORT_C_PARAMS + _PERIPHERALS_PARAMS + _CODEGEN_FRAMEWORK_PARAMS,
        "Configure peripheral driver instances (Can, Adc, Pwm, Uart, Spi, ...), "
        "import an existing project or .c sources, and emit driver sources.",
    ),
    (
        "DCD",
        _DCD_PARAMS,
        "Configure Device Configuration Data, import a binary DCD image, and "
        "export the DCD blob or generated sources.",
    ),
    (
        "IVT",
        _IVT_PARAMS + _CODEGEN_FRAMEWORK_PARAMS,
        "Configure the Image Vector Table and boot image: embed payloads, set "
        "start/entry pointers, and export a bootable blob or binary.",
    ),
    (
        "eFUSE",
        _EFUSE_PARAMS,
        "Configure eFUSE / one-time-programmable values and export them as a "
        "binary, ELF, or configuration file.",
    ),
    (
        "QuadSPI",
        _QUADSPI_PARAMS,
        "Configure the QuadSPI serial-flash interface, import a binary QuadSPI "
        "image, and export the resulting configuration.",
    ),
    (
        "FFC",
        _FFC_PARAMS,
        "Configure Firmware Feature Control, import AUTOSAR ARXML (.ecvd) or "
        "JSON, and export the firmware feature files.",
    ),
)


def _build_configure_action(
    tool_name: str,
    extra_params: tuple[ActionParameter, ...],
    focus: str,
) -> ActionExecutable:
    """Assemble the ``s32ct.configure_<tool>`` action for one subsystem."""

    slug = tool_name.lower()
    handler = getattr(action_handlers, f"configure_{slug}")

    params: tuple[ActionParameter, ...] = (
        # Mode: load an existing .mex, or bootstrap an empty configuration.
        P.PROJECT_PATH,
        P.EMPTY_CONFIG,
        P.MCU,
        P.SDK_VERSION,
        P.CONFIG_NAME,
        # Generic edits and reads.
        P.ENABLE_TOOL,
        P.APPLY_USE_CASE,
        P.SET_VALUES,
        P.GET_VALUES,
        # Subsystem-specific flags.
        *extra_params,
        # Validation and export.
        ActionParameter(
            name="validate",
            required=False,
            schema={
                "type": "boolean",
                "description": (
                    "Pass -Validate. Note the launcher always exits 0, so use "
                    "the s32ct.validate action when you need a trustworthy "
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

    return ActionExecutable(
        contract=ActionContract(
            name=f"s32ct.configure_{slug}",
            description=(
                f"Drive the S32 Configuration Tools {tool_name} tool headlessly. "
                f"{focus} "
                f"Provide exactly one of project_path (edit an existing .mex) or "
                f"empty_config=true with mcu and sdk_version (bootstrap a new "
                f"configuration). tool_name is implied by this action, so it "
                f"does not need to be passed. Set export_kind together with "
                f"output_dir to write artifacts. Returns "
                f"{{exit_code, command, stdout_tail, stderr_tail, values, summary}}."
            ),
            params=params,
            preconditions=(
                "An S32 Configuration Tools installation must be resolvable; "
                "check with s32ct.env_status.",
                "project_path and empty_config are mutually exclusive.",
                "output_dir is required whenever export_kind is set.",
            ),
            workflow_hints=(
                "Call s32ct.validate after editing to confirm the .mex is clean "
                "- the launcher exit code alone is not a reliable signal.",
                f"Use s32ct.inspect_summary to review the .mex before and after "
                f"a {tool_name} edit.",
            ),
            related_actions=(
                "s32ct.configure_cli",
                "s32ct.validate",
                "s32ct.generate_code",
            ),
            category="configure",
        ),
        handler=handler,
    )


CONFIGURE_SUBSYSTEM_ACTIONS: tuple[ActionExecutable, ...] = tuple(
    _build_configure_action(tool_name, extra_params, focus)
    for tool_name, extra_params, focus in SUBSYSTEMS
)


__all__ = ["CONFIGURE_SUBSYSTEM_ACTIONS"]
