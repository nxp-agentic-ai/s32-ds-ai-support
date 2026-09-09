# Clocks-tool error decision tree

Match the `SEVERE: [TOOL]` line that survives the
`s32ct.validate` noise filter against the patterns below. Each entry
shows what the message means and what to change.

When a problem doesn't match any pattern: **don't guess**. Open the
RTD example `.mex` for the target MCU family and either lift the entire
`<clock_configuration>` (workflow C) or diff the example's settings
against yours.

---

## "Frequency out of range" / "exceeds maximum allowed"

The computed value of an output exceeds the silicon ceiling declared in
`TOP.xml` (range max_freq).

**Fix**:
- Reduce the upstream PLL multiplier (`CORE_MFD.scale`).
- Or increase the downstream divider (`MC_CGM_MUX_<N>_DIV<M>.scale`).
- `references/performance-presets.md` lists known-good combinations.

## "MUX selector value not allowed"

The `<setting id="MC_CGM_MUX_N.sel" value="...">` value isn't among the
selector's legal sources.

**Fix**: open `TOP.xml`, find the matching `<selector id="MC_CGM_MUX_N">`,
read its `<source id="...">` children  --  those are the legal values
(typically: `PHI0`, `PHI1`, `FIRC`, `FXOSC`, `SIRC`, `SXOSC`).

## "PLL output ODIV disabled but referenced"

A downstream MUX selects a PLL output (PHI0/PHI1) whose `_DE` enable
setting is `Disabled`.

**Fix**: set `CORE_PLLODIV_0_DE` / `CORE_PLLODIV_1_DE` to `Enabled`, or
re-point the MUX at a different source.

## "Crystal oscillator power-mode incompatible with current operation"

You enabled an output that depends on FXOSC, but `FXOSC_PM` is
`Disabled`. Or you set `FXOSC_PM = Crystal_mode` but the pin
dependencies aren't routed.

**Fix**:
- Set `FXOSC_PM = Crystal_mode` if a crystal is on board.
- For the dependency side, ensure the Pins tool has
  `FXOSC_CLK.EXTAL` and `FXOSC_CLK.XTAL` routed to the correct pads
  (S32K312: PTA24/PTA25). Run `s32ct.inspect_pins` to
  confirm.

## "PLL multiplier out of legal range"

`CORE_MFD.scale` value lies outside `<value_field min="..." max="..."/>`.

**Fix**: clamp to the declared range. For S32K312 the integer-mode PLL
multiplier is typically `[20..320]`.

## "Dependency PinSignal not provided"

The clock configuration declares a `<dependency>` (most commonly
`FXOSC_CLK.EXTAL/XTAL` or `SXOSC_CLK.EXTAL/XTAL`) that the Pins tool
hasn't routed.

**Fix**: open the Pins-tool side and add the routing. For S32K312:

| Dependency           | Pin   | Pad pin number |
|----------------------|-------|----------------|
| `FXOSC_CLK.EXTAL`    | PTA24 | 23             |
| `FXOSC_CLK.XTAL`     | PTA25 | 25             |
| `SXOSC_CLK.EXTAL`    | PTA31 | 16             |
| `SXOSC_CLK.XTAL`     | PTB0  | 95             |

If the user doesn't want to add the routing, disable the corresponding
source (`FXOSC_PM = Disabled` etc.) instead.

## "MC_CGM divider ratio cannot exceed bounds"

`MC_CGM_MUX_<N>_DIV<M>.scale` out of range. Typical bounds: `[1..64]`.

**Fix**: clamp to the declared range.

## "Computed output frequency is zero / undefined"

An upstream selector is set to a disabled source, or a divider is `0`.

**Fix**:
- Verify every `<setting id="MC_CGM_MUX_*.sel">` resolves to an enabled
  source.
- Verify every `*_DIV<N>.scale` is `>= 1`.

## "Output X is referenced by a peripheral but has no value"

A driver instance's `*ClockRef` points at a clock output that doesn't
exist in this configuration (perhaps removed by a recent edit).

**Fix**: this is a *Peripherals-tool* error surfacing because a
Clocks-tool change broke a downstream reference. Either re-add the
clock output or re-point the offending driver.
`s32ct.inspect_xrefs root_filter=Mcu` lists the references.

---

## Pattern not in this list

Two diagnostic moves:

1. **Compare to an RTD example**. The clock tree of any S32K3xx RTD
   example is by construction valid; if your edit broke things, the
   delta is the suspect.

2. **Look up the offending setting**. `TOP.xml`'s
   `<configuration_element id="<your-id>">` declaration carries
   `<value_field>` (range) or `<choices>` (enum) telling you the
   legal value set.

If neither works, fall back to workflow C (lift the whole
`<clock_configuration>` from an example)  --  it's the safest reset.
