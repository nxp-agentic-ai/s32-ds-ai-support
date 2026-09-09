# Authoring a pin entry in a generated `.mex`

This file is referenced from `SKILL.md` of `s32ct-pins-info`.
Although that skill itself is read-only, its output is the canonical input
for **adding a new pin to a `.mex` Pins-tool configuration** (typically a
`.mex` produced by `s32ct-generate-mex-config` from a board/family starter
template such as the ones documented in `s32ct-pins-author-mex`). This
document encodes the authoring rules.

A new pin is inserted as a `<pin>` element under:

```
<configuration> -> <tools> -> <pins ...> -> <functions_list> -> <function name="..."> -> <pins>
```

## Required `<pin>` shape

```xml
<pin peripheral="SIUL2" signal="gpio, 0" pin_num="137" pin_signal="PTA0">
   <pin_features>
      <pin_feature name="direction" value="INPUT/OUTPUT"/>
   </pin_features>
</pin>
```

Every attribute on that `<pin>` element comes **directly** from
`signal_configuration.xml`. Use the parent skill (`s32ct-pins-info`) to look
the values up  -  never invent them, never re-case them.

| `.mex` attribute | Where to read it from `signal_configuration.xml` | Notes |
|---|---|---|
| `peripheral` | `<peripheral_signal_ref peripheral="...">` inside the chosen `<connections package_function="altN">` of the target `<pin>`. | The peripheral **instance** id, e.g. `LPSPI0`, `LPUART2`, `CAN0`, `eMIOS_0`, `ADC1`, `SIUL2`. Case-sensitive  -  copy verbatim. |
| `signal` | `<peripheral_signal_ref signal="..." [channel="..."]/>` on the same element. | Lower-case in the XML (`gpio`, `lpuart2_tx`, `lpspi0_sin`, `can0_tx`, `emios_0_ch_3`). When the `<peripheral_signal_ref>` also has a `channel="N"` attribute, the `.mex` joins them with `", "` -> `signal="gpio, 0"`, `signal="adc1_p, 7"`. When there is no `channel`, omit the comma -> `signal="lpspi0_sout"`. |
| `pin_num` | The `coords="..."` attribute of the target `<pin>` element. | Integer package pin number (e.g. `PTA0` -> `coords="137"` -> `pin_num="137"`). |
| `pin_signal` | The `name="..."` attribute of the target `<pin>` element. | The pin id, e.g. `PTA0`, `PTB10`, `PTE15`. Case-sensitive. |

## `<pin_features>` (optional but recommended)

`<pin_feature>` entries override the **functional properties** of the pin
(direction, pull, drive strength, slew rate, open-drain, ...). The legal
`name`/`value` pairs are exactly those declared for that pin under its
`<functional_properties>` block in `signal_configuration.xml`. Common
features (the exact set depends on the MCU/package):

| Feature | Typical values |
|---|---|
| `direction` | `INPUT`, `OUTPUT`, `INPUT/OUTPUT` |
| `pull_select` | `PULL_UP`, `PULL_DOWN` |
| `pull_enable` | `PULL_ENABLED`, `PULL_DISABLED` |
| `slew_rate` | `SLOW`, `FAST` |
| `drive_strength` | `LOW`, `HIGH` |
| `open_drain` | `OPEN_DRAIN_ENABLED`, `OPEN_DRAIN_DISABLED` |

If a feature is omitted, the Pins tool keeps the pin's silicon default.

## End-to-end example (verified on `S32K312_172HDQFP`; pattern applies to any MCU)

Goal: route **LPSPI0_SOUT** to **PTB1** in a `.mex`.

1. Query the parent skill with `filter = { "pin": "PTB1" }` (or
   `filter = { "signal": "lpspi0_sout" }`). The returned `<pin>` excerpt
   contains:
   ```xml
   <pin name="PTB1" coords="94" description="...">
     ...
     <connections package_function="alt3">
       <connection ...>
         <peripheral_signal_ref signal="lpspi0_sout" peripheral="LPSPI0"/>
         ...
   ```
2. Read off the four attributes:
   - `peripheral`  = `LPSPI0`              (from `peripheral=...`)
   - `signal`      = `lpspi0_sout`         (no `channel` -> no `", N"`)
   - `pin_num`     = `94`                  (from `coords="94"`)
   - `pin_signal`  = `PTB1`                (from `name="PTB1"`)
3. Insert the entry into the `.mex` under the appropriate
   `<function><pins>`:
   ```xml
   <pin peripheral="LPSPI0" signal="lpspi0_sout" pin_num="94" pin_signal="PTB1">
      <pin_features>
         <pin_feature name="direction" value="OUTPUT"/>
      </pin_features>
   </pin>
   ```

A channelled signal (e.g. SIUL2 GPIO 0 on PTA0) becomes:
```xml
<pin peripheral="SIUL2" signal="gpio, 0" pin_num="137" pin_signal="PTA0">
   <pin_features>
      <pin_feature name="direction" value="INPUT/OUTPUT"/>
   </pin_features>
</pin>
```
because the source XML is
`<peripheral_signal_ref signal="gpio" peripheral="SIUL2" channel="0"/>` and
the `.mex` form merges signal + channel as `"<signal>, <channel>"`. The same
rule applies to ADC channels (`adcN_p, M`), eMIOS channels
(`emios_N_ch, M`), FlexCAN, etc. on any S32 MCU.

## Pre-insertion checklist

Before patching a `.mex` with a new `<pin>` entry, the parent skill should
confirm  -  by quoting the source XML  -  that:

1. A `<pin name="<pin_signal>">` exists in `signal_configuration.xml` for
   the chosen `(mcu, platform_sdk, package)`.
2. That pin contains a `<connections package_function="altN">` whose
   `<peripheral_signal_ref>` matches the desired `(peripheral, signal,
   channel?)` triple **exactly** (case-sensitive, channel respected).
3. Every feature listed under `<pin_features>` is declared for that pin in
   `<functional_properties>` and the value is one of the legal values.

If any of those checks fails, do **not** emit the `<pin>` entry  -  return an
error message that names the offending field and lists the closest legal
alternatives. Inventing a routing that does not exist in the XML produces a
`.mex` that the S32 Configuration Tools `-ShowProblems` validator will
reject.

## Hand-off

After the `<pin>` entries have been authored:
- Use `s32ct-generate-mex-config` to bake them into a fresh `.mex`
  (pass them under the `pins` key of `modifications`), starting from a
  board-appropriate template described by `s32ct-pins-author-mex`.
- Use `s32ct-generate-code` (`ExportSrc` or `ExportAll` on the Pins tool)
  to emit `Siul2_Port_Ip_Cfg.[ch]` and `Tspc_Port_Ip_Cfg.[ch]`, or
- Use `s32ct-cli` / `s32ct-pins-facade` with
  `-Load <mex> -HeadlessTool Pins -ShowProblems` to validate the patched
  `.mex` before code generation.
