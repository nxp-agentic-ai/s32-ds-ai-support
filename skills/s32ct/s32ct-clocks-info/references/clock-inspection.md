# S32CT Clocks Info - Detailed inspection reference

Full-detail companion to `SKILL.md`: the XML data-model layout, schema
elements, filter schema, behaviour rules, and the XML <-> `.mex` mapping
used when authoring the `<clocks>` block.

---

## Preconditions

1. The S32 Real-Time Drivers / Platform SDK package is installed under
   the S32 Design Studio or S32 Configuration Tools installation,
   exposing the per-package clocks data model at:

   ```
   <S32DS_INSTALL>/eclipse/mcu_data/processors/<processor>/<platform_sdk>/clocks/<package>/
   ```

   Verified concrete example (install root differs per host - the MCP
   resolves it at startup; see `s32ct-distributions`):

   ```
   C:/NXP/S32DS.3.6.6/eclipse/mcu_data/processors/S32K312/PlatformSDK_S32K3/clocks/S32K312_172HDQFP/
   ```

   Segments:
   - `<S32DS_INSTALL>` - install root of S32 Design Studio (or a
     standalone S32CT install exposing the same `eclipse/mcu_data` tree).
     MCP-resolved at startup - see `s32ct-distributions`.
   - `<processor>` - MCU folder, e.g. `S32K312`, `S32K344`, `S32K358`,
     `S32M276`, `S32G274A`, .... Case-sensitive.
   - `<platform_sdk>` - RTD / Platform SDK folder, e.g.
     `PlatformSDK_S32K3`, `PlatformSDK_S32G2`, `PlatformSDK_S32M27`.
   - `<package>` - package variant, e.g. `S32K312_172HDQFP`,
     `S32K312_100HDQFP`, `S32K312_100LQFP`.

2. The clocks directory exists and is readable.
3. The skill is idempotent and safe to call multiple times.

---

## Clocks data-model layout

Schema: `http://apif.freescale.net/schemas/clocks/1.1`. Every package
directory contains the same logical set of files. File **names** that
are not fixed identifiers may differ across MCUs - discover them by
listing the directory rather than hard-coding them.

| File | Root element | Purpose |
|------|--------------|---------|
| `TOP.xml` | `<clocks:top_level>` | Top-level clock tree. Declares every output clock signal of the MCU (`<output_clock_signal>` - typically 80-200 entries: `CORE_CLK`, `AIPS_PLAT_CLK`, `PLL_PHI0`, every `<PERIPH>_CLK`, ...) and the implementation: internal sources (`FIRC_CLK`, `SIRC_CLK`), the PLL (`<clock_source id="PLL">`...), selectors (`MC_CGM_MUX_n`), dividers (`MC_CGM_MUX_n_DIVm`), gates, fractional dividers, global tool-level `<configuration_element>` entries (`ClockIpDevErrorDetect`, `ClockLoopTimeout`, `ClockGetFrequencyAPI`, ...), and `<map_output>` rules binding sources to output signals. References sibling files via `<diagram file="..."/>` and `<power_modes file="..."/>`. |
| `FXOSC.xml` | `<clocks:component id="FXOSC">` | Fast crystal-oscillator module. Declares `<output_clock_signal id="FXOSCOUT">`, the pin interface (`EXTAL`/`XTAL`), the `<external_source>` (default + min/max frequency `<range>`), and `<configuration_element>` entries for operation mode (`FXOSC_PM`: `Crystal_mode` / `Functional_mode` / `Power_down`), startup delay, transconductance / overdrive protection, ALC, MCU-control flag, plus `<constraint>` rules and the `<assign register="FXOSC::CTRL" bit_field="..."/>` register writes. |
| `SXOSC.xml` | `<clocks:component id="SXOSC">` | Slow crystal oscillator (typically 32.768 kHz). Same structure as `FXOSC.xml`. |
| `MODULE_CLOCKS.xml` | `<clocks:component id="MODULE_CLOCKS">` | Per-peripheral clock gates / selectors / dividers. Inputs are the major clock-tree signals (`CORE_CLK`, `AIPS_PLAT_CLK`, `PLL_PHI0`, `FIRC_IN`, ...). Outputs are `<PERIPH>_CLK_OUT` signals exposed back to the tool UI (`ADC0_CLK_OUT`, `LPSPI0_CLK_OUT`, `LPUART2_CLK_OUT`, `eMIOS0_CLK_OUT`, `FLEXCAN0_CLK_OUT`, ...). This is where to look up which clock feeds a given peripheral and how the corresponding gate / divider is programmed. |
| `POWER_MODES.xml` | `<clocks:power_modes>` | Declares `<power_mode id="..." type="run|standby" default="true|false" description="..."/>` for every mode supported by the MCU (`DRUN`, `RUN0`-`RUN3`, `STANDBY`, ...). Cross-referenced from `<enable>` / `<configuration_element>` `cond_expr` rules to express "this setting is only available in mode X". |
| `*.dsn` (e.g. `S32V2xx.dsn`, `S32K3.dsn`) | binary | Vector diagram of the clock tree used by the GUI. **Not authoring-relevant** - do not parse for configuration data. Quote only if the user explicitly asks about the GUI diagram. |

Additional XML files may be present for newer or wider MCUs (`PLL.xml`,
`MC_CGM.xml`, `CMU.xml`, ...). When present they follow the
`<clocks:component ...>` schema - treat any file with that root as a
clock module and parse it the same way.

---

## Schema elements to quote from these files

| Element | Meaning | Typical use in the answer |
|---------|---------|---------------------------|
| `<output_clock_signal id="..." name="..." description="..."/>` | Clock signal exposed by the module/tree. | Catalog of clocks. `id` becomes `<clock_output id="<id>.outFreq" ...>` in a `.mex`. |
| `<input_clock_signal id="..."/>` | Clock signal consumed by the module. | Documents the upstream feed. |
| `<clock_source id="..." name="..." description="...">` | A source (oscillator, IRC, PLL, external pin). May contain `<internal_source>`, `<external_source>`, `<value_map>`, `<range>`, `<pin>`, `<configuration_element>`. | Source catalog + tunable knobs. |
| `<configuration_element id="..." name="..." description="...">` | A user-facing knob. Contains a `<default value="..."/>` and either enum `<item id="..." description="...">` entries or a numeric `<value_field id="..." type="..." signed="...">`. Children `<assigns><assign register="MOD::REG" bit_field="FLD" value="..."/></assigns>` describe the exact register/bit-field write. | Each `id` maps 1:1 to a `<setting id="..." value="...">` in the `.mex` `<clock_settings>`. |
| `<constraint cond_expr="..." when="..." description="..."/>` | Validation rule on an element (e.g. "in Crystal mode `GM_SEL` must be > 0"). | Quote when explaining why a value is rejected. |
| `<enable cond_expr="..." description="..."/>` | Guards under which a knob / source is available. | Quote when an element is "greyed out". |
| `<assigns><assign register="..." bit_field="..." value="..."/></assigns>` | Exact register write for a given choice. | Trace user-visible setting -> register bit. |
| `<map_output id="..."><input signal="..."/></map_output>` | Binds a `<clock_source>` output (e.g. `FXOSC_CLK.clk`) to a top-level `<output_clock_signal>` (e.g. `FXOSCOUT`). | Documents clock-tree topology. |
| `<value_map expr="..."><setting ctrl_value="..." freq="..."/></value_map>` | Maps a discrete control value to a frequency (boot-time `FIRC_DIV_SEL` -> 48/24/3 MHz). | Legal frequencies of a discrete source. |
| `<power_mode id="..." type="run|standby" default="..."/>` | Declares one power mode. | Power-mode enumeration. |

---

## Filter schema

```jsonc
{
  "module":       "FXOSC",           // FXOSC | SXOSC | TOP | MODULE_CLOCKS | <component id>
  "clock_source": "FXOSC_CLK",       // <clock_source id="...">
  "output":       "LPUART2_CLK",     // <output_clock_signal id="..."> or .outFreq id
  "element":      "FXOSC_PM",        // <configuration_element id="...">
  "power_mode":   "DRUN",            // <power_mode id="...">
  "register":     "FXOSC::CTRL",     // <assign register="...">
  "bit_field":    "OSCON"            // <assign bit_field="...">
}
```

Multiple keys are AND-combined. Unknown keys produce an explicit error.

---

## Output format

Markdown, structured:

1. **Resolved sources** - absolute path of the clocks directory read,
   plus the list of XML files discovered.
2. **Answer** - human-readable response, e.g. `"On <MCU>/<RTD>/<pkg>,
   FXOSC supports modes [Crystal_mode, Functional_mode, Power_down];
   the frequency range is 8-40 MHz (default 20 MHz)."`
3. **Evidence** - short verbatim XML excerpts
   (`<configuration_element>`, `<assign>`, `<clock_source>`,
   `<map_output>`, `<power_mode>`, `<constraint>`) so every claim is
   traceable.
4. **Truncation note** - when `max_results` capped the listing:
   `"... 38 more results omitted (raise max_results to see all)."`

---

## Behaviour

1. **Resolve paths** from `s32ds_install`, `mcu`, `platform_sdk`,
   `package`. Derive default `platform_sdk` by listing
   `mcu_data/processors/<mcu>/` and picking the unique subfolder when
   exactly one exists; otherwise return an explicit error listing the
   available SDKs.
2. **Discover files** by listing `.../clocks/<package>/`. Treat `.xml`
   files as data; ignore `.dsn` and other non-XML assets for authoring
   questions.
3. **Parse** each `.xml`. Root may be `<clocks:top_level>`,
   `<clocks:component>`, or `<clocks:power_modes>` - strip the
   `clocks:` prefix before iterating, otherwise namespace matching
   silently skips every child.
4. **Build the in-memory index** keyed by:
   - module id (root `<clocks:component id="...">` or fixed
     `top_level` / `power_modes`)
   - `<clock_source id="...">`
   - `<output_clock_signal id="...">` and `<input_clock_signal id="...">`
   - `<configuration_element id="...">` (the canonical `.mex` setting id)
   - `<power_mode id="...">`
   - register / bit-field (every `<assign register="..." bit_field="..."/>`).
5. **Apply `filter` and `query`**. `filter` is the structured fast path
   (exact matches). `query` is the free-text fallback (fuzzy match
   against ids, names, and `description` content).
6. **Assemble the answer** by walking matched nodes:
   - For a `<configuration_element>`: emit `name`, `description`,
     `<default>`, full list of `<item>` (or `<value_field>` type), and
     the `<assign>` rows fired by each choice (when
     `include_register_writes`). Include any guarding `<enable>` /
     `<constraint>` blocks (when `include_constraints`).
   - For a `<clock_source>`: list its `<internal_source>` /
     `<external_source>` / `<value_map>` and the
     `<configuration_element>` entries it contains.
   - For an `<output_clock_signal>`: walk `<map_output>` and the
     `MODULE_CLOCKS.xml` gates to identify what feeds it.
   - For a `<power_mode>`: emit its `type` and `default` flag.
7. **Quote evidence verbatim** - never paraphrase XML attribute values.
   RTD versions, MCUs, and packages differ; only the XML is
   authoritative.
8. **Cap output** at `max_results`; emit a truncation note when needed.

---

## Authoring the `<clocks>` block of a `.mex`

This skill is read-only, but its output is the canonical input for
authoring or editing the Clocks-tool section of a `.mex` (typically one
produced by `s32ct-generate-mex-config` or edited via
`s32ct-clocks-graft-mex`). The Clocks tool stores its configuration
under:

```
<configuration> -> <tools> -> <clocks ...>
   -> <clock_configurations>
      -> <clock_configuration name="...">
         -> <dependencies>     <- pin-routing requirements (FXOSC EXTAL/XTAL, ...)
         -> <clock_sources>    <- initial frequencies of every external source
         -> <clock_outputs>    <- resulting frequencies of every output clock
         -> <clock_settings>   <- every tunable knob set by the user
```

### Exact `.mex` <-> XML mapping (verified)

| `.mex` element | XML source | Notes |
|----------------|-----------|-------|
| `<clock_source id="<src>.outFreq" value="..." enabled="..."/>` | `<clock_source id="<src>">` in `FXOSC.xml` / `SXOSC.xml` / `TOP.xml`. `value` must satisfy `<external_source default_freq="...">` and any `<range min_freq="..." max_freq="..."/>`. | Pattern observed: `id="FXOSC_CLK.FXOSC_CLK.outFreq"`, `id="SXOSC_CLK.SXOSC_CLK.outFreq"`. |
| `<clock_output id="<sig>.outFreq" value="..."/>` | `<output_clock_signal id="<sig>">` in `TOP.xml` (and `MODULE_CLOCKS.xml` for peripheral clocks). | One entry per output signal asserted. |
| `<setting id="<elem_id>" value="<choice>" locked="..."/>` | `<configuration_element id="<elem_id>">` in `TOP.xml` / `FXOSC.xml` / `SXOSC.xml` / `MODULE_CLOCKS.xml`. `value` must be one of the declared `<item id="...">` (enum) or numeric and satisfy the `<value_field>` type/signedness. Examples: `FXOSC_PM=Crystal_mode`, `CORE_PLL_PD=Power_up`, `MC_CGM_MUX_0.sel=PHI0`, `MC_CGM_MUX_0_DIV0.scale=1`. | Primary place where the user expresses intent. Pure defaults can be omitted. |
| `<dependency resourceType="PinSignal" resourceId="..."/>` | The `<pin id="EXTAL"/>` / `<pin id="XTAL"/>` declarations in `FXOSC.xml` / `SXOSC.xml` (and any clock-source that contains a `<pin>` referencing a `peripheral_signal_ref`). | Emitted automatically when the corresponding source is enabled. Must be routed by the Pins tool - cross-check with `s32ct-pins-info`. |
| `<power_mode>` references inside `<options>` / `<dependencies>` | `<power_mode id="...">` in `POWER_MODES.xml`. | Only modes declared here are legal. |

### Pre-insertion checklist

Before writing or patching a `<clock_settings>` entry, confirm by
quoting the source XML that:

1. A `<configuration_element id="<elem_id>">` exists in one of the
   package's clock XML files for the requested setting.
2. The chosen `value` is one of the declared `<item id="...">` (enum) or
   satisfies the `<value_field>` type and any `<constraint>`.
3. The enclosing `<enable cond_expr="..."/>` is satisfied by the other
   settings in the same `<clock_configuration>` (e.g. "SSCG-only
   fields require `CORE_PLLMODE == SSCG`").
4. For a `<clock_source>` `outFreq`, the value lies inside the declared
   `<range>`.
5. Every dependency pin (EXTAL/XTAL) is reachable on the chosen
   package - cross-check with `s32ct-pins-info`.

If any check fails, do **not** emit the setting - return an error
naming the offending element and the closest legal alternatives.
Inventing settings that the XML does not declare produces a `.mex` that
`-ShowProblems` will reject.

### Hand-off

After the `<clock_settings>` / `<clock_sources>` / `<clock_outputs>`
entries have been authored:

- Use `s32ct-generate-mex-config` (or `s32ct-clocks-graft-mex`) to bake
  them into a `.mex`.
- Validate with `nxp_s32ct_execute_action(action_name="s32ct.configure_clocks", params={...})` - `-Load {mex}
  -HeadlessTool Clocks -ShowProblems` returns zero problems on a clean
  configuration.
- Emit driver sources with
  `nxp_s32ct_execute_action(action_name="s32ct.generate_code", params={"tool_name": "Clocks", "export_kind": "ExportSrc"})`
  (or `"export_kind": "ExportAll"`) - produces
  `Clock_Ip_Cfg.[ch]` and `Clock_Ip_Cfg_Defines.h`.

---

## Reasoning notes

- **The XML is the only authoritative source.** Never invent
  `<configuration_element>` ids, `<item>` values, register names, or
  bit-field names from training data - different MCUs and RTD versions
  diverge significantly (an S32K3 PLL is described by a different
  element set than an S32G2 PLL).
- **Naming is case-sensitive on disk** for `mcu`, `platform_sdk`, and
  `package`. Element ids, source ids, output signal ids, register
  names, and bit-field names inside the XML are also case-sensitive.
- The mapping XML -> `.mex` is exact and 1-to-1:
  - `<configuration_element id="X">` -> `<setting id="X" value="..."/>`
  - `<output_clock_signal id="Y">` -> `<clock_output id="Y.outFreq" .../>`
  - `<clock_source id="Z">` -> `<clock_source id="Z.Z.outFreq" .../>`
- When exploring an unfamiliar MCU, first list
  `mcu_data/processors/`, then `processors/<mcu>/`, then
  `processors/<mcu>/<platform_sdk>/clocks/` to discover the available
  packages, before drilling down.
- **Performance note:** `TOP.xml` and `MODULE_CLOCKS.xml` are typically
  the largest files (tens of thousands of lines on wider MCUs). For
  interactive use, prefer `filter` (indexed lookup) over `query`
  (full-text scan), and use `include_register_writes=false` /
  `include_constraints=false` for overview answers.

---

## Error handling

| Condition | Message template |
|-----------|------------------|
| `mcu_data/processors/<mcu>` missing | `"MCU '<mcu>' is not installed at '<s32ds_install>'. Available MCUs: <list>."` |
| `mcu_data/processors/<mcu>/<platform_sdk>` missing | `"Platform SDK '<platform_sdk>' is not installed for MCU '<mcu>'. Available SDKs: <list>."` |
| `clocks/<package>` missing | `"Clocks data model not found for MCU='<mcu>', SDK='<platform_sdk>', package='<package>'. Checked: <abs_path>. Available packages: <list>."` |
| `<package>` directory has no `.xml` files | `"Clocks directory '<abs_path>' exists but contains no XML data. Reinstall the RTD/Platform SDK."` |
| An XML file exists but parsing fails | `"Failed to parse '<abs_path>': <parser error>. The file may be corrupted; reinstall the RTD package."` |
| `query`/`filter` matches nothing | `"No clock element matching the given criteria was found for '<package>'. Closest matches: <top-N id suggestions>."` |
| `filter` contains an unknown key | `"Unsupported filter key '<key>'. Allowed: module, clock_source, output, element, power_mode, register, bit_field."` |

All errors are returned as actionable text - the skill never raises raw
exceptions to the agent.
