# Configuration - Full Input Reference

Referenced from `SKILL.md`. This file documents the full input table and
the schema for the `tweaks` and `add_clock_points` entries.

## Input table

| Name | Required | Description |
|------|----------|-------------|
| `project_path`, `output_path` | yes | Absolute paths of the input and resulting `.mex`. |
| `mode` | yes | `preset` \| `tweak` \| `lift`. |
| `mcu`, `package` | yes | E.g. `S32K312`, `S32K312_172HDQFP`. |
| `preset` | mode=preset | `max_performance` \| `mid_performance` \| `low_power_run` \| `safe`. See `performance-presets.md`. |
| `tweaks` | mode=tweak | Array of `{ type, id, value, [from, to] }` - see schema below. |
| `example_mex` | mode=lift | RTD example whose `<clock_configuration>` is lifted. |
| `add_clock_points` | no | New `McuClockReferencePoint_*` entries - `{ name, select }`. |
| `platform_sdk`, `rtd_version` | no | Defaults auto-discovered. |
| `s32ds_install` | no | Override of the S32CT install root. |
| `validate`, `overwrite` | no | Default `true` / `false`. |

## Tweak schema

`type` values:

- `setting` - direct `<setting id value/>` write. `id` = the exact
  string the Clocks tool stores (e.g. `CORE_MFD.scale`,
  `MC_CGM_MUX_0_DIV0.scale`); `value` matches the declared enum items
  (`Power_up`, `PHI0`) or numeric range.
- `frequency_select` - `from` / `to` fields select a new source; used
  when the schema encodes the change as a selector rather than a
  scalar.
- `enable_pll` - toggle a PLL block.
- `configure_clkout` - set up the CLKOUT peripheral.

Enumerate legal `id` values on this package with
`s32ct.inspect_clock_settings`.

## Clock-point schema

`{ "name": "LPUART_CLK" | "CAN_PE_CLK" | ..., "select": "AIPS_SLOW_CLK" }`

`name` is a Clocks-tool output id. Each entry adds a `<struct>` to
`McuClockSettingConfig_0/McuClockReferencePoint`; drivers then re-point
their `*ClockRef` at the new entry.
