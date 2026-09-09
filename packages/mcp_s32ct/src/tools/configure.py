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

"""``configure`` - unified write-side dispatcher for S32 Configuration Tools.

This single MCP tool folds **eleven** previously-separate tools into one
``action``-discriminated surface:

* ``action="cli"``           - full-surface headless CLI (was ``cli``)
* ``action="pins"``          - was ``pins``           (cli with tool_name=Pins)
* ``action="clocks"``        - was ``clocks``         (cli with tool_name=Clocks)
* ``action="peripherals"``   - was ``peripherals``    (cli with tool_name=Peripherals)
* ``action="dcd"``           - was ``dcd``            (cli with tool_name=DCD)
* ``action="ivt"``           - was ``ivt``            (cli with tool_name=IVT)
* ``action="efuse"``         - was ``efuse``          (cli with tool_name=eFUSE)
* ``action="gtm"``           - was ``gtm`` (edit / list_usecases / create_from_usecase)
* ``action="quadspi"``       - was ``quadspi``        (cli with tool_name=QuadSPI)
* ``action="ffc"``           - was ``ffc``            (cli with tool_name=FFC)
* ``action="generate_code"`` - was ``generate_code`` (headless ExportAll/Src/...)

All actions ultimately invoke :func:`nxp.mcp.s32ct.tools.launcher.cli_impl`
(or the dedicated ``generate_code_impl`` / ``gtm_create_from_usecase_impl``)
so behaviour is **identical** to the pre-refactor per-tool wrappers.

Why one tool: each MCP tool registration costs system-prompt tokens. The 11
write-side tools all share the same execution model (invoke ``toolsc.exe``,
mutate ``.mex`` or generated source) and the same ~50 parameters. Folding them
into one ``action``-routed entry preserves the full functional surface while
collapsing 11 schema definitions into 1.

The ``action`` parameter is also a useful **verb-routing hint** for the LLM:
instead of choosing between ``nxp_s32ct_pins`` and ``nxp_s32ct_clocks`` by
guessing the matching subsystem, the agent simply picks the action it
intends to perform.
"""
import logging
from pathlib import Path
from typing import Literal, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import (
    S32CTContext,
    _resolve_platform_sdk_dir,
    cli_impl,
    generate_code_impl,
    gtm_create_from_usecase_impl,
)

_logger = logging.getLogger(MCP_SERVER_NAME)


# Mapping from a friendly `action` value to the canonical S32CT tool_name
# that ``cli_impl`` expects. ``cli`` / ``generate_code`` / ``gtm`` are handled
# separately because they don't slot into the simple cli-with-tool_name path.
_ACTION_TO_TOOL_NAME: dict[str, str] = {
    "pins": "Pins",
    "clocks": "Clocks",
    "peripherals": "Peripherals",
    "dcd": "DCD",
    "ivt": "IVT",
    "efuse": "eFUSE",
    "quadspi": "QuadSPI",
    "ffc": "FFC",
}


def register_configure_tool(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    @server.tool(
        name="configure",
        description=(
            "Unified write-side dispatcher for S32 Configuration Tools. Folds "
            "11 previously-separate tools (cli + 9 per-tool wrappers + "
            "generate_code) into one `action`-routed surface.\n\n"
            "Actions:\n"
            "  - `cli` -- full-surface generic headless CLI across all 9 tools "
            "(Pins, Clocks, Peripherals, DCD, IVT, eFUSE, GTM, QuadSPI, FFC). "
            "Supports any documented chain: -Load <mex> OR -EmptyConfig + -MCU "
            "+ -SDKVersion, -HeadlessTool/-Enable/-ApplyUseCase/-SetValue/"
            "-GetValue/-ImportC, -ImportBin/-ImportBlob/-ImportAB/-ImportDDRC/"
            "-ImportARXML/-ImportJSON, IVT pointer & raw-binary args, eFUSE/FFC "
            "flags, -Validate, and any export verb (ExportAll/Src/HTML/CSV/"
            "Registers/MEX/Bin/C/Blob/AB/Pointers/DDRC/FssFw/Config/ELF/ARXML/"
            "JSON).\n"
            "  - `pins` / `clocks` / `peripherals` / `dcd` / `ivt` / `efuse` / "
            "`quadspi` / `ffc` -- per-tool convenience wrappers that pre-fill "
            "tool_name and surface only the flags relevant to that subsystem.\n"
            "  - `gtm` -- GTM facade with three sub-modes selected by "
            "`gtm_action` in {edit, list_usecases, create_from_usecase}: edit "
            "(default) uses cli with tool_name=GTM; list_usecases returns the "
            "GTM use-case names available for `mcu` under the MCU data package "
            "(requires only `mcu`); create_from_usecase bootstraps a new GTM "
            "configuration via -EmptyConfig + -MCU + -SDKVersion, applies a "
            "predefined GTM use-case .mex, and exports the generated code "
            "(requires `mcu`, `sdk_version`, `usecase`, `output_dir`).\n"
            "  - `generate_code` -- headless code generation from an existing "
            ".mex for a single tool (Pins/Clocks/Peripherals/DCD/IVT/eFUSE/GTM/"
            "QuadSPI/FFC); export_kind in {ExportAll, ExportSrc, ExportHTML, "
            "ExportCSV, ExportRegisters, ExportMEX}.\n\n"
            "Portable across both S32CT distributions: the launcher prefix is "
            "auto-selected per the active install (`desktop` -> `toolsc.exe`; "
            "`integrated_s32ds` -> `s32dsc.exe` with mandatory `-data <ws>`). "
            "See the `s32ct-distributions` skill. Returns "
            "{exit_code, command, stdout_tail, stderr_tail, values, summary} "
            "for cli-routed actions, or the action-specific shape documented "
            "above for gtm sub-modes and generate_code."
        ),
    )
    def configure(
        action: Literal[
            "cli",
            "pins",
            "clocks",
            "peripherals",
            "dcd",
            "ivt",
            "efuse",
            "gtm",
            "quadspi",
            "ffc",
            "generate_code",
        ],
        # ------------------------------------------------------------------
        # Mode / project
        # ------------------------------------------------------------------
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        # ------------------------------------------------------------------
        # Tool selection (for action="cli" or to override the wrapper default)
        # ------------------------------------------------------------------
        tool_name: Optional[Literal[
            "Pins", "Clocks", "Peripherals", "DCD", "IVT",
            "eFUSE", "GTM", "QuadSPI", "FFC",
        ]] = None,
        enable_tool: Optional[bool] = None,
        # ------------------------------------------------------------------
        # Generic edits / queries
        # ------------------------------------------------------------------
        apply_use_case: Optional[str] = None,
        set_values: Optional[list[str]] = None,
        get_values: Optional[list[str]] = None,
        # ------------------------------------------------------------------
        # Pins / Peripherals
        # ------------------------------------------------------------------
        import_c: Optional[list[str]] = None,
        import_project: Optional[str] = None,
        sdk_path: Optional[str] = None,
        overwrite_with_sdk_sources: bool = False,
        migrate_to_toolchain_version: bool = False,
        migrate_to_highest_version: bool = False,
        # ------------------------------------------------------------------
        # Code-gen framework
        # ------------------------------------------------------------------
        custom_copyright: Optional[str] = None,
        output_path_overrides: Optional[str] = None,
        # ------------------------------------------------------------------
        # Imports (binary / blob / ARXML / JSON)
        # ------------------------------------------------------------------
        import_bin: Optional[str] = None,
        import_blob: Optional[str] = None,
        import_ab: Optional[str] = None,
        import_ddrc: Optional[str] = None,
        import_arxml: Optional[list[str]] = None,
        import_json: Optional[str] = None,
        # ------------------------------------------------------------------
        # IVT / boot-image params
        # ------------------------------------------------------------------
        auto_align: Optional[str] = None,
        custom_pointers_addrs: Optional[str] = None,
        start_pointer_addr: Optional[str] = None,
        entry_pointer_addr: Optional[str] = None,
        raw_binary: Optional[str] = None,
        clock_config_data: Optional[str] = None,
        mini_paco_structure: Optional[str] = None,
        pre_defined_data: Optional[str] = None,
        boot_device_id: Optional[str] = None,
        ivt_start_addr: Optional[str] = None,
        update_filepaths: Optional[Literal[
            "relativeToCurrentMex", "absolute", "keepExisting",
        ]] = None,
        ivt_filter: Optional[Literal[
            "UnresolvedCustomPointers", "All",
        ]] = None,
        include_marker: bool = False,
        # ------------------------------------------------------------------
        # eFUSE
        # ------------------------------------------------------------------
        include_serial_boot_header: bool = False,
        # ------------------------------------------------------------------
        # FFC
        # ------------------------------------------------------------------
        file_type: Optional[Literal["all", "Fss_Rem_Pm", "Fss_Btm"]] = None,
        default_containers: bool = False,
        # ------------------------------------------------------------------
        # Validate (CLI-level toggle - the gate-tool ``validate`` is preferred)
        # ------------------------------------------------------------------
        validate: bool = False,
        # ------------------------------------------------------------------
        # Export
        # ------------------------------------------------------------------
        export_kind: Optional[Literal[
            "ExportAll", "ExportSrc", "ExportHTML", "ExportCSV",
            "ExportRegisters", "ExportMEX",
            "ExportBin", "ExportC", "ExportBlob", "ExportAB",
            "ExportPointers", "ExportDDRC", "ExportFssFw",
            "ExportConfig", "ExportELF",
            "ExportARXML", "ExportJSON",
        ]] = None,
        output_dir: Optional[str] = None,
        # ------------------------------------------------------------------
        # GTM-specific (only used when action="gtm")
        # ------------------------------------------------------------------
        gtm_action: Literal[
            "edit", "list_usecases", "create_from_usecase",
        ] = "edit",
        usecase: Optional[str] = None,
        usecase_mex_path: Optional[str] = None,
        gtm_codegen: bool = True,
        mcu_data_root: Optional[str] = None,
        platform_sdk_dir: Optional[str] = None,
        # ------------------------------------------------------------------
        # generate_code-specific (only used when action="generate_code")
        # ------------------------------------------------------------------
        enable_if_disabled: bool = True,
        # ------------------------------------------------------------------
        # Launcher / runtime
        # ------------------------------------------------------------------
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ):
        # ------------------------------------------------------------------
        # action="generate_code" -- dedicated impl, distinct return shape (str)
        # ------------------------------------------------------------------
        if action == "generate_code":
            missing = [
                n for n, v in (
                    ("project_path", project_path),
                    ("tool_name", tool_name),
                    ("output_dir", output_dir),
                ) if not v
            ]
            if missing:
                return (
                    "configure(action='generate_code') requires: "
                    + ", ".join(missing)
                )
            _allowed_export = {
                "ExportAll", "ExportSrc", "ExportHTML",
                "ExportCSV", "ExportRegisters", "ExportMEX",
            }
            ek = export_kind if export_kind in _allowed_export else "ExportAll"
            try:
                return generate_code_impl(
                    ctx,
                    project_path=project_path,
                    tool_name=tool_name,
                    output_dir=output_dir,
                    export_kind=ek,
                    enable_if_disabled=enable_if_disabled,
                    sdk_version=sdk_version,
                    s32ct_launcher=s32ct_launcher,
                    launcher_ini=launcher_ini,
                )
            except Exception as e:
                _logger.exception("configure(action=generate_code) failed")
                return f"generate_code error: {e}"

        # ------------------------------------------------------------------
        # action="gtm" with sub-modes
        # ------------------------------------------------------------------
        if action == "gtm":
            try:
                if gtm_action == "list_usecases":
                    if not mcu:
                        raise ValueError(
                            "gtm_action='list_usecases' requires `mcu`."
                        )
                    root = (
                        Path(mcu_data_root) if mcu_data_root
                        else ctx.mcu_data_root
                    )
                    mcu_dir = root / "processors" / mcu
                    if not mcu_dir.exists():
                        raise FileNotFoundError(
                            f"MCU '{mcu}' not found under "
                            f"{root / 'processors'}"
                        )
                    sdk_dir = _resolve_platform_sdk_dir(
                        mcu_dir, platform_sdk_dir
                    )
                    uc_dir = sdk_dir / "gtm" / "use_cases" / "use_cases_mexes"
                    if not uc_dir.exists():
                        return []
                    return sorted(p.stem for p in uc_dir.glob("*.mex"))

                if gtm_action == "create_from_usecase":
                    missing = [
                        n for n, v in (
                            ("mcu", mcu),
                            ("sdk_version", sdk_version),
                            ("usecase", usecase),
                            ("output_dir", output_dir),
                        ) if not v
                    ]
                    if missing:
                        raise ValueError(
                            "gtm_action='create_from_usecase' requires: "
                            + ", ".join(missing)
                        )
                    _allowed_gtm_export = {
                        "ExportAll", "ExportSrc", "ExportHTML", "ExportMEX",
                    }
                    _export = (
                        export_kind
                        if export_kind in _allowed_gtm_export
                        else "ExportAll"
                    )
                    return gtm_create_from_usecase_impl(
                        ctx,
                        mcu=mcu,
                        sdk_version=sdk_version,
                        usecase=usecase,
                        output_dir=output_dir,
                        mcu_data_root=mcu_data_root,
                        platform_sdk_dir=platform_sdk_dir,
                        usecase_mex_path=usecase_mex_path,
                        export_kind=_export,
                        gtm_codegen=gtm_codegen,
                        config_name=config_name,
                        s32ct_launcher=s32ct_launcher,
                        launcher_ini=launcher_ini,
                    )

                # gtm_action == "edit" -- delegate to cli with tool_name=GTM
                return cli_impl(
                    ctx,
                    project_path=project_path,
                    empty_config=empty_config,
                    mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                    tool_name="GTM", enable_tool=enable_tool,
                    apply_use_case=apply_use_case,
                    set_values=set_values, get_values=get_values,
                    export_kind=export_kind, output_dir=output_dir,
                    data_dir=data_dir, extra_args=extra_args,
                    s32ct_launcher=s32ct_launcher,
                    launcher_ini=launcher_ini,
                    timeout_s=timeout_s,
                )
            except Exception as e:
                _logger.exception(
                    "configure(action=gtm, gtm_action=%s) failed", gtm_action,
                )
                return {
                    "exit_code": -1,
                    "summary": f"gtm error: {e}",
                }

        # ------------------------------------------------------------------
        # action="cli" or one of the per-component wrappers -- all funnel
        # through cli_impl. For wrappers we just pre-fill tool_name.
        # ------------------------------------------------------------------
        effective_tool_name = tool_name
        if action != "cli":
            mapped = _ACTION_TO_TOOL_NAME.get(action)
            if mapped is None:
                return {
                    "exit_code": -1,
                    "summary": f"Unknown configure action: {action!r}",
                }
            # Respect an explicit override only when the user actively passed
            # a different tool_name -- otherwise pre-fill from the action.
            if effective_tool_name is None:
                effective_tool_name = mapped

        try:
            return cli_impl(
                ctx,
                project_path=project_path,
                empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name=effective_tool_name, enable_tool=enable_tool,
                apply_use_case=apply_use_case,
                set_values=set_values, get_values=get_values,
                import_c=import_c,
                import_project=import_project, sdk_path=sdk_path,
                overwrite_with_sdk_sources=overwrite_with_sdk_sources,
                migrate_to_toolchain_version=migrate_to_toolchain_version,
                migrate_to_highest_version=migrate_to_highest_version,
                custom_copyright=custom_copyright,
                output_path_overrides=output_path_overrides,
                import_bin=import_bin, import_blob=import_blob,
                import_ab=import_ab, import_ddrc=import_ddrc,
                import_arxml=import_arxml, import_json=import_json,
                auto_align=auto_align,
                custom_pointers_addrs=custom_pointers_addrs,
                start_pointer_addr=start_pointer_addr,
                entry_pointer_addr=entry_pointer_addr,
                raw_binary=raw_binary,
                clock_config_data=clock_config_data,
                mini_paco_structure=mini_paco_structure,
                pre_defined_data=pre_defined_data,
                boot_device_id=boot_device_id,
                ivt_start_addr=ivt_start_addr,
                update_filepaths=update_filepaths,
                ivt_filter=ivt_filter,
                include_marker=include_marker,
                include_serial_boot_header=include_serial_boot_header,
                file_type=file_type,
                default_containers=default_containers,
                validate=validate,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher,
                launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("configure(action=%s) failed", action)
            return {
                "exit_code": -1,
                "summary": f"configure(action={action}) error: {e}",
            }
