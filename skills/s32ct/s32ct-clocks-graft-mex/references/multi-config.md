# Multiple `<clock_configuration>` siblings

Adding a second `<clock_configuration>` to a `.mex` lets the application
switch power-mode-specific clock trees at runtime. Common pattern:

- `ClockConfig0`  --  the always-active default, max-performance.
- `LowPower`  --  used during STANDBY / WAIT (FXOSC off, PLL off, FIRC only).

The Mcu driver's `mcu.set_mode` API expects them as siblings of the
default config.

---

## Structural shape

```xml
<clocks name="Clocks" enabled="true">
  <clock_configuration name="ClockConfig0">  ... </clock_configuration>
  <clock_configuration name="LowPower">      ... </clock_configuration>
</clocks>
```

Both blocks share the same `<clock_sources>` / `<clock_outputs>` /
`<clock_settings>` / `<dependencies>` structure but with different
`<setting>` values. Each `<clock_configuration>` is self-contained  --  no
inheritance.

---

## Adding a second config

1. **Copy** the existing `<clock_configuration name="ClockConfig0">`
   element verbatim.
2. **Rename** the copy: `name="LowPower"` (or whatever the application
   needs).
3. **Edit** the copy's `<clock_settings>` for the target power mode.
   Typical low-power overrides:

   ```xml
   <setting id="FXOSC_PM" value="Disabled"/>
   <setting id="CORE_PLL_PD" value="Power_down"/>
   <setting id="MC_CGM_MUX_0.sel" value="FIRC"/>
   <setting id="MC_CGM_MUX_0_DIV0.scale" value="1"/>
   ```

4. **Update `<dependencies>`** if any oscillator was disabled (no pins
   needed for FIRC-only mode).
5. **Reference from Mcu**: add a `McuModeSettingConf_<N>` entry that
   binds the new config to a power-mode token.

---

## Validation considerations

- Both configs must validate clean independently. Run
  `s32ct.validate tool_name=Clocks` after each edit.
- All `*ClockRef` driver references resolve against
  `ClockConfig0` at code-gen time, regardless of which other configs
  exist. The runtime switch happens dynamically.
- Adding configs increases the generated `Mcu_Cfg.c` size noticeably.
  Each extra config produces another `tMcu_ClockConfigType` constant.

---

## Out of scope for this skill

This file documents the *shape*. The actual decision of which
power-mode policy a particular application needs (when to enter
LOWPOWER, what clocks must stay alive, etc.) is a system-design
question outside the scope of this skill.

For the bring-up path the original session walked, **don't add a second
config until the first one is fully validated and the driver `*ClockRef`
retargeting is done.** Multi-config debugging is meaningfully harder
than single-config.
