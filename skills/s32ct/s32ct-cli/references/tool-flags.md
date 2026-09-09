# S32CT CLI - Per-tool flag matrix and worked examples

Companion reference for `s32ct-cli` (the `nxp_s32ct_execute_action(action_name="s32ct.configure_cli", params={...})`
dispatcher). Documents the full parameter surface, the deterministic
command build order, and one worked example per tool.

## Tool selection

| Name | Type | Description |
|------|------|-------------|
| `tool_name` | enum | `Pins` / `Clocks` / `Peripherals` / `DCD` / `IVT` / `eFUSE` / `GTM` / `QuadSPI` / `FFC` |
| `enable_tool` | bool | Defaults to `true` when `tool_name` is set; appends `-Enable` |

> **DCA / DCF are not separate `tool_name` values.** The S32CT DCD plugin
> registers a single `-HeadlessTool DCD` whose `CmdApplication` drives DCD,
> DCF (Device Configuration Format) and DCA (Device Configuration Area) and
> auto-selects the active variant from the loaded processor. To target DCF or
> DCA, use `tool_name="DCD"` (or the `dca` / `dcf` convenience actions) - the
> import / validate / export grammar is identical for all three.


## Mode selection (mutually exclusive)

| Name | Type | Description |
|------|------|-------------|
| `project_path` | string | Existing `.mex` to load via `-Load` |
| `empty_config` | bool | If `true`, start from `-EmptyConfig`. Requires `mcu` + `sdk_version` |
| `mcu` | string | MCU id (e.g. `S32E288`). Used with `empty_config` |
| `sdk_version` | string | SDK id (e.g. `PlatformSDK_S32ZE`). Required with `empty_config`; optional otherwise |
| `config_name` | string | Friendly configuration name - `-ConfigName` |

## Data-model edits and queries

| Name | Type | Used with | Maps to |
|------|------|-----------|---------|
| `apply_use_case` | string (.mex) | GTM | `-ApplyUseCase` |
| `set_values` | array of `key=value` | GTM (and any tool that supports it) | `-SetValue` |
| `get_values` | array of IDs | GTM (and any tool that supports it) | `-GetValue` |
| `import_c` | array of paths | Pins / Peripherals | `-ImportC` |
| `validate` | bool | DCD / IVT / FFC | `-ValidateConfiguration` |

## Peripherals tool helpers

| Name | Type | Maps to |
|------|------|---------|
| `import_project` | string | `-importProject` |
| `sdk_path` | string | `-sdkPath` |
| `overwrite_with_sdk_sources` | bool | `-overwriteWithSdkSources` |
| `migrate_to_toolchain_version` | bool | `-MigrateComponentsToToolchainVersion` |
| `migrate_to_highest_version` | bool | `-MigrateComponentsToHighestVersion` |

## Code-generation framework options (any tool)

| Name | Type | Maps to |
|------|------|---------|
| `custom_copyright` | string | `-CustomCopyright` |
| `output_path_overrides` | string | `-OutputPathOverrides` |

## Binary / blob / data imports

| Name | Type | Used with | Maps to |
|------|------|-----------|---------|
| `import_bin` | string | DCD / IVT / QuadSPI | `-ImportBin` |
| `import_blob` | string | IVT | `-ImportBlob` |
| `import_ab` | string | IVT | `-ImportAB` |
| `import_ddrc` | string | IVT | `-ImportDDRC` |
| `import_arxml` | array of paths | FFC | `-ImportARXML` |
| `import_json` | string | FFC | `-ImportJSON` |

## IVT / boot-image options

| Name | Type | Maps to |
|------|------|---------|
| `auto_align` | string (empty or hex addr) | `-AutoAlign [<addr>]` |
| `custom_pointers_addrs` | string `0x...,0x...` | `-CustomPointersAddrs` |
| `start_pointer_addr` | string (hex) | `-start_pointer_addr` |
| `entry_pointer_addr` | string (hex) | `-entry_pointer_addr` |
| `raw_binary` | string | `-raw_binary` |
| `clock_config_data` | string | `-clockConfigData` |
| `mini_paco_structure` | string | `-miniPacoStructure` |
| `pre_defined_data` | string | `-pre_defined_data` |
| `boot_device_id` | string | `-bootDeviceId` |
| `ivt_start_addr` | string | `-IvtStartAddr` |
| `update_filepaths` | enum (`relativeToCurrentMex` / `absolute` / `keepExisting`) | `-UpdateFilepaths` |
| `ivt_filter` | enum (`UnresolvedCustomPointers` / `All`) | `-filter` |
| `include_marker` | bool | `-includeMarker` |

## eFUSE options

| Name | Type | Maps to |
|------|------|---------|
| `include_serial_boot_header` | bool | `-IncludeSerialBootHeader` |

## FFC options

| Name | Type | Maps to |
|------|------|---------|
| `file_type` | enum (`all` / `Fss_Rem_Pm` / `Fss_Btm`) | `-FileType` |
| `default_containers` | bool | `-defaultContainers` |

## Export

| Name | Type | Maps to |
|------|------|---------|
| `export_kind` | enum | `-<ExportKind>` |
| `output_dir` | string | argument of the export verb |

`export_kind one of: ExportAll, ExportSrc, ExportHTML, ExportCSV, ExportRegisters,
ExportMEX, ExportBin, ExportC, ExportBlob, ExportAB, ExportPointers,
ExportDDRC, ExportFssFw, ExportConfig, ExportELF, ExportARXML, ExportJSON`.

## Launcher / Eclipse plumbing

| Name | Type | Description |
|------|------|-------------|
| `data_dir` | string | `-data <workspace>` (auto-injected on `IllegalStateException` retry) |
| `extra_args` | array of strings | Escape hatch - appended verbatim |
| `s32ct_launcher` | string | Launcher executable override |
| `launcher_ini` | string | `tools.ini` override |
| `timeout_s` | int (default 600) | Process timeout |

## Deterministic command build order

```
<launcher> --launcher.ini=<ini> -application com.nxp.swtools.framework.application -noSplash
  [-data <data_dir>]
  [-Load <project_path>] | [-EmptyConfig -MCU <mcu> -SDKVersion <sdk_version>]
  [-ConfigName <config_name>]
  [-CustomCopyright <...>] [-OutputPathOverrides <...>]
  [-HeadlessTool <tool_name>]
  [-Enable]                                # if enable_tool
  [-ImportC <paths>]
  [-importProject <...> [-sdkPath <...>] [-overwriteWithSdkSources]]
  [-MigrateComponentsToToolchainVersion]
  [-MigrateComponentsToHighestVersion]
  [-ImportBin <...>] [-ImportBlob <...> [-IvtStartAddr <...>] [-bootDeviceId <...>]]
  [-ImportAB <...>] [-ImportDDRC <...>]
  [-ImportARXML <paths>] [-ImportJSON <...>]
  [-ApplyUseCase <...>]
  [-SetValue k1=v1 k2=v2 ...]
  [-GetValue id1 id2 ...]
  [-ValidateConfiguration]
  [-AutoAlign [<addr>]] [-CustomPointersAddrs <...>]
  [-start_pointer_addr <...>] [-entry_pointer_addr <...>]
  [-raw_binary <...>] [-clockConfigData <...>] [-miniPacoStructure <...>]
  [-pre_defined_data <...>] [-UpdateFilepaths <...>] [-filter <...>]
  [-includeMarker]
  [-IncludeSerialBootHeader]
  [-FileType <...>] [-defaultContainers]
  [-<ExportKind> <output_dir>]
  [<extra_args ...>]
```

## Worked examples

### 1. Enable extra TOM channels on an existing GTM project and save
```json
{
  "action": "cli",
  "project_path": "C:/out/gtm_demo/S32E2XX.mex",
  "tool_name": "GTM",
  "set_values": [
    "tom0_ch1_dynamic_entry=true", "tom0_ch1_en=true",
    "tom1_ch2_dynamic_entry=true", "tom1_ch2_en=true",
    "tom1_ch3_dynamic_entry=true", "tom1_ch3_en=true"
  ],
  "export_kind": "ExportMEX",
  "output_dir": "C:/out/gtm_demo"
}
```

### 2. Read back current ATOM channel parameters (GTM)
```json
{
  "action": "cli",
  "project_path": "C:/out/gtm_demo/S32E2XX.mex",
  "tool_name": "GTM",
  "get_values": ["atom0_ch2_en", "atom0_ch2_period", "atom0_ch2_duty_cycle"]
}
```

### 3. Apply a use-case AND tweak a value in one run (GTM)
```json
{
  "action": "cli",
  "empty_config": true,
  "mcu": "S32E288",
  "sdk_version": "PlatformSDK_S32ZE",
  "tool_name": "GTM",
  "apply_use_case": "C:/uc/atom_inverted_pwm.mex",
  "set_values": ["gtm_codegen=true", "atom0_ch2_period=0xBB80"],
  "export_kind": "ExportAll",
  "output_dir": "C:/out/gtm_custom"
}
```

### 4. Validate an existing IVT configuration headlessly
```json
{
  "action": "cli",
  "project_path": "C:/projects/bldc/bldc.mex",
  "tool_name": "IVT",
  "validate": true
}
```

### 5. Import a binary IVT image and export C + Blob
```json
{
  "action": "cli",
  "empty_config": true,
  "mcu": "S32S247TV",
  "sdk_version": "s32sdk_s32s_rtm_100",
  "tool_name": "IVT",
  "import_bin": "C:/Input/ivt_image.bin",
  "auto_align": "0x34000000",
  "export_kind": "ExportAll",
  "output_dir": "C:/Output/ivt_export"
}
```

### 6. Export application bootloader image (IVT)
```json
{
  "action": "cli",
  "project_path": "C:/projects/boot/boot.mex",
  "tool_name": "IVT",
  "raw_binary": "C:/Input/app_boot_raw.bin",
  "start_pointer_addr": "0x34300000",
  "entry_pointer_addr": "0x34300000",
  "export_kind": "ExportAB",
  "output_dir": "C:/Output/app_boot"
}
```

### 7. Export eFUSE configuration in ELF format with serial-boot header
```json
{
  "action": "cli",
  "project_path": "C:/projects/efuse/efuse.mex",
  "tool_name": "eFUSE",
  "include_serial_boot_header": true,
  "export_kind": "ExportELF",
  "output_dir": "C:/Output/efuse"
}
```

### 8. FFC: import ARXML, export JSON
```json
{
  "action": "cli",
  "project_path": "C:/projects/ffc/ffc.mex",
  "tool_name": "FFC",
  "import_arxml": ["C:/arxml/Fss_Rem_Pm.ecvd", "C:/arxml/Fss_Btm.ecvd"],
  "export_kind": "ExportJSON",
  "output_dir": "C:/Output/ffc_json"
}
```

### 9. Peripherals: import toolchain project, overwrite with SDK sources

> **Warning - irreversible overwrite of project sources.**
> `overwrite_with_sdk_sources: true` replaces the existing sources in the
> imported project with the SDK copies. Local modifications in the
> overwritten files are lost, there is no prompt, and no backup is
> written. Confirm with the user and commit or back up
> `import_project` before running this. Omit the flag (or set it to
> `false`) to import without touching existing sources.

```json
{
  "action": "cli",
  "empty_config": true,
  "mcu": "S32K344",
  "sdk_version": "s32sdk_s32k3_rtm_402",
  "tool_name": "Peripherals",
  "import_project": "C:/projects/my_motor_ctrl",
  "sdk_path": "C:/NXP/sdk_manifest",
  "overwrite_with_sdk_sources": true,
  "export_kind": "ExportSrc",
  "output_dir": "C:/projects/my_motor_ctrl/generated"
}
```

### 10. Pins: regenerate with custom copyright header
```json
{
  "action": "cli",
  "project_path": "C:/projects/my_motor_ctrl/my_motor_ctrl.mex",
  "tool_name": "Pins",
  "custom_copyright": "C:/templates/copyright_header.txt",
  "export_kind": "ExportSrc",
  "output_dir": "C:/projects/my_motor_ctrl/board/generated/pins"
}
```

## Notes for agent reasoning

- Only one tool block runs per invocation. Multi-tool workflows require
  one call per tool.
- Data-model IDs live in the per-tool CLI documentation pages (e.g.
  `topics/command_line_execution_-_gtm_tool.html`). Confirm the exact id
  from the docs before invoking `-SetValue`.
- `extra_args` is the escape hatch for any option not yet wrapped -
  prefer typed parameters when available.
- Distribution portability: `desktop` uses `toolsc.exe -noSplash
  --launcher.ini {ini} -application {app} -consoleLog {tool commands}`;
  `integrated_s32ds` uses `s32dsc.exe -noSplash --launcher.ini {ini}
  -application {app} -consoleLog -data {ws} {tool commands}`. The
  `-data <workspace>` is mandatory on `integrated_s32ds`; the MCP
  injects a stable per-host workspace automatically (override per call
  via `data_dir`). See the `s32ct-distributions` skill for context.
- Editing pointer addresses inside `<ivt_pointer>` rows via `-SetValue`
  is unsupported - that command writes bitfield `<setting>` nodes only.
  Direct XML edits are required; see `s32ct-ivt-build-blob`.
