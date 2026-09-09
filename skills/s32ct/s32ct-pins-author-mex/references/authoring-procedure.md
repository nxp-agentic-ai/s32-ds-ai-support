# S32CT Pins .mex - Detailed authoring procedure

Full-detail companion to `SKILL.md`. Load when actually running the skill,
extending it to a new target, or diagnosing a validation failure.

---

## Supported targets

The skill supports every `(mcu, package, platform_sdk)` triple for which
the `s32ct-generate-mex-config` skill has a bundled reference template
under `skills/s32ct/s32ct-generate-mex-config/`.

Discovery rule:

```
skills/s32ct/s32ct-generate-mex-config/<MCU>_default.mex          <- canonical
skills/s32ct/s32ct-generate-mex-config/<MCU>_<PKG>_default.mex    <- override
```

**Currently bundled templates:**

| MCU | Package | Platform SDK | Template file |
|-----|---------|--------------|---------------|
| S32K312 | S32K312_172HDQFP | PlatformSDK_S32K3 | `S32K312_default.mex` |

For any other target the skill fails fast with:

> `"No reference .mex template registered for ({mcu}, {package},
>  {platform_sdk}). See the 'Extending to a new MCU/RTD/package' section
>  to add one."`

### Extending to a new MCU/RTD/package

1. In S32 Configuration Tools, open a new empty project for the target
   `(mcu, package, platform_sdk)` triple, enable the Pins, Clocks and
   Peripherals tools at the RTD versions you want as defaults, and leave
   them otherwise empty (one placeholder `PTA0` pin is acceptable - this
   skill replaces the `<pins>` block wholesale).
2. Save the project to
   `skills/s32ct/s32ct-generate-mex-config/<MCU>_default.mex`. If the same MCU
   ships in multiple packages and the templates must differ, save them
   as `skills/s32ct/s32ct-generate-mex-config/<MCU>_<PKG>_default.mex`.
3. Optionally copy the sibling `ClockConfigurationMappings.txt` next to
   the `.mex` - `copy_sidecars=true` picks it up.
4. Re-run this skill - no code changes needed.

---

## Preconditions

1. The Real-Time Drivers / Platform SDK is installed and exposes a
   `signal_configuration.xml` under
   `<S32DS_INSTALL>/eclipse/mcu_data/processors/<mcu>/<platform_sdk>/<package>/`.
2. A reference `.mex` is registered for the requested triple.
3. The S32CT headless CLI (`toolsc.exe`) is reachable (required only
   when `validate=true`).
4. The board description is either a parseable file (PDF/image/BOM) or a
   structured `routings` list. When only a PDF is provided, the agent
   extracts the pin <-> board-net mapping before calling the inner skills.
5. The skill is idempotent: identical inputs -> byte-identical `.mex`
   (modulo a fresh UUID when `regenerate_uuid=true`).

---

## Full input schema

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `board_name` | string | yes | Human label, e.g. `"S32K312MINI-EVB"`. |
| `schematic_path` | string | conditional | PDF or folder of design files. Required when `routings` is not supplied. |
| `routings` | array | conditional | Explicit list. Each item: `{ "function": "SPI #1 (on-board SBC)", "peripheral": "LPSPI0", "signal": "lpspi0_sout", "pin": "PTB1", "direction": "OUTPUT" }`. When supplied, `schematic_path` may be omitted. |
| `peripheral_request` | object | yes when `routings` absent | Quota, e.g. `{ "SPI": 2, "UART": 2, "CAN": 2, "LIN": 2, "ADC": 2, "PWM": 1 }`. |
| `mcu` | string | yes | E.g. `"S32K312"`, `"S32G274A"`. |
| `package` | string | yes | Must match folder name under `processors/<mcu>/<platform_sdk>/`. |
| `platform_sdk` | string | no | Defaults to the sole subfolder under `processors/<mcu>/` when exactly one exists. |
| `s32ds_install` | string | no | Optional override of the S32CT install root. |
| `output_path` | string | yes | Absolute path for the generated `.mex`. |
| `template_path` | string | no | Override the reference `.mex`. |
| `prefer_onboard` | bool | no | Default `true`. Prefer routings that match on-board wiring. |
| `regenerate_uuid` | bool | no | Default `true`. |
| `copy_sidecars` | bool | no | Default `true` (`ClockConfigurationMappings.txt`). |
| `overwrite` | bool | no | Default `false`. **Destructive when `true`** - see the caution below. |
| `validate` | bool | no | Default `true` - runs `-HeadlessTool Pins -ShowProblems`. |
| `generate_sources` | bool | no | Default `false`. When `true`, also runs `s32ct-generate-code` with `tool_name="Pins"`, `export_kind="ExportSrc"`. |

> **Caution - data loss.** Setting `overwrite: true` permanently
> replaces any existing file at `output_path`, and when
> `copy_sidecars: true` the copied sidecars (for example
> `ClockConfigurationMappings.txt`) are overwritten at the destination
> as well. There is no prompt and no backup. Confirm `output_path` with
> the user and back up or commit the existing `.mex` before enabling
> it; leave `overwrite: false` to fail safely instead.

---

## Behaviour

### Step 1 - Resolve and parse the board description

- If `routings` is supplied -> skip to Step 2.
- Otherwise parse `schematic_path`:
  - Use `pdftotext`, `pypdf`, or any available PDF text extractor.
  - On NXP DEVKIT/EVB-style schematics, the *Ports* pages (typically
    `MCU PORTS1`, `MCU PORTS2`, `MCU PORTS3` in the title block) contain
    the canonical `PTxx / signal-alt-function / pin_number` triples.
    For other vendors/custom boards, look for net labels of the form
    `PTxx_<peripheral>_<signal>` and the device pin-out section.
  - Prefer on-board wiring when `prefer_onboard=true`: if the schematic
    shows `PTB0/PTB1 -> on-board SBC SPI`, that beats an arbitrary header
    pin.
- Build a candidate map
  `function_request -> [(peripheral_instance, signal, pin), ...]`.

### Step 2 - Verify every candidate against `signal_configuration.xml`

Call `s32ct-pins-info` once to load the XML index for `(mcu, package,
platform_sdk)`. Then for every candidate `(peripheral, signal, pin)`:

1. Confirm a `<pin name="<pin>">` exists.
2. Confirm it carries a matching
   `<peripheral_signal_ref peripheral="{peripheral}" signal="{signal}"
   [channel="{ch}"]/>`.
3. Read off `coords` -> that integer is `pin_num` in the `.mex`.
4. Build the `.mex` `signal=` value:
   - **No `channel` attribute** in XML -> `signal="<sig>"` (e.g.
     `signal="lpspi0_sout"`, `signal="adc0_p1"`,
     `signal="emios_0_ch_4_g"` - channel baked into signal name).
   - **`channel` attribute present** -> `signal="<sig>, <channel>"`
     (e.g. `signal="gpio, 0"`).
5. Reject any candidate whose triple is not present in the XML; log it
   into the *Conflict report* as `"signal not exposed on package"` and
   pick the next legal alternative.

### Step 3 - Conflict resolution

Iterate over the requested peripheral instances in this fixed greedy
order (lowest pin flexibility first -> highest):

1. **ADC** channels (each is a single, fixed pin per channel).
2. **CAN** instances (typically 2-3 pin choices per instance).
3. **LPSPI** instances (four pins each - SOUT/SIN/SCK/PCS0).
4. **LPUART** instances (TX + RX, multiple pin pairs).
5. **PWM** - `eMIOS_0` / `eMIOS_1`, or FlexPWM where that is the PWM IP
   (typically dozens of choices).

For each peripheral, pick the first candidate whose every pin is unused
by already-resolved peripherals. Maintain a `used_pins` set and update
it after every successful assignment. If no conflict-free candidate
exists, **stop and return an error** listing the conflicts - never
silently drop a peripheral.

### Step 4 - Assemble the `<pin>` entries

Each routing becomes:

```xml
<pin peripheral="<peripheral>" signal="<signal>" pin_num="<coords>" pin_signal="<pin>">
   <pin_features>
      <pin_feature name="direction" value="<INPUT|OUTPUT|INPUT/OUTPUT>"/>
   </pin_features>
</pin>
```

`direction` defaults (apply unless the user supplies an explicit
`direction` in `routings`):

| Signal kind | Direction |
|-------------|-----------|
| `*_tx`, `*_sout`, `*_sck`, `*_pcs*`, `*_out*`, `emios_*` | `OUTPUT` |
| `*_rx`, `*_sin`, `adc*`, `*_in*` | `INPUT` |
| `gpio` (no alternate function) | `INPUT/OUTPUT` |

### Step 5 - Generate the `.mex`

Call `s32ct-generate-mex-config` with:

- `output_path`, `overwrite`, `regenerate_uuid`, `copy_sidecars` as passed in.
- `mcu`, `package`, `platform_sdk` - select the reference template.
- `modifications.pins` = the literal `<pin>` block from Step 4. Internally
  the skill replaces the placeholder pin in the reference template with
  this block - that is the only `<pin>` edit needed.
- `modifications.common.description`:
  `"Board-tailored Pins configuration: <board_name> - <peripheral_request_summary>"`.

### Step 6 - Optional: generate driver sources

When `generate_sources=true`, call `s32ct-generate-code`:

```jsonc
{ "project_path": "<output_path>",
  "tool_name":    "Pins",
  "export_kind":  "ExportSrc",
  "output_dir":   "<dirname(output_path)>/generated_pins" }
```

Include the produced file list in the report.

### Step 7 - Return the report

Always return the full structured report even on partial failure. The
caller needs to see *why* a peripheral was skipped or a conflict was
unresolvable.

---

## Validation recipe (four steps)

**DO NOT trust `exit_code` alone.** `toolsc.exe` **always** exits 0 even
when the Problems View contains errors. In a real session this rule was
hard-won: an `exit_code=0` silently masked 25 validation errors that
only became visible after capturing stderr properly. This is the single
most important lesson of the skill - preserve it verbatim.

Real problems are written to stderr as `SEVERE:` records produced by the
tool's `logValidationProblems` Java logger. The MCP wrapper's
`stderr_tail` is truncated (~3 KB) - if it shows the substring
`(truncated)` you are seeing only the warning preamble, not the real
problems.

1. Run the CLI redirecting stderr to a file.

   Windows - easiest path is a one-line `.bat` wrapper run via the shell
   tool (`cmd` evaluates `2>file` properly only with non-spaced paths -
   copy the `.mex` to a spaceless path first if necessary):

   ```bat
   "<S32CT_INSTALL>/toolsc.exe" -Load "<path-without-spaces>/proj.mex"
       -HeadlessTool <ToolName> -Enable -ShowProblems
       1> stdout.txt 2> stderr.txt
   ```

   Linux / macOS - POSIX shells quote correctly, so no staging copy is
   needed:

   ```sh
   "$S32CT_INSTALL/toolsc" -Load "/path/with spaces/proj.mex" \
       -HeadlessTool <ToolName> -Enable -ShowProblems \
       >stdout.txt 2>stderr.txt
   ```

2. Grep captured stderr for real problems.

   Windows:

   ```bat
   findstr /n /c:"SEVERE: [TOOL]" /c:"SEVERE: [Generation" stderr.txt
   ```

   Linux / macOS:

   ```sh
   grep -n -e 'SEVERE: \[TOOL\]' -e 'SEVERE: \[Generation' stderr.txt
   ```

   Format: `SEVERE: [TOOL] The resource "{DriverName}" from functional
   group "{group}" has the following error: {human-readable text}.`

3. Filter out generic Eclipse/framework noise - these always appear even
   on a clean project and are **not** problems with the `.mex`:
   - `SEVERE: Cannot get container for IPath ...`
   - `SEVERE: [TOOL] No script file found while trying to recompile the
     codegeneration script for SerDes Config Tool` (only relevant if
     SerDes is enabled).
   - `SEVERE: Error in expression parsing. Missing right bracket ')' ...
     in expression: (featureDefined(\`FEATURE_*\`) && ...` (internal
     conditional evaluator on optional features).
   - `SEVERE: Problem occurred during invocation of function derefAsr`
     (AUTOSAR ref deref on optional refs).

4. **Pass** = filtered output is empty AND `exit_code == 0`. **Fail** =
   any line remains after filtering. Surface verbatim in the *Validation
   result* section of the report.

Treating `exit_code == 0` as proof of correctness without this
stderr-capture / `.bat` wrapper / noise-filter procedure is a
silent-failure trap. Always run all four steps.

---

## Output - structured Markdown report

1. **Resolved sources** - the schematic file actually read (if any), the
   `signal_configuration.xml` path, the template `.mex` path.
2. **Final routing table** - one row per `<pin>` written, columns:
   *Function / Peripheral / Signal / Pin / pin_num / Direction / Source*
   (where *Source* is e.g. `"schematic page 5"` or `"auto-selected,
   conflict-free"`).
3. **Conflict report** - pins considered and rejected because they
   overlapped with an already-chosen routing. Empty when no conflict
   occurred.
4. **Generated artifacts** - absolute paths of the `.mex`, sidecar
   `ClockConfigurationMappings.txt`, and driver source files when
   `generate_sources=true`.
5. **Validation result** - pass/fail plus verbatim tail of the
   `-ShowProblems` output. Always present when `validate=true`.
6. **Hand-off suggestions** - e.g. run `s32ct-generate-code` to emit
   driver sources; open in S32CT to inspect; Peripherals tool not
   configured yet - call `s32ct-peripherals-author-mex`.

Typical one-line confirmation:

> `I generated the Pins-tool .mex with {N} routings at: {output_path}
>  (Validation: OK, 0 problem(s)).`

---

## Error handling

| Condition | Message template |
|-----------|------------------|
| Neither `schematic_path` nor `routings` provided | `"Either 'schematic_path' (a PDF/folder I can parse) or an explicit 'routings' list is required."` |
| `peripheral_request` mentions an unknown family | `"Unsupported peripheral family '<name>'. Allowed: SPI, UART, CAN, LIN, ADC, PWM."` |
| No reference `.mex` template registered | `"No reference .mex template registered for (<mcu>, <package>, <platform_sdk>). See the 'Extending to a new MCU/RTD/package' section to add one."` |
| A requested peripheral has no conflict-free routing | `"Could not place <function>: every candidate pin overlaps with already-assigned peripherals. Conflicts: <list>. Consider reducing the request or passing an explicit 'routings' override."` |
| A `routings` entry references a pin/signal not in the XML | `"Routing (peripheral='<p>', signal='<s>', pin='<n>') is not present on '<package>'. Closest matches: <top-3>."` |
| `output_path` exists and `overwrite=false` | `"Output '<output_path>' already exists. Re-run with overwrite=true or choose a different path."` |
| Inner skill fails | Propagate verbatim, prefixed with the offending step. |
| `validate=true` reports problems (after filter) | `"Generated '<output_path>' but Pins-tool validation reported <N> problem(s):\n<verbatim ShowProblems output>"` - file is kept on disk. |

All errors are returned as actionable text. The skill never raises raw
exceptions to the agent.

---

## MCP tool mapping (post 16->5 refactor)

| Referenced skill ID | MCP call to use |
|---------------------|-----------------|
| `s32ct-cli` | `nxp_s32ct_execute_action(action_name="s32ct.configure_cli", params={...})` |
| `s32ct-pins-facade` | `nxp_s32ct_execute_action(action_name="s32ct.configure_pins", params={...})` |
| `s32ct-clocks-facade` | `nxp_s32ct_execute_action(action_name="s32ct.configure_clocks", params={...})` |
| `s32ct-generate-code` | `nxp_s32ct_execute_action(action_name="s32ct.generate_code", params={...})` |
