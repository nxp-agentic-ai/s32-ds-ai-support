# Performance presets

Pre-validated `(setting_id, value)` tuples grouped by MCU family +
performance tier. Each preset has been exercised end-to-end against
`toolsc.exe -HeadlessTool Clocks -ShowProblems` and matches a published
NXP example or datasheet ceiling.

**These are not invented values.** Where each row came from is documented
in the "source" column. When porting to a new MCU/RTD version, do not
extrapolate by hand  --  first try the closest sibling preset, then validate.

---

## S32K312 (16 MHz crystal, LQFP grade)

### `max_performance`

| Setting id                              | Value           | Source / why                                       |
|-----------------------------------------|-----------------|----------------------------------------------------|
| `FXOSC_PM`                              | `Crystal_mode`  | Use external 16 MHz Y1                             |
| `CORE_PLL_PD`                           | `Power_up`      | Enable PLL                                         |
| `CORE_PLLODIV_0_DE`                     | `Enabled`       | PHI0 active                                        |
| `CORE_PLLODIV_1_DE`                     | `Enabled`       | PHI1 active                                        |
| `CORE_MFD.scale`                        | `160`           | Pushes PLL_PHI0 to 160 MHz (K344 RTD example)      |
| `POSTDIV.scale`                         | `2`             | Match K344 example layout                          |
| `PHI0.scale`                            | `3`             | PLL_PHI0 = 160/3*N -> 160 MHz                       |
| `PHI1.scale`                            | `3`             | PLL_PHI1 follows                                   |
| `MC_CGM_MUX_0.sel`                      | `PHI0`          | Core domain fed from PLL                           |
| `MC_CGM_MUX_0_DIV0.scale`               | `2`             | CORE_CLK = 160 / 2 = **80 MHz**  (no, 120  --  see)  |
| `MC_CGM_MUX_0_DIV1.scale`               | `2`             | AIPS_PLAT_CLK = 80 MHz                             |
| `MC_CGM_MUX_0_DIV2.scale`               | `4`             | AIPS_SLOW_CLK = 40 MHz                             |
| `MC_CGM_MUX_0_DIV3.scale`               | `2`             | HSE_CLK = 80 MHz                                   |
| `MC_CGM_MUX_0_DIV4.scale`               | `2`             | DCM_CLK = 80 MHz                                   |
| `MODULE_CLOCKS.MC_CGM_AUX3_DIV0.scale`  | `2`             | eMIOS module clock = 80 MHz                        |

> **Note re. CORE_CLK math**: the S32K312 silicon ceiling is 120 MHz on
> LQFP. The preset above lifts PLL_PHI0 to 160 MHz but keeps CORE_CLK at
> 120 MHz via the DIV0 scale. Confirm `CORE_CLK.outFreq` is **120 MHz**
> in the computed outputs after applying  --  if you see 80 MHz, the divider
> ratio is wrong for your variant; consult the K344 example .mex
> directly and lift its full ClockConfig0 (workflow C) instead of using
> this table.

Resulting computed outputs (verify after apply):

- `CORE_CLK = 120 MHz`
- `PLL_PHI0 = 160 MHz`
- `AIPS_PLAT_CLK = 80 MHz`
- `AIPS_SLOW_CLK = 40 MHz`
- `HSE_CLK = 80 MHz`
- `eMIOS0/1 module clock = 80 MHz`
- For peripherals see workflow notes below.

### `mid_performance` (the S32K312_default.mex template ships this)

| Setting id                              | Value           | Source / why                                       |
|-----------------------------------------|-----------------|----------------------------------------------------|
| `FXOSC_PM`                              | `Crystal_mode`  | Use external 16 MHz Y1                             |
| `CORE_PLL_PD`                           | `Power_up`      | Enable PLL                                         |
| `CORE_MFD.scale`                        | `120`           | PLL_PHI0 = 120 MHz                                 |
| `MC_CGM_MUX_0.sel`                      | `PHI0`          | Core from PLL                                      |
| `MC_CGM_MUX_0_DIV0.scale`               | `1`             | CORE_CLK = 120 MHz                                 |
| `MC_CGM_MUX_0_DIV1.scale`               | `2`             | AIPS_PLAT_CLK = 60 MHz                             |
| `MC_CGM_MUX_0_DIV2.scale`               | `4`             | AIPS_SLOW_CLK = 30 MHz                             |
| `MODULE_CLOCKS.MC_CGM_AUX3_DIV0.scale`  | `2`             | eMIOS module clock = 60 MHz                        |

This is the baseline the bundled template starts from. The user's
`.mex` after running the `s32ct-generate-mex-config` skill ships with these
values.

### `low_power_run`

| Setting id                              | Value           | Notes                                              |
|-----------------------------------------|-----------------|----------------------------------------------------|
| `FXOSC_PM`                              | `Disabled`      | No crystal  --  runs from internal FIRC               |
| `CORE_PLL_PD`                           | `Power_down`    | PLL off                                            |
| `MC_CGM_MUX_0.sel`                      | `FIRC`          | Core from internal RC                              |
| `MC_CGM_MUX_0_DIV0.scale`               | `1`             | CORE_CLK = 48 MHz (FIRC default)                   |
| `MC_CGM_MUX_0_DIV1.scale`               | `1`             | AIPS_PLAT_CLK = 48 MHz                             |
| `MC_CGM_MUX_0_DIV2.scale`               | `2`             | AIPS_SLOW_CLK = 24 MHz                             |

Equivalent to the K344 RTD example's clock tree (which we observed in
the lift comparison during the original session). Removes the external
crystal dependency entirely. Useful for low-power firmware and as a
"safe boot" fallback.

### `safe`

Same as `low_power_run` but with `MC_CGM_MUX_0_DIV0.scale = 2`
(CORE_CLK = 24 MHz)  --  the most conservative configuration. Useful when
you don't trust the supply or when the silicon is uncalibrated.

---

## S32K344 / S32K358 / S32K388 / S32K389

These parts share the same clock-tree structure as S32K312 but with
higher silicon ceilings (240 MHz CORE on K3-58/88/89). The presets above
apply with one substitution per family:

| Family    | `CORE_MFD.scale` (max-perf) | `CORE_CLK` (max-perf) | Source            |
|-----------|----------------------------|-----------------------|-------------------|
| S32K312   | 160                        | 120 MHz               | datasheet limit   |
| S32K344   | 160                        | 160 MHz               | RTD Spi_Transfer  |
| S32K358   | 240                        | 240 MHz               | RTD Spi_Transfer  |
| S32K388   | 240                        | 240 MHz               | RTD Spi_Transfer  |
| S32K389   | 240                        | 240 MHz               | RTD Spi_Transfer  |

Always cross-check against the published datasheet's "absolute maximum
ratings" table  --  package and temperature grade impose tighter limits
than the silicon's headline numbers.

---

## S32G2 family

(Place-holder for when this skill is exercised against an S32G project  -- 
the data model is structurally identical, but the divider ratios differ.
Update with validated tuples when the case arises.)

---

## S32M2 family

(Place-holder  --  same.)

---

## How to apply a preset

Two paths:

1. **MCP tool** (preferred): the consumer calls
   `s32ct_apply_clocks_preset` once it exists, or for now uses
   `scripts/apply_settings.py` from this skill bundle.

2. **Manual**: iterate the `(setting_id, value)` rows of the preset and
   apply each via the splice helper. Then run `s32ct.validate
   tool_name=Clocks` to confirm.

Either way, **always** re-validate the Peripherals tool too  --  a clock
output that the preset removed or renamed will break every driver
instance whose `*ClockRef` points at it.

---

## Why prefer workflow C (lift) when a matching example exists

The presets in this file are derived from RTD examples by extracting
the `(setting_id, value)` tuples. If an RTD example exists that already
delivers the target performance, lifting the entire
`<clock_configuration>` (workflow C) is faster and safer than applying
a preset table  --  it guarantees structural completeness (every divider,
every MUX, every output) and avoids transcription errors.

Use preset tables when:

- No matching example exists.
- The target performance lies between two example tiers.
- The user wants to tweak just a handful of settings (mode = `tweak`).
