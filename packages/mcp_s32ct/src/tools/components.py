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

"""Per-tool wrappers over the generic S32CT CLI.

Each function exposes only the flags that apply to its specific S32 CT tool
(Pins / Clocks / Peripherals / DCD / IVT / eFUSE / GTM / QuadSPI / FFC),
delegating to :func:`nxp.mcp.s32ct.tools.launcher.cli_impl` with the
matching ``tool_name``. These per-tool surfaces are easier for an agent to
reason about than the full 50-parameter ``cli``.
"""
import logging
from typing import Literal, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from pathlib import Path

from nxp.mcp.s32ct.tools.launcher import (
    S32CTContext,
    _resolve_platform_sdk_dir,
    cli_impl,
    gtm_create_from_usecase_impl,
)

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_component_tools(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    # ------------------------------------------------------------------ Pins
    @server.tool(
        name="pins",
        description=(
            "Per-tool wrapper for the Pins tool of S32 Configuration Tools. "
            "Surfaces only Pins-relevant flags (import_c, custom_copyright, "
            "output_path_overrides) plus generic mode/export. Delegates to "
            "cli with tool_name=Pins."
        ),
    )
    def pins(
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        enable_tool: Optional[bool] = None,
        import_c: Optional[list[str]] = None,
        custom_copyright: Optional[str] = None,
        output_path_overrides: Optional[str] = None,
        export_kind: Optional[Literal[
            "ExportAll", "ExportSrc", "ExportCSV", "ExportHTML", "ExportRegisters", "ExportMEX"
        ]] = None,
        output_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> dict:
        try:
            return cli_impl(
                ctx,
                project_path=project_path, empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name="Pins", enable_tool=enable_tool,
                import_c=import_c,
                custom_copyright=custom_copyright,
                output_path_overrides=output_path_overrides,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher, launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("pins failed")
            return {"exit_code": -1, "summary": f"pins error: {e}"}

    # ---------------------------------------------------------------- Clocks
    @server.tool(
        name="clocks",
        description=(
            "Per-tool wrapper for the Clocks tool. Surfaces clock-relevant flags. "
            "Delegates to cli with tool_name=Clocks."
        ),
    )
    def clocks(
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        enable_tool: Optional[bool] = None,
        custom_copyright: Optional[str] = None,
        output_path_overrides: Optional[str] = None,
        export_kind: Optional[Literal[
            "ExportAll", "ExportSrc", "ExportHTML", "ExportRegisters", "ExportMEX"
        ]] = None,
        output_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> dict:
        try:
            return cli_impl(
                ctx,
                project_path=project_path, empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name="Clocks", enable_tool=enable_tool,
                custom_copyright=custom_copyright,
                output_path_overrides=output_path_overrides,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher, launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("clocks failed")
            return {"exit_code": -1, "summary": f"clocks error: {e}"}

    # ----------------------------------------------------------- Peripherals
    @server.tool(
        name="peripherals",
        description=(
            "Per-tool wrapper for the Peripherals tool. Surfaces import_c, "
            "import_project, sdk_path, overwrite_with_sdk_sources, migrate_* verbs, "
            "plus mode/export. Delegates to cli with tool_name=Peripherals."
        ),
    )
    def peripherals(
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        enable_tool: Optional[bool] = None,
        import_c: Optional[list[str]] = None,
        import_project: Optional[str] = None,
        sdk_path: Optional[str] = None,
        overwrite_with_sdk_sources: bool = False,
        migrate_to_toolchain_version: bool = False,
        migrate_to_highest_version: bool = False,
        custom_copyright: Optional[str] = None,
        output_path_overrides: Optional[str] = None,
        export_kind: Optional[Literal["ExportAll", "ExportSrc", "ExportHTML", "ExportMEX"]] = None,
        output_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> dict:
        try:
            return cli_impl(
                ctx,
                project_path=project_path, empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name="Peripherals", enable_tool=enable_tool,
                import_c=import_c,
                import_project=import_project, sdk_path=sdk_path,
                overwrite_with_sdk_sources=overwrite_with_sdk_sources,
                migrate_to_toolchain_version=migrate_to_toolchain_version,
                migrate_to_highest_version=migrate_to_highest_version,
                custom_copyright=custom_copyright,
                output_path_overrides=output_path_overrides,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher, launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("peripherals failed")
            return {"exit_code": -1, "summary": f"peripherals error: {e}"}

    # -------------------------------------------------------------------- DCD
    @server.tool(
        name="dcd",
        description=(
            "Per-tool wrapper for the DCD tool. Surfaces import_bin, validate, and "
            "DCD-specific exports. Delegates to cli with tool_name=DCD."
        ),
    )
    def dcd(
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        import_bin: Optional[str] = None,
        validate: bool = False,
        export_kind: Optional[Literal["ExportAll", "ExportBin", "ExportC", "ExportMEX"]] = None,
        output_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> dict:
        try:
            return cli_impl(
                ctx,
                project_path=project_path, empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name="DCD",
                import_bin=import_bin, validate=validate,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher, launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("dcd failed")
            return {"exit_code": -1, "summary": f"dcd error: {e}"}

    # -------------------------------------------------------------------- IVT
    @server.tool(
        name="ivt",
        description=(
            "Per-tool wrapper for the IVT tool. Surfaces the full IVT/boot-image "
            "surface: import_bin/blob/ab/ddrc, pointer & raw-binary args, auto_align, "
            "custom_pointers_addrs, update_filepaths, ivt_filter, include_marker, "
            "validate, plus IVT-specific exports. Delegates to cli with "
            "tool_name=IVT."
        ),
    )
    def ivt(
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        import_bin: Optional[str] = None,
        import_blob: Optional[str] = None,
        import_ab: Optional[str] = None,
        import_ddrc: Optional[str] = None,
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
        update_filepaths: Optional[Literal["relativeToCurrentMex", "absolute", "keepExisting"]] = None,
        ivt_filter: Optional[Literal["UnresolvedCustomPointers", "All"]] = None,
        include_marker: bool = False,
        validate: bool = False,
        export_kind: Optional[Literal[
            "ExportAll", "ExportBin", "ExportC", "ExportBlob",
            "ExportAB", "ExportPointers", "ExportDDRC", "ExportFssFw", "ExportMEX",
        ]] = None,
        output_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> dict:
        try:
            return cli_impl(
                ctx,
                project_path=project_path, empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name="IVT",
                import_bin=import_bin, import_blob=import_blob,
                import_ab=import_ab, import_ddrc=import_ddrc,
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
                validate=validate,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher, launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("ivt failed")
            return {"exit_code": -1, "summary": f"ivt error: {e}"}

    # ------------------------------------------------------------------ eFUSE
    @server.tool(
        name="efuse",
        description=(
            "Per-tool wrapper for the eFUSE tool. Surfaces include_serial_boot_header "
            "and eFUSE-specific exports. Delegates to cli with tool_name=eFUSE."
        ),
    )
    def efuse(
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        include_serial_boot_header: bool = False,
        export_kind: Optional[Literal["ExportAll", "ExportConfig", "ExportELF", "ExportMEX"]] = None,
        output_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> dict:
        try:
            return cli_impl(
                ctx,
                project_path=project_path, empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name="eFUSE",
                include_serial_boot_header=include_serial_boot_header,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher, launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("efuse failed")
            return {"exit_code": -1, "summary": f"efuse error: {e}"}

    # -------------------------------------------------------------------- GTM
    @server.tool(
        name="gtm",
        description=(
            "GTM tool facade with three actions selected by `action`:\n"
            "  - `edit` (default): per-tool wrapper over the GTM tool on an "
            "existing .mex; surfaces apply_use_case, set_values, get_values, "
            "and GTM-specific exports. Delegates to cli with tool_name=GTM.\n"
            "  - `list_usecases`: read-only discovery; returns the GTM "
            "use-case names available for `mcu` under the MCU data package. "
            "Requires only `mcu`.\n"
            "  - `create_from_usecase`: bootstrap a new GTM configuration via "
            "-EmptyConfig + -MCU + -SDKVersion, apply a predefined GTM "
            "use-case .mex from the MCU data package, and export the "
            "generated code. Requires `mcu`, `sdk_version`, `usecase`, and "
            "`output_dir`.\n"
            "Use-case .mex files resolve to <mcu_data_root>/processors/<mcu>"
            "/<PlatformSDK_*>/gtm/use_cases/use_cases_mexes/<usecase>.mex. "
            "Portable across both S32CT distributions; the MCU data package "
            "shipped with each may differ -- discover use-cases via "
            "action=`list_usecases` rather than assuming a fixed file layout. "
            "See the `s32ct-distributions` skill."
        ),
    )
    def gtm(
        action: Literal["edit", "list_usecases", "create_from_usecase"] = "edit",
        # --- shared / edit-mode args ---
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        enable_tool: Optional[bool] = None,
        apply_use_case: Optional[str] = None,
        set_values: Optional[list[str]] = None,
        get_values: Optional[list[str]] = None,
        export_kind: Optional[Literal["ExportAll", "ExportSrc", "ExportHTML", "ExportMEX"]] = None,
        output_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
        # --- args for list_usecases + create_from_usecase ---
        mcu_data_root: Optional[str] = None,
        platform_sdk_dir: Optional[str] = None,
        # --- args for create_from_usecase only ---
        usecase: Optional[str] = None,
        usecase_mex_path: Optional[str] = None,
        gtm_codegen: bool = True,
    ):
        try:
            if action == "list_usecases":
                if not mcu:
                    raise ValueError("action='list_usecases' requires `mcu`.")
                root = Path(mcu_data_root) if mcu_data_root else ctx.mcu_data_root
                mcu_dir = root / "processors" / mcu
                if not mcu_dir.exists():
                    raise FileNotFoundError(
                        f"MCU '{mcu}' not found under {root / 'processors'}"
                    )
                sdk_dir = _resolve_platform_sdk_dir(mcu_dir, platform_sdk_dir)
                uc_dir = sdk_dir / "gtm" / "use_cases" / "use_cases_mexes"
                if not uc_dir.exists():
                    return []
                return sorted(p.stem for p in uc_dir.glob("*.mex"))

            if action == "create_from_usecase":
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
                        "action='create_from_usecase' requires: "
                        + ", ".join(missing)
                    )
                _allowed = {"ExportAll", "ExportSrc", "ExportHTML", "ExportMEX"}
                _export = export_kind if export_kind in _allowed else "ExportAll"
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

            # action == "edit" -- original behaviour
            return cli_impl(
                ctx,
                project_path=project_path, empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name="GTM", enable_tool=enable_tool,
                apply_use_case=apply_use_case,
                set_values=set_values, get_values=get_values,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher, launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("gtm failed")
            return {"exit_code": -1, "summary": f"gtm error: {e}"}

    # ---------------------------------------------------------------- QuadSPI
    @server.tool(
        name="quadspi",
        description=(
            "Per-tool wrapper for the QuadSPI tool. Surfaces import_bin and "
            "QuadSPI-specific exports. Delegates to cli with tool_name=QuadSPI."
        ),
    )
    def quadspi(
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        import_bin: Optional[str] = None,
        export_kind: Optional[Literal["ExportAll", "ExportBin", "ExportC", "ExportMEX"]] = None,
        output_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> dict:
        try:
            return cli_impl(
                ctx,
                project_path=project_path, empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name="QuadSPI", import_bin=import_bin,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher, launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("quadspi failed")
            return {"exit_code": -1, "summary": f"quadspi error: {e}"}

    # -------------------------------------------------------------------- FFC
    @server.tool(
        name="ffc",
        description=(
            "Per-tool wrapper for the FFC tool. Surfaces import_arxml, import_json, "
            "file_type, default_containers, validate, and FFC-specific exports. "
            "Delegates to cli with tool_name=FFC."
        ),
    )
    def ffc(
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        import_arxml: Optional[list[str]] = None,
        import_json: Optional[str] = None,
        file_type: Optional[Literal["all", "Fss_Rem_Pm", "Fss_Btm"]] = None,
        default_containers: bool = False,
        validate: bool = False,
        export_kind: Optional[Literal["ExportAll", "ExportARXML", "ExportJSON", "ExportMEX"]] = None,
        output_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> dict:
        try:
            return cli_impl(
                ctx,
                project_path=project_path, empty_config=empty_config,
                mcu=mcu, sdk_version=sdk_version, config_name=config_name,
                tool_name="FFC",
                import_arxml=import_arxml, import_json=import_json,
                file_type=file_type, default_containers=default_containers,
                validate=validate,
                export_kind=export_kind, output_dir=output_dir,
                data_dir=data_dir, extra_args=extra_args,
                s32ct_launcher=s32ct_launcher, launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("ffc failed")
            return {"exit_code": -1, "summary": f"ffc error: {e}"}
