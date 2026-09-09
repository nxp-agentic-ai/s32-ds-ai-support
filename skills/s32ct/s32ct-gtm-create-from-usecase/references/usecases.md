# s32ct-gtm-create-from-usecase - Use-Cases and Examples

Deep-dive companion to the parent skill. Covers the MCU / Platform-SDK
folder layout, the known GTM use-case catalogue, and four worked
scenarios.

## Table of Contents

- [MCU data package layout](#mcu-data-package-layout)
- [Resolving the use-case `.mex`](#resolving-the-use-case-mex)
- [Known use-cases for `S32E288 / PlatformSDK_S32ZE`](#known-use-cases-for-s32e288--platformsdk_s32ze)
- [Example 1 - ATOM Inverted PWM, full export](#example-1--atom-inverted-pwm-full-export)
- [Example 2 - TOM Simple PWM, source only, custom name](#example-2--tom-simple-pwm-source-only-custom-name)
- [Example 3 - Save the new configuration as a `.mex`](#example-3--save-the-new-configuration-as-a-mex)
- [Example 4 - Direct path to a use-case template](#example-4--direct-path-to-a-use-case-template)
- [Notes for agent reasoning](#notes-for-agent-reasoning)

## MCU data package layout

The MCU data root is typically:

```
C:/ProgramData/NXP/mcu_data_<release>/    # desktop distribution
<S32DS install>/eclipse/mcu_data/         # integrated_s32ds distribution
```

Under it, GTM use-case templates live at:

```
<mcu_data_root>/processors/<MCU>/<PlatformSDK_*>/gtm/use_cases/use_cases_mexes/<usecase>.mex
```

The `<PlatformSDK_*>` subfolder name is MCU-family specific (e.g.
`PlatformSDK_S32ZE` for the S32E / S32Z family). Do **not** hardcode it
in agent code - the skill auto-detects the folder when there is exactly
one candidate, and errors out asking the caller to disambiguate when
there are multiple.

## Resolving the use-case `.mex`

1. If the caller passes `usecase_mex_path=<abs path>`, that path wins
   and the auto-resolution below is skipped.
2. Otherwise the skill builds:

   ```
   <mcu_data_root>/processors/<mcu>/<platform_sdk_dir>/gtm/use_cases/use_cases_mexes/<usecase>.mex
   ```

   with `platform_sdk_dir` provided explicitly or auto-detected.
3. The resolved path must exist and end in `.mex`; otherwise the skill
   returns the resolved path together with a listing of available
   use-cases in that folder.

## Known use-cases for `S32E288 / PlatformSDK_S32ZE`

The use-case *name* the caller passes is the file base-name in
`use_cases_mexes/` (without `.mex`). Representative catalogue:

- ATOM: `atom_inverted_pwm`, `atom_ocu_mode`, `atom_simple_pwm`
- TOM: `tom_inverted_pwm`, `tom_ocu_mode`, `tom_simple_pwm`
- TIM edge counting: `tim_edge_count_internal`,
  `tim_edge_count_external`
- TIM edge detection: `tim_edge_detect_internal`,
  `tim_edge_detect_external`
- TIM signal measurement: `tim_signal_measurement_internal`,
  `tim_signal_measurement_external`
- TIM timestamp: `tim_timestamp_internal`, `tim_timestamp_external`
- Time base / clocks / CCM: `tbu_free_running`,
  `ccm_enable_cluster0`, `clock_configuration`

Different MCUs may ship a different set of use-cases (and even a
different `PlatformSDK_*` folder name). Always discover the
authoritative list via:

```python
nxp_s32ct_execute_action(
    action_name="s32ct.gtm_list_usecases",
    params={
        "mcu": "<MCU>",
    },
)
```

## Example 1 - ATOM Inverted PWM, full export

**Inputs**

```python
nxp_s32ct_execute_action(
    action_name="s32ct.gtm_create_from_usecase",
    params={
        "mcu": "S32E288",
        "sdk_version": "s32sdk_s32ze_rtm_200",
        "usecase": "atom_inverted_pwm",
        "output_dir": r"C:/out/s32e288_atom_inverted_pwm",
    },
)
```

**Resolved use-case `.mex`**

```
C:/ProgramData/NXP/mcu_data_25.12/processors/S32E288/PlatformSDK_S32ZE/gtm/use_cases/use_cases_mexes/atom_inverted_pwm.mex
```

**Resolved CLI (desktop distribution)**

Windows (`cmd.exe`) - line continuation is `^`:

```bat
toolsc.exe -noSplash --launcher.ini <tools.ini> ^
  -application com.nxp.swtools.framework.application -consoleLog ^
  -EmptyConfig ^
  -MCU S32E288 ^
  -SDKVersion s32sdk_s32ze_rtm_200 ^
  -HeadlessTool GTM -Enable ^
  -ApplyUseCase "C:\ProgramData\NXP\mcu_data_25.12\processors\S32E288\PlatformSDK_S32ZE\gtm\use_cases\use_cases_mexes\atom_inverted_pwm.mex" ^
  -SetValue gtm_codegen=true ^
  -ExportAll "C:\out\s32e288_atom_inverted_pwm"
```

Linux / macOS (`sh`/`bash`) - line continuation is `\`, and the launcher
has no `.exe` suffix:

```sh
toolsc -noSplash --launcher.ini <tools.ini> \
  -application com.nxp.swtools.framework.application -consoleLog \
  -EmptyConfig \
  -MCU S32E288 \
  -SDKVersion s32sdk_s32ze_rtm_200 \
  -HeadlessTool GTM -Enable \
  -ApplyUseCase "/opt/nxp/mcu_data_25.12/processors/S32E288/PlatformSDK_S32ZE/gtm/use_cases/use_cases_mexes/atom_inverted_pwm.mex" \
  -SetValue gtm_codegen=true \
  -ExportAll "/out/s32e288_atom_inverted_pwm"
```

The MCP dispatcher builds this command line for you and picks the right
launcher per platform and distribution - see `s32ct-distributions`. The
raw forms above are shown only for diagnosis.

**Expected status**

```
GTM use-case 'atom_inverted_pwm' applied for S32E288 (s32sdk_s32ze_rtm_200).
ExportAll -> C:\out\s32e288_atom_inverted_pwm
```

> **Warning - exports overwrite files in `output_dir`.** Every example
> below writes generated artifacts (`*.c`, `*.h`, `*.html`, and for
> `ExportMEX` a `.mex`) into the directory you name, replacing any
> same-named files already there with no prompt and no backup. Point
> `output_dir` at a dedicated generated-output folder, confirm the
> resolved path with the user, and commit or back up anything valuable
> in that directory before re-running.

## Example 2 - TOM Simple PWM, source only, custom name

```python
nxp_s32ct_execute_action(
    action_name="s32ct.gtm_create_from_usecase",
    params={
        "mcu": "S32E288",
        "sdk_version": "s32sdk_s32ze_rtm_200",
        "usecase": "tom_simple_pwm",
        "output_dir": r"C:/projects/bldc_demo/board/generated",
        "export_kind": "ExportSrc",
        "config_name": "bldc_gtm_init",
    },
)
```

## Example 3 - Save the new configuration as a `.mex`

```python
nxp_s32ct_execute_action(
    action_name="s32ct.gtm_create_from_usecase",
    params={
        "mcu": "S32E288",
        "sdk_version": "s32sdk_s32ze_rtm_200",
        "usecase": "tim_edge_count_internal",
        "output_dir": r"C:/out/bldc_gtm",
        "export_kind": "ExportMEX",
    },
)
```

The exported `.mex` can later be reopened in S32CT or fed to
`nxp_s32ct_execute_action(action_name="s32ct.generate_code", params={...})` for further scoped
regeneration.

## Example 4 - Direct path to a use-case template

```python
nxp_s32ct_execute_action(
    action_name="s32ct.gtm_create_from_usecase",
    params={
        "mcu": "S32E288",
        "sdk_version": "s32sdk_s32ze_rtm_200",
        "usecase": "atom_inverted_pwm",            # informational only
        "usecase_mex_path": r"D:/templates/my_custom_atom_inverted_pwm.mex",
        "output_dir": r"C:/out/custom",
    },
)
```

When `usecase_mex_path` is supplied, it takes precedence over the
`mcu_data_root` / `platform_sdk_dir` / `usecase` resolution chain.

## Notes for agent reasoning

- `gtm_codegen=true` is the recommended default: the GTM Tool emits C
  code directly (documented "GTM Drivers Code Generation" mode). Set
  `gtm_codegen=false` only if the user explicitly wants the Peripherals
  Tool preset workflow.
- A successful return confirms *generation*, not *compilation*. Chain
  with a build skill to verify.
- This skill is conceptually a *superset* of `s32ct-generate-code` for
  the GTM tool only: it adds use-case application and empty-config
  bootstrap. For non-GTM tools, or when an existing `.mex` already
  exists, prefer `s32ct-generate-code`.
- Portable across both S32CT distributions (`desktop` and
  `integrated_s32ds`). The MCU data package shipped with each
  distribution may differ - always discover use-cases via
  `s32ct.gtm_list_usecases` rather than assuming a fixed layout.
  See `s32ct-distributions`.
