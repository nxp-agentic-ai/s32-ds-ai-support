# Authoring procedure: the 5-source rule and 7-step recipe

Extended detail for authoring driver `<instance>` blocks from scratch
against the Peripherals tool of a `.mex`. Read after the main SKILL.md
when actually authoring a driver you have not previously hand-written.

## The 5-source rule

To emit a driver `<instance>` you need information from five different
places. Inventing values from just one source is the #1 cause of failed
validation.

| # | Source | Question it answers |
|---|---|---|
| 1 | `.component` schema at `<S32DS_INSTALL>/eclipse/mcu_data/components/<PLATFORM_SDK>/<driver_folder>/<driver_folder>.component` | What's the container hierarchy? Which settings/arrays exist? Which are `min_expr="1"` (required)? What's the `<integer id="ModuleId">`? |
| 2 | `<dynamic_enum>` refs in the `.component` + the resource tables they point at: `<S32DS_INSTALL>/eclipse/mcu_data/processors/<MCU>/<PLATFORM_SDK>/<PACKAGE>/resource_tables/[RTD/]<Driver>.xml` | What are the exact allowed enum values (case-sensitive - `LPSPI_0` vs `LPSPI0`, `LPUART_IP` vs `LPUART_6`, `MASTER` vs `LIN_MASTER_NODE`, `BL_13` vs `BREAK_13_BITS`, `P<N>_ChanNum<N>` vs `AN_<N>`)? Driver-name -> resource-table-file mapping is not 1:1 - read the `<dynamic_enum>` reference in the `.component` to discover which table file to load. |
| 3 | `.component` `<quick_selection>` blocks | What does the GUI write when the default-config button is pressed? Mirror these defaults - they are guaranteed valid. |
| 4 | A real RTD example `.mex` for the same driver at `<S32DS_INSTALL>/S32DS/software/<PLATFORM_SDK>/RTD/<Driver>_<RTD_VERSION>/examples/S32DS/<MCU_FAMILY>/<Example>/<Example>.mex` | What is the canonical XML shape that S32CT actually accepts? Which container holds which setting? What are the cross-reference path formats? |
| 5 | The user's existing `.mex` (and any `<MCU>_default.mex` template) | What does the rest of the `.mex` expect? Specifically: which `McuClockReferencePoint_*` entries exist for `LinClockRef` / `CanCpuClockRef` to point at? |

Always cross-check source 1 against source 4 - the RTD example is the
only authoritative answer for what XML actually validates.

## The 7-step recipe

```text
1. Inventory routed peripherals (read from existing Pins-tool entries in .mex).
2. For each requested driver, look up:
   a. Schema   -> <driver>.component                    (containers, mandatory fields, ModuleId)
   b. Enums    -> resource_tables/[RTD/]<Driver>.xml    (allowed values for the target PACKAGE)
   c. Defaults -> <driver>.component <quick_selection>  (sensible bool/enum defaults)
   d. Shape    -> RTD example .mex for the same driver  (canonical XML form, ref-path syntax)
3. Programmatically emit one <instance> per driver into peripherals_block.xml
   - one helper to emit CommonPublishedInformation
   - one builder per driver (see scripts/build_peripherals.py)
4. Splice the block into the user's .mex (replace any prior peripherals block).
   *** Destructive step - see the warning below. ***
5. Validate via scripts/check_problems.bat - read stderr, filter the noise.
6. Iterate until the filtered output is empty.
7. (Optional) Run s32ct_generate_code Peripherals ExportSrc to produce .ecvd
   + driver C sources; verify each named controller appears in its .ecvd.
```

> **Warning - step 4 modifies the user's `.mex` in place.** Any existing
> peripherals block in the target project is replaced, so hand-authored
> driver configuration in that region is lost. Before splicing:
>
> - Confirm the target `.mex` path with the user.
> - Back up or commit the project (`scripts/splice_peripherals.py` writes
>   a timestamped `.bak` by default - do not pass `--no-backup` unless
>   the project is already under version control).
> - Preview the region that will be replaced with
>   `python scripts/splice_peripherals.py --mex <project.mex> --block
>   <peripherals_block.xml> --dry-run` and check it contains only the
>   `<instance>` blocks you expect.

Plan for 3-5 rounds the first time you author a driver. Each iteration
should shrink the error count; if it doesn't, you are guessing instead
of consulting the next pitfall in `per-driver-reference.md`.

## Inputs

```jsonc
{
  // REQUIRED
  "project_path":   "<abs path to the .mex to extend>",
  "drivers":        [
    {
      "driver": "Spi" | "Uart" | "Can_43_FLEXCAN" | "Lin_43_LPUART_FLEXIO"
              | "Adc" | "Pwm" | "Wdg_43_...",
      "controllers": [
        { "hw": "LPSPI_0", "name_suffix": "FS26_SBC" /* + driver-specific extras */ }
      ]
    }
  ],
  // OPTIONAL - defaults auto-discovered from the MCP install
  "mcu":            "<MCU>",             // e.g. "S32K312"
  "package":        "<PACKAGE>",         // e.g. "S32K312_172HDQFP"
  "platform_sdk":   "<PLATFORM_SDK>",    // e.g. "PlatformSDK_S32K3"
  "rtd_version":    "<RTD_VERSION>",     // e.g. "TS_T40D34M70I1R0"
  "s32ds_install":  "<S32DS_INSTALL>",
  "s32ct_install":  "<S32CT_INSTALL>",
  "validate":       true,
  "generate_code":  true,
  "code_output":    "<abs path>"         // required if generate_code
}
```

## Outputs

Markdown report:

1. Driver instance table - one row per `<instance>` added, resolved
   hw-channel selectors, `.ecvd` lines confirming each named controller
   materialised.
2. Validation result - one of `PASS - 0 real problems after filtering`
   (state which lines were filtered) or `FAIL - N real problems remain`
   (paste verbatim).
3. Code-generation result (if `generate_code=true`) - `.c`/`.h` files
   per driver; for drivers where only `.ecvd` was produced, the
   application-level containers still needed.
4. Known caveats - copy the relevant pitfalls from
   `per-driver-reference.md` for the specific drivers configured, and
   state on which MCU/RTD they were verified vs. inferred.

## Verification scope

All concrete enum values, ModuleIds, and field names in
`per-driver-reference.md` were verified on **S32K312 /
PlatformSDK_S32K3 / RTD `TS_T40D34M70I1R0`**. For any other MCU + RTD
combination, re-verify against the matching RTD example `.mex` before
trusting the constants. The 5-source rule, workflow, validation gate,
and error-decision tree are MCU- and RTD-independent.

## Safety classification

- Read-only: `signal_configuration.xml`, `.component` files,
  `resource_tables/*.xml`, RTD example `.mex` files, the
  `<MCU>_default.mex` template.
- Read-write: the user's `.mex` and any output folders the user names.
- No network, no telemetry.
- Deterministic: same inputs -> same `.mex` shape. UUIDs for new
  `<instance>` elements are freshly generated.
