# S32CT Pins Info - Detailed inspection reference

Full-detail companion to `SKILL.md`. Load whenever a query needs the
exact XML shape, filter schema, or behaviour beyond the Quickstart.

---

## Preconditions

1. The S32 Real-Time Drivers / Platform SDK is installed under an S32
   Design Studio or S32 Configuration Tools installation, exposing the
   per-package pins data model at:

   ```
   <S32DS_INSTALL>/eclipse/mcu_data/processors/<processor>/<platform_sdk>/<package>/signal_configuration.xml
   ```

   Segments (all case-sensitive on disk):
   - `<S32DS_INSTALL>` - the active S32CT install root, auto-discovered
     by the MCP at startup. Both `desktop` and `integrated_s32ds`
     distributions are supported. See `s32ct-distributions`.
   - `<processor>` - MCU folder under `mcu_data/processors/`. Any
     subfolder is valid: `S32K312`, `S32K314`, `S32K322`, `S32K324`,
     `S32K328`, `S32K344`, `S32K358`, `S32K388`, `S32G274A`, `S32G399A`,
     `S32M276`, `S32M274`, `S32R45`, `S32Z270`, `S32E270`, ...
     (typical install exposes ~20-25 folders).
   - `<platform_sdk>` - RTD/Platform SDK directory, e.g.
     `PlatformSDK_S32K1`, `PlatformSDK_S32K3`, `PlatformSDK_S32G2`,
     `PlatformSDK_S32G3`, `PlatformSDK_S32M27x`. Multiple RTD versions
     can coexist.
   - `<package>` - physical package variant, e.g. `S32K312_172HDQFP`,
     `S32K312_100LQFP`, `S32K344_172HDQFP`, `S32G274A_257MAPBGA`,
     `S32M276_100LQFP`.

   Concrete verified example path (install root differs per host - the
   MCP resolves it at startup):

   ```
   C:/NXP/S32DS.3.6.6/eclipse/mcu_data/processors/S32K312/PlatformSDK_S32K3/S32K312_172HDQFP/signal_configuration.xml
   ```

2. The `signal_configuration.xml` file exists and is readable.
3. This skill is idempotent and safe to call multiple times.

---

## `signal_configuration.xml` shape

Schema: `http://swtools.freescale.net/XSD/pinsModel/5.0/PinModelSchema.xsd`.
Root: `<pinsmodel:signal_configuration>`.

> **Namespace pitfall:** only the **root** element carries the
> `pinsmodel:` prefix; every child is in the *default* (empty)
> namespace. A naive XPath like `pinsmodel:pin` returns zero matches.
> Strip the prefix on the root (or register the namespace as the
> default) before iterating.

Top-level children (in order):

| Element | Purpose |
|---------|---------|
| `<part_information>` | Part number + package + total pin count (e.g. `pins="172"`, `pins="100"`, `pins="257"`). |
| `<functional_properties_declarations>` | Declares per-pin attributes (mode, pull, drive strength, slew, open-drain, direction, ...) and their legal value sets. |
| `<peripheral_types>` | Per-peripheral-family signal catalog (e.g. `ADC`, `CAN`/`FlexCAN`, `CMP`, `eMIOS`, `FCCU`, `FXIO`, `HSE`, `JTAG`, `LCU`, `LPI2C`, `LPSPI`, `LPUART`, `OSC32K`, `SIUL2`, `SYSTEM`, `TRGMUX`, `WKPU`, ...). Each contains `<peripheral_signal>` and `<signal_channel>` definitions with `directions` and `modes`. The exact set depends on the MCU. |
| `<peripherals>` | Concrete peripheral instances on this package (e.g. `ADC0`, `ADC1`, `CAN0`-`CAN5`, `LPUART0`-`LPUART7`, `eMIOS_0`-`eMIOS_2`, ...), each tagged with its `peripheral_type`. |
| `<pins>` | The physical `<pin>` elements (one per package ball/pad). Each pin is identified by its **`name`** attribute (e.g. `PTA0`, `PTB10`) and carries its package pin number in **`coords`** (e.g. `coords="137"` -> physical pin 137). Contains `<functional_properties>` (configurable attributes) plus a sequence of `<connections package_function="altN">` children, each holding a `<connection>` with a `<peripheral_signal_ref signal="..." peripheral="..." [channel="..."]/>` - those `<peripheral_signal_ref>` elements **are** the routing matrix. The inner `<assign>` elements are register-level patches the tool applies when a given routing is selected. |
| `<package_functions>` | Package-level shared functions. |
| `<signal_routes>` | Cross-pin signal-route declarations. |
| `<non_peripheral_pin_functions>` | Non-peripheral functions (GPIO, analog supplies, reset, debug, ...). |

Illustrative bulk counts on `S32K312_172HDQFP` (~2.4 MB XML - other
MCU/package combinations scale similarly):
- 172 `<pin>` (matches package pin count).
- 17 `<peripheral_type>`, 58 `<peripheral>`.
- 306 `<peripheral_signal>`, 250 `<signal_channel>`.
- ~7 000 `<assign>` and ~1 130 `<peripheral_signal_ref>` - the bulk of
  the file, the routing matrix.

Treat these numbers only as order-of-magnitude references.

---

## Filter schema

```jsonc
{
  "pin":             "PTA10",            // exact pin id (case-sensitive)
  "peripheral":      "LPUART2",          // peripheral instance id
  "peripheral_type": "LPUART",           // family
  "signal":          "LPUART2_TX",       // peripheral_signal id
                                         //   (lookup case-insensitive;
                                         //    emit lower-case in the .mex)
  "direction":       "out",              // "in" | "out" | "inout"
  "mode":            "digital",          // "digital" | "analog"
  "property":        "pull",             // functional property id
  "property_value":  "up"                // functional property value
}
```

Multiple keys are AND-combined. Unknown keys produce an explicit error.

---

## Output format

Markdown, structured:

1. **Resolved sources** - absolute path of the
   `signal_configuration.xml` actually read, plus `part_number`,
   `package` and total pin count from `<part_information>`.
2. **Answer** - human-readable response, e.g. `"On {package},
   LPUART2_TX can be routed to: PTA10, PTB3, PTD2."` or `"PTA10
   supports modes [digital, analog], pulls [none, up, down], drive
   strengths [low, high], slew [slow, fast], and N legal peripheral
   assignments: ..."`.
3. **Evidence** - short verbatim XML excerpts (`<pin>`, `<assign>`,
   `<peripheral_signal>`, `<functional_property>`) so every claim is
   traceable.
4. **Truncation note** - when `max_results` capped the listing:
   `"... 38 more results omitted (raise max_results to see all)."`

---

## Behaviour

1. **Resolve paths** from `s32ds_install`, `mcu`, `platform_sdk`,
   `package`. Derive default `platform_sdk` from a directory listing
   of `mcu_data/processors/<mcu>/` (only when unambiguous).
2. **Parse** `signal_configuration.xml` handling the namespace pitfall
   correctly (see above).
3. **Build the in-memory index** keyed by:
   - pin name (`<pin name="..." coords="...">`) - the `name` attribute
     (e.g. `PTA0`) is the pin id used by the Pins tool; `coords` is
     the integer package pin number that ends up as the `pin_num`
     attribute in a `.mex`.
   - peripheral instance id (`<peripheral id="...">`).
   - peripheral_type id (`<peripheral_type id="...">`).
   - peripheral_signal id (`<peripheral_signal id="...">`) - **lower-case
     in the XML** (e.g. `lpuart2_tx`, `lpspi0_sin`, `gpio`, `can0_tx`,
     `emios_0_ch_3`). The same lower-case string is reused verbatim in
     the `signal=...` attribute of a `.mex` `<pin>` entry.
4. **Apply `filter` and `query`**. `filter` is the structured fast
   path - exact matches against the index. `query` is the free-text
   fallback - fuzzy match against pin ids, signal ids, peripheral ids,
   and `<description>` content.
5. **Assemble the answer** by walking the matched nodes:
   - For a pin: pull its `<functional_properties>` and every
     `<assign>` / `<peripheral_signal_ref>` (legal routing).
   - For a signal/peripheral: enumerate every `<pin>` containing a
     matching `<assign>`.
6. **Quote evidence verbatim** - never paraphrase XML attribute
   values. RTD versions, MCUs and packages differ; the XML is
   authoritative.
7. **Cap output** at `max_results` and emit a truncation note when
   needed.

---

## Reasoning notes

- The authoritative source of truth is `signal_configuration.xml`.
  Always quote from it rather than inventing pin names - packages and
  RTD versions differ (the same MCU on `100LQFP`, `100HDQFP`,
  `172HDQFP` exposes different signal subsets; the same MCU under two
  different PlatformSDK versions can declare different functional
  properties).
- **Pin / signal / peripheral / package are linked**: a routing exists
  only when `<pin>` -> `<assign>` -> `<peripheral_signal_ref
  peripheral="..." signal="..."/>` is present in the XML for the chosen
  package. Never claim a routing without finding such an element.
- **Naming is case-sensitive on disk** for `mcu`, `platform_sdk`, and
  `package`. Pin ids (`PTA10`) are case-sensitive in the XML. Signal
  ids are stored **lower-case** in the XML and **must be emitted
  lower-case** in the `.mex`'s `signal=` attribute, even if the user
  typed them upper-case (`LPUART2_TX` in the question ->
  `signal="lpuart2_tx"` in the `.mex`).
- **Channel rule:** when a `<peripheral_signal_ref>` carries a
  `channel="N"` attribute, the `.mex` joins it as
  `signal="<sig>, <N>"`. No channel attribute means a bare
  `signal="<sig>"`. Uniform across all S32 MCUs.
- **Namespace rule:** only the root
  `<pinsmodel:signal_configuration>` has the `pinsmodel:` prefix;
  children do not. Strip/normalise the prefix on the root before XPath
  lookups.
- When exploring an unfamiliar MCU, first list
  `mcu_data/processors/` to discover installed MCUs, then
  `processors/<mcu>/` to discover installed PlatformSDKs, then
  `processors/<mcu>/<platform_sdk>/` to discover available packages,
  before drilling down.
- **Performance note:** `signal_configuration.xml` is large (multi-MB;
  the S32K312_172HDQFP file is ~2.4 MB with ~7 000 `<assign>` elements;
  bigger packages on S32G/S32R can be larger still). For interactive
  use, prefer `filter` (indexed lookup) over `query` (full-text scan)
  and use `include_routings=false` for overview answers.
- For follow-up actions, hand off to `s32ct-pins-facade`
  (apply/export), `s32ct-generate-code` (`ExportAll`/`ExportSrc` on
  the Pins tool -> `Siul2_Port_Ip_Cfg.[ch]` and
  `Tspc_Port_Ip_Cfg.[ch]`), or `s32ct-generate-mex-config` (bake pin
  choices into a `.mex` starter, using a board template from
  `s32ct-pins-author-mex`).

---

## Error handling

| Condition | Message template |
|-----------|------------------|
| `signal_configuration.xml` does not exist | `"Pins data model not found for MCU='<mcu>', SDK='<platform_sdk>', package='<package>'. Checked: <abs_path>. Verify the RTD/Platform SDK is installed and the package name is spelled correctly (case-sensitive)."` |
| `mcu_data/processors/<mcu>` missing | `"MCU '<mcu>' is not installed at '<s32ds_install>'. Available MCUs: <list>."` |
| `<platform_sdk>` subfolder missing | `"Platform SDK '<platform_sdk>' is not installed for MCU '<mcu>'. Available SDKs: <list>."` |
| `<package>` subfolder missing | `"Package '<package>' is not available for MCU '<mcu>' / SDK '<platform_sdk>'. Available packages: <list>."` |
| `signal_configuration.xml` exists but XML parsing fails | `"Failed to parse '<abs_path>': <parser error>. The file may be corrupted; reinstall the RTD package."` |
| `query` / `filter` matches nothing | `"No pin/signal matching the given criteria was found on '<package>'. Closest matches: <top-N suggestions>."` |
| `filter` contains an unknown key | `"Unsupported filter key '<key>'. Allowed: pin, peripheral, peripheral_type, signal, direction, mode, property, property_value."` |

All errors are returned as actionable text - the skill never raises
raw exceptions to the agent.

---

## MCP tool mapping (post 16->5 refactor)

| Referenced skill ID | MCP call to use |
|---------------------|-----------------|
| `s32ct-cli` | `nxp_s32ct_execute_action(action_name="s32ct.configure_cli", params={...})` |
| `s32ct-pins-facade` | `nxp_s32ct_execute_action(action_name="s32ct.configure_pins", params={...})` |
| `s32ct-generate-code` | `nxp_s32ct_execute_action(action_name="s32ct.generate_code", params={...})` |
