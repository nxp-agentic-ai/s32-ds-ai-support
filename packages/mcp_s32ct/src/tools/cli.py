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

"""``cli`` - full-surface S32 CT headless CLI driver."""
import logging
from typing import Literal, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import S32CTContext, cli_impl

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_cli_tool(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    @server.tool(
        name="cli",
        description=(
            "Generic S32 Configuration Tools headless CLI - full surface across all 9 "
            "tools (Pins, Clocks, Peripherals, DCD, IVT, eFUSE, GTM, QuadSPI, FFC). "
            "Portable across both S32CT distributions: the launcher prefix is "
            "auto-selected per the active install (`desktop` -> `toolsc.exe` form; "
            "`integrated_s32ds` -> `s32dsc.exe` form with mandatory `-data <ws>`). "
            "See the `s32ct-distributions` skill for details. "
            "Supports any documented chain: -Load <mex> OR -EmptyConfig+-MCU+-SDKVersion, "
            "optional -HeadlessTool/-Enable/-ApplyUseCase/-SetValue/-GetValue/-ImportC, "
            "-importProject/-sdkPath/-overwriteWithSdkSources, "
            "-ImportBin/-ImportBlob/-ImportAB/-ImportDDRC/-ImportARXML/-ImportJSON, "
            "IVT pointer/raw-binary args, eFUSE/FFC flags, -Validate, and any export verb "
            "(ExportAll/Src/HTML/CSV/Registers/MEX/Bin/C/Blob/AB/Pointers/DDRC/FssFw/"
            "Config/ELF/ARXML/JSON). Returns "
            "{exit_code, command, stdout_tail, stderr_tail, values, summary}."
        ),
    )
    def cli(
        # Mode
        project_path: Optional[str] = None,
        empty_config: bool = False,
        mcu: Optional[str] = None,
        sdk_version: Optional[str] = None,
        config_name: Optional[str] = None,
        # Tool selection
        tool_name: Optional[Literal[
            "Pins", "Clocks", "Peripherals", "DCD", "IVT", "eFUSE", "GTM", "QuadSPI", "FFC"
        ]] = None,
        enable_tool: Optional[bool] = None,
        # Generic edits / queries
        apply_use_case: Optional[str] = None,
        set_values: Optional[list[str]] = None,
        get_values: Optional[list[str]] = None,
        # Pins / Peripherals
        import_c: Optional[list[str]] = None,
        import_project: Optional[str] = None,
        sdk_path: Optional[str] = None,
        overwrite_with_sdk_sources: bool = False,
        migrate_to_toolchain_version: bool = False,
        migrate_to_highest_version: bool = False,
        # Code-gen framework
        custom_copyright: Optional[str] = None,
        output_path_overrides: Optional[str] = None,
        # Imports (binary / blob / ARXML / JSON)
        import_bin: Optional[str] = None,
        import_blob: Optional[str] = None,
        import_ab: Optional[str] = None,
        import_ddrc: Optional[str] = None,
        import_arxml: Optional[list[str]] = None,
        import_json: Optional[str] = None,
        # IVT / boot-image params
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
        # eFUSE
        include_serial_boot_header: bool = False,
        # FFC
        file_type: Optional[Literal["all", "Fss_Rem_Pm", "Fss_Btm"]] = None,
        default_containers: bool = False,
        # Validate
        validate: bool = False,
        # Export
        export_kind: Optional[Literal[
            "ExportAll", "ExportSrc", "ExportHTML", "ExportCSV", "ExportRegisters", "ExportMEX",
            "ExportBin", "ExportC", "ExportBlob", "ExportAB", "ExportPointers", "ExportDDRC", "ExportFssFw",
            "ExportConfig", "ExportELF",
            "ExportARXML", "ExportJSON",
        ]] = None,
        output_dir: Optional[str] = None,
        # Launcher
        data_dir: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> dict:
        try:
            return cli_impl(
                ctx,
                project_path=project_path,
                empty_config=empty_config,
                mcu=mcu,
                sdk_version=sdk_version,
                config_name=config_name,
                tool_name=tool_name,
                enable_tool=enable_tool,
                apply_use_case=apply_use_case,
                set_values=set_values,
                get_values=get_values,
                import_c=import_c,
                import_project=import_project,
                sdk_path=sdk_path,
                overwrite_with_sdk_sources=overwrite_with_sdk_sources,
                migrate_to_toolchain_version=migrate_to_toolchain_version,
                migrate_to_highest_version=migrate_to_highest_version,
                custom_copyright=custom_copyright,
                output_path_overrides=output_path_overrides,
                import_bin=import_bin,
                import_blob=import_blob,
                import_ab=import_ab,
                import_ddrc=import_ddrc,
                import_arxml=import_arxml,
                import_json=import_json,
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
                export_kind=export_kind,
                output_dir=output_dir,
                data_dir=data_dir,
                extra_args=extra_args,
                s32ct_launcher=s32ct_launcher,
                launcher_ini=launcher_ini,
                timeout_s=timeout_s,
            )
        except Exception as e:
            _logger.exception("cli failed")
            return {"exit_code": -1, "summary": f"cli error: {e}"}
