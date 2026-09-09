# S32CT Clocks Info - Worked examples

Canonical invocation payloads for the five most common query patterns.

---

## 1. Overview of the clock data model for a package

> "What does the Clocks tool let me configure for `S32K312` on
> `S32K312_172HDQFP`?"

```jsonc
{ "mcu": "S32K312",
  "package": "S32K312_172HDQFP",
  "include_register_writes": false }
```

Returns the list of XML files discovered, the set of clock sources
(`FIRC_CLK`, `SIRC_CLK`, `FXOSC_CLK`, `SXOSC_CLK`, `PLL`, ...), the count
of output clock signals, the set of declared power modes, and the
top-level tool-wide `<configuration_element>` entries
(`ClockIpDevErrorDetect`, `ClockLoopTimeout`,
`ClockGetFrequencyAPI`, ...).

---

## 2. Modes and register writes of a single source

> "How do I configure FXOSC?"

```jsonc
{ "mcu": "S32K312",
  "package": "S32K312_172HDQFP",
  "filter": { "module": "FXOSC" } }
```

Returns the `<external_source>` range (e.g. 8-40 MHz, default 20 MHz),
every `<configuration_element>` (`FXOSCunderMcuControl`, `FXOSC_PM`,
`FxoscEndOfCount`, `FxoscOverdriveProtection`, `FxoscALCEnable`), each
with its `<item>` choices, defaults, and verbatim
`<assign register="FXOSC::CTRL" bit_field="..."/>` rows.

---

## 3. What feeds a peripheral clock?

> "What feeds `LPUART2_CLK` and how do I change its frequency?"

```jsonc
{ "mcu": "S32K312",
  "package": "S32K312_172HDQFP",
  "filter": { "output": "LPUART2_CLK" } }
```

Walks `MODULE_CLOCKS.xml` to find the gate/selector/divider chain
feeding `LPUART2_CLK_OUT` and quotes the corresponding
`<configuration_element>` ids - the same ids that will appear as
`<setting id="...">` in the `.mex`.

---

## 4. Lookup by register bit-field

> "Which Clocks-tool setting writes `FXOSC::CTRL[OSCON]`?"

```jsonc
{ "mcu": "S32K312",
  "package": "S32K312_172HDQFP",
  "filter": { "register": "FXOSC::CTRL", "bit_field": "OSCON" } }
```

Returns the matching `<configuration_element>` (`FXOSC_PM`) and the
specific `<item>` values that produce `OSCON=1` vs `OSCON=0`.

---

## 5. Power modes

> "Which power modes does this MCU declare?"

```jsonc
{ "mcu": "S32K312",
  "package": "S32K312_172HDQFP",
  "filter": { "module": "POWER_MODES" } }
```

Returns every `<power_mode id="..." type="..." default="..."/>` from
`POWER_MODES.xml`.
