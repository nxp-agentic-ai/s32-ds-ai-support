# Clocks-tool data model  --  anatomy reference

This file explains what the on-disk XML under
`<MCU_DATA_ROOT>/processors/<MCU>/<PLATFORM_SDK>/clocks/<PACKAGE>/`
declares, and how each declaration shows up inside the `.mex`'s
`<clocks>` element. Read this when a setting id surfaces that you've
never seen before, or when you need to know the legal range of a divider
without firing up the GUI.

The files in the `clocks/<PACKAGE>/` directory (typical layout):

```
TOP.xml                  <- top-level: PLL, OSC selectors, the MUX matrix
FXOSC.xml                <- Fast crystal oscillator
SXOSC.xml                <- Slow (32 kHz) crystal oscillator
MODULE_CLOCKS.xml        <- Per-peripheral clock gates / dividers
POWER_MODES.xml          <- Power-mode-specific overrides
HSE.xml, etc.            <- Per-domain extras
```

---

## Elements you'll encounter

### `<clock_source>`

A primary frequency source. Examples: `FXOSC_CLK`, `SXOSC_CLK`, `FIRC_CLK`,
`PLL_PHI0`, `PLL_PHI1`. Each declares:

```xml
<clock_source id="FXOSC_CLK">
  <external_source default_freq="16 MHz"/>
  <range min_freq="8 MHz" max_freq="40 MHz"/>
</clock_source>
```

The `range` enforces the legal crystal frequency. The `external_source`
gives the default the GUI suggests.

PLLs have additional shape  --  `<input>`, `<vco>`, multiple
`<output_clock_signal>` (PHI0, PHI1, ...). The PLL multiplier shows up as
a `<configuration_element id="CORE_MFD">` whose `value_field` declares
the legal range:

```xml
<configuration_element id="CORE_MFD">
  <value_field type="integer" min="20" max="320"/>
  <default value="160"/>
</configuration_element>
```

### `<output_clock_signal>`

A named output frequency the Clocks tool computes. Examples:
`CORE_CLK`, `AIPS_PLAT_CLK`, `LPSPI0_CLK`, `eMIOS0_CLK`. In the
`.mex`, each appears as:

```xml
<clock_output id="CORE_CLK.outFreq" value="120 MHz"/>
```

The value is computed by S32CT from the upstream sources + divider
settings; you don't set it directly. To change `CORE_CLK`'s value you
adjust the upstream `CORE_MFD` (PLL multiplier) and/or
`MC_CGM_MUX_0_DIV0.scale` (the divider into the core clock domain).

### `<configuration_element>`  --  what `<setting>` ids reference

The `<setting id="X" value="Y"/>` entries inside `<clock_settings>` are
direct references to `<configuration_element id="X">` declarations in the
on-disk XML. Common categories:

| Pattern                            | Element kind                |
|------------------------------------|-----------------------------|
| `CORE_MFD.scale`                   | PLL multiplier              |
| `CORE_PLL_PD`                      | PLL power-down enum         |
| `CORE_PLLODIV_<N>_DE`              | PLL output divider enable   |
| `MC_CGM_MUX_<N>.sel`               | CGM MUX source select       |
| `MC_CGM_MUX_<N>_DIV<M>.scale`      | CGM MUX divider             |
| `MODULE_CLOCKS.MC_CGM_AUX<N>_DIV<M>.scale` | AUX clock divider   |
| `FXOSC_PM`                         | FXOSC power mode (`Crystal_mode`/`Bypass_mode`/`Disabled`) |
| `SXOSC_PM`                         | SXOSC power mode            |

To find what a specific id allows, grep `TOP.xml` (and family-specific
files) for `<configuration_element id="<your-id>">` and inspect its
`<value_field>` / `<choices>` children.

### `<selector>` and its `<source>` children

For `<setting id="MC_CGM_MUX_0.sel">` the legal values are the `id`
attributes of `<source>` elements inside the matching
`<selector id="MC_CGM_MUX_0">`. Common sources: `PHI0`, `PHI1`,
`FIRC`, `FXOSC`, `SIRC`, `SXOSC`.

### `<dependency>` inside `<clock_configuration>`

Tells the Pins tool which routings are required for this clock config to
work. The Clocks-tool side declares:

```xml
<dependency resourceType="PinSignal" resourceId="FXOSC_CLK.EXTAL"/>
<dependency resourceType="PinSignal" resourceId="FXOSC_CLK.XTAL"/>
```

The Pins tool then routes `FXOSC_CLK.EXTAL` -> `PTA24` and `FXOSC_CLK.XTAL`
-> `PTA25` (S32K312). Removing the routings while the Clocks tool still
declares them = validation error.

### `<clock_configuration name="X">`

The top-level container. Most projects have exactly one,
`ClockConfig0`. Multi-config projects use multiple siblings to model
runtime power-mode switching  --  see `multi-config.md`.

---

## How the .mex stores the live state

After computing, the `.mex` `<clocks>` element holds:

```xml
<clocks name="Clocks" enabled="true">
  <clock_configuration name="ClockConfig0">
    <clock_sources>
      <clock_source id="FXOSC_CLK" value="16 MHz" enabled="true"/>
    </clock_sources>
    <clock_outputs>
      <clock_output id="CORE_CLK.outFreq" value="120 MHz"/>
      ... (~80 outputs)
    </clock_outputs>
    <clock_settings>
      <setting id="CORE_MFD.scale" value="120"/>
      <setting id="MC_CGM_MUX_0.sel" value="PHI0"/>
      <setting id="FXOSC_PM" value="Crystal_mode"/>
      ... (~25 settings)
    </clock_settings>
    <dependencies>
      <dependency resourceType="PinSignal" resourceId="FXOSC_CLK.EXTAL"/>
      <dependency resourceType="PinSignal" resourceId="FXOSC_CLK.XTAL"/>
    </dependencies>
  </clock_configuration>
</clocks>
```

The Clocks tool's job is to keep the `<clock_outputs>` (computed) in
sync with the `<clock_settings>` (authored) you provide. So editing a
`.mex` means editing `<clock_settings>` (and possibly `<clock_sources>`
for things like changing the crystal frequency), then re-validating to
let S32CT recompute the outputs.

---

## The two tools you'll use most

When inspecting a `.mex`:
```
nxp_s32ct_execute_action(action_name="s32ct.inspect_clock_outputs", params={})  -> "{id: value}" pairs, all 80
nxp_s32ct_execute_action(action_name="s32ct.inspect_clock_settings", params={}) -> the ~25 authored settings
```

When verifying legality of a value you're about to write:
- Open `TOP.xml` and find `<configuration_element id="<your-setting-id>">`.
- For ranges: `<value_field min="..." max="..."/>`.
- For enums: `<choices><choice value="..."/></choices>`.
- For MUX selects: find the matching `<selector id="...">` and its
  `<source>` children.

There is no current MCP tool that surfaces these per-setting bounds (the
Clocks data model is structurally different from `resource_tables/`; it
would deserve its own `s32ct_clocks_lookup` if the need grows). For
now, the `references/performance-presets.md` file holds pre-validated
preset values so you rarely need to derive from scratch.
