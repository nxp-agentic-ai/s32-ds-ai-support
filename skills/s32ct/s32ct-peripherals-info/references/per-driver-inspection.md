# Per-driver inspection - full procedure and reference

Companion reference for `s32ct-peripherals-info`. Documents preconditions,
inputs, the resolution algorithm for `<dynamic_enum>` references, resource
table anatomy, driver families, worked examples, and the error-message
catalog.

## Authoritative source layout

Two on-disk sources shipped with S32 Design Studio:

1. Component descriptor:
   ```
   <S32DS_INSTALL>/eclipse/mcu_data/components/<platform_sdk>/<peripheral_folder>/<peripheral_folder>.component
   ```
2. Per-package resource tables:
   ```
   <S32DS_INSTALL>/eclipse/mcu_data/processors/<processor>/<platform_sdk>/<package>/resource_tables/<Driver>.xml
   <S32DS_INSTALL>/eclipse/mcu_data/processors/<processor>/<platform_sdk>/<package>/resource_tables/RTD/<Driver>.xml
   ```

`<S32DS_INSTALL>` is auto-discovered by the MCP at startup (override via
input). Both `desktop` and `integrated_s32ds` distributions are supported -
see the `s32ct-distributions` skill.

`<platform_sdk>` is the RTD folder (e.g. `PlatformSDK_S32K3`,
`PlatformSDK_S32G2`, `PlatformSDK_S32M27`, `PlatformSDK_S32K1`). The exact
set depends on the RTDs the user has installed.

A current S32K3 install, for example, ships roughly 100 sub-folders
including: `Adc, Adc_Sar_Ip, Base, Bctu_Ip, Can_43_FLEXCAN, Crc_Ip, Dio,
Dma_Ip, Emios_Gpt, Emios_Pwm, Eth_43_GMAC, Fee, FlexCAN, Flexio_Lin,
Flexio_Pwm, Flexio_Spi, Flexio_Uart, FlexPwm_Ip, Gmac, Gpt, I2c, Icu,
IntCtrl_Ip, Lcu_Ip, Lin_43_LPUART_FLEXIO, Lpi2c, Lpspi, Lpuart_Lin,
Lpuart_Uart, Mcl, Mcu, Mem_43_INFLS, Os, Pit, Platform, Port, Pwm,
Qspi_Ip, Rtc, Sai_Ip, Siul2_Dio, Siul2_Icu, Siul2_Port, Spi, Stm,
Swt_Ip, Trgmux_Ip, Uart, Wdg, Wdg_43_Instance1..4, Wkpu, Zipwire` plus
several `_Ip` and AUTOSAR-style variants. Other RTDs (S32G, S32M, S32K1,
...) expose a different, smaller or different-named set. Always discover
by listing the folder; never hard-code.

Peripheral folder names are case-sensitive on disk. The descriptor
filename matches the folder name.

Verified S32K312_172HDQFP top-level `resource_tables/` ships:
`Adc.xml, Can.xml, Crypto.xml, Dio.xml, Eth.xml, Fls.xml, Gpt.xml,
I2c.xml, Icu.xml, interrupts.xml, Lin.xml, Mcl.xml, MCU.xml, Ocu.xml,
Platform.xml, Port.xml, Spi.xml, Wdg.xml` plus a `RTD/` subfolder with
`Adc.xml, Can.xml, Crc.xml, Dio.xml, Gpt.xml, I2c.xml, I2s.xml, Icu.xml,
Lin.xml, Mcl.xml, MCU.xml, Mem.xml, Ocu.xml, Platform.xml, Port.xml,
Pwm.xml, Rm.xml, Sent.xml, Spi.xml, Uart.xml, Wdg.xml`. Other packages
ship different sets - discover by listing.

Optional inputs:
- Bundled reference `.mex` at
  `.../skills/s32ct/s32ct-generate-mex-config/<MCU>_default.mex` for the
  `include_mex_shape=true` path. Currently only `S32K312_default.mex`.
  For any other MCU, fall back gracefully.
- `doc/index.md` next to the `.component` - JSON pointer to the PDF:
  ```json
  {"component-doc-link":"../../../../../S32DS/software/<platform_sdk>/RTD/<Driver_TS_...>/doc/RTD_<DRIVER>_UM.pdf"}
  ```

## Inputs (full table)

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `peripheral_name` | string | yes | Driver folder name under `mcu_data/components/<platform_sdk>/`. Case-sensitive (e.g. `Mcu`, `Port`, `Can_43_FLEXCAN`, `Lpuart_Uart`, `Wdg_43_Instance1`, `Qspi_Ip`). |
| `platform_sdk` | string | no | RTD folder. Defaults to the sole folder under `mcu_data/components/`, or the one matching `mcu`. |
| `mcu` | string | no | Processor folder under `mcu_data/processors/` (e.g. `S32K312`, `S32G274A`). Needed to resolve resource tables. |
| `package` | string | no | Package variant folder under `<mcu>/<platform_sdk>/` (e.g. `S32K312_172HDQFP`). Defaults to sole package, or errors listing all packages. |
| `s32ds_install` | string | no | Override the auto-discovered install root. |
| `query` | string | no | Free-form question. Empty -> structured overview. |
| `include_mex_shape` | bool | no | Also return an `<instance>` excerpt from the bundled reference `.mex`. Default `false`. |
| `include_doc_link` | bool | no | Resolve `doc/index.md` and return absolute PDF path. Default `true`. |
| `include_resource_table` | bool | no | Resolve `<dynamic_enum>` referenced by the answer. Default `true` (or implied by `query`). |

## Behavior

1. **Resolve paths** from `s32ds_install`, `platform_sdk`, `mcu`,
   `package`, `peripheral_name`.
2. **Parse** `<peripheral_folder>.component` as XML. Mine these elements:
   - `<component:config_component id="..." label="..." category="..."
     max_instances="...">` - top-level metadata (`category` typically
     `AUTOSAR`, `BSW`, `IP`, ...).
   - `<mode id="..." label="..." available="true|false">` - driver modes
     (typical ids: `general`, `autosar`, `non_autosar`, `ip`). Each mode
     lists `<config_set_refs><config_set_ref>...</config_set_ref></config_set_refs>`.
   - `<config_set id="..." label="...">` - top-level UI containers.
   - `<struct id="...">` and `<array id="...">` - nested containers.
   - `<settings>` block: `<bool>`, `<int>`, `<enum>`, `<string>`,
     `<float>`, `<dynamic_enum ref="..."/>`.
   - `<quick_selection id="..." label="...">` with child
     `<set id="<dotted.path>">value</set>` - default presets.
   - `<description>` blocks - quote as supporting text.
3. **Filter** by `query`. Empty -> structured overview: name, label,
   category, max_instances, modes, top-level config containers, list of
   quick selections.
4. **Resolve dynamic enums** - the critical step, see next section.
5. **Cross-reference** (optional):
   - `include_mex_shape` -> quote `<instance name="<peripheral_name>" ...>`
     from the bundled reference `.mex` (when present).
   - `include_doc_link` -> read `doc/index.md`, parse JSON, resolve the
     relative `component-doc-link` against the `.component`'s directory,
     return absolute PDF path.
6. **Return** the formatted Markdown response.

## Resolving `<dynamic_enum>` to package-specific values

Many `.component` settings are not enumerated inline; instead they
declare:

```xml
<dynamic_enum ref="Spi.SpiGeneral.SpiPhyUnit.SpiPhyUnitMapping"/>
```

This means: *the legal values for this setting are defined by the
resource table `Spi.xml` for the currently selected `<package>`*. The
values are package-specific - they reflect the physical instances
exposed by that pinout (an LQFP100 package may expose fewer LPSPIs than
a 172HDQFP). They are **not** discoverable from the `.component` alone.

### Which resource table

- Top-level `resource_tables/<Driver>.xml` is the classic / pre-RTD
  table. Use when the component's `<dynamic_enum ref="...">` namespace
  matches its file id (`id="Spi"` in the example above).
- `resource_tables/RTD/<Driver>.xml` is the RTD-aware table shipped
  with newer Platform SDKs. Some drivers (e.g. `Pwm`, `Uart`, `Mem`,
  `Sent`, `Crc`, `Rm`, `I2s`) only appear under `RTD/`.
- Always try the top-level file first, then fall back to `RTD/`.
  Document which file actually supplied the values in the Resolved
  sources section of the output.

### Anatomy of a resource table

```xml
<resource:resource_table ... id="Spi">
  <user_types>
    <string id="spigeneral.spiphyunit.spiphyunitmapping_type" label="..."/>
    ...
  </user_types>
  <definition>
    <array id="SpiGeneral.SpiPhyUnit.SpiPhyUnitMapping"
           label="..."
           type="spigeneral.spiphyunit.spiphyunitmapping_type"/>
    ...
  </definition>
  <data>
    <array name="SpiGeneral.SpiPhyUnit.SpiPhyUnitMapping">
      <setting name="LPSPI_0" value="LPSPI_0"/>
      <setting name="LPSPI_1" value="LPSPI_1"/>
      <setting name="LPSPI_2" value="LPSPI_2"/>
      <setting name="LPSPI_3" value="LPSPI_3"/>
      <setting name="LPSPI_4" value="LPSPI_4"/>
      <setting name="LPSPI_5" value="LPSPI_5"/>
      <setting name="LPSPI_6" value="LPSPI_6"/>
    </array>
    ...
  </data>
</resource:resource_table>
```

### Resolution algorithm

Given `<dynamic_enum ref="<Driver>.<dotted.Path>"/>`:

1. `<Driver>` = first dotted segment of `ref` (matches the resource
   table's `id=` attribute and filename; case-sensitive on disk but
   generally compared case-insensitively because tables sometimes
   capitalise the id - e.g. file `MCU.xml` with `id="MCU"`).
2. `<Path>` = remaining dotted segments.
3. Open `resource_tables/<Driver>.xml`; if absent, open
   `resource_tables/RTD/<Driver>.xml`.
4. Locate `<data><array name="<Path>">` (or `<array name="<Path>">`
   anywhere under `<data>` for nested tables).
5. Each child `<setting name="X" value="Y"/>` is one legal value. The
   display name is `name`; the value written into the `.mex` is `value`
   (usually identical).

### Worked example: `SpiGeneral.SpiPhyUnit.SpiPhyUnitMapping`

- `.component` (`Spi.component`) declares the setting as
  `<dynamic_enum ref="Spi.SpiGeneral.SpiPhyUnit.SpiPhyUnitMapping"/>`.
- Resource table for `<package>=S32K312_172HDQFP`:
  `.../S32K312_172HDQFP/resource_tables/Spi.xml`.
- Inside, `<array name="SpiGeneral.SpiPhyUnit.SpiPhyUnitMapping">`
  lists `LPSPI_0..LPSPI_6`. Smaller packages may list `LPSPI_0..LPSPI_3`.
  Use the package-resolved list - never assume.

## Common dynamic-enum families (illustrative - confirm per RTD/package)

| Component setting (typical) | Resource table file | `<array name="...">` |
|---|---|---|
| `Spi.SpiGeneral.SpiPhyUnit.SpiPhyUnitMapping` | `Spi.xml` | LPSPI instances |
| `Can.CanController.CanControllerRef` | `Can.xml` | FlexCAN instances (`FLEXCAN_0..`) |
| `Adc.AdcConfigSet.AdcHwUnit.AdcChannel.AdcChannelName` | `Adc.xml` (or `RTD/Adc.xml`) | Channel symbolic names (`P1_ChanNum1`, ...) |
| `Port.PortConfigSet.PortContainer.PortPin.PortPinId` | `Port.xml` | All SIUL2 pad ids on this package |
| `Mcl....DmaChannel...` | `Mcl.xml` | DMA channel ids |
| `Uart.UartGlobalConfig.UartChannel.UartHwUsing` | `RTD/Uart.xml` | LPUART instances |
| `Pwm.PwmChannel.PwmHwChannel` | `RTD/Pwm.xml` | eMIOS/FlexPWM channel ids |
| `Wdg.WdgGeneral.WdgHwInstance` | `Wdg.xml` | Watchdog instance ids |
| `Mcu....McuClockSelector...` | `MCU.xml` (or `RTD/MCU.xml`) | Clock source enumerations |

The table is descriptive, not authoritative. Always confirm by opening
the actual `.component` and the actual `resource_tables/<Driver>.xml`
in the user's install.

## Worked queries

### 1. Overview of a peripheral
> "What can I configure in the `Mcu` peripheral on my S32K3 install?"

`peripheral_name="Mcu"`, `platform_sdk="PlatformSDK_S32K3"` - returns
modes (`autosar`), top-level config set `Mcu`, list of quick selections
(`autosar_default`, ...), main sub-containers
(`McuGeneralConfiguration`, `McuModuleConfiguration`,
`McuClockSettingConfig`, ...), plus any `<dynamic_enum>` references
resolved against `MCU.xml`.

### 2. Specific parameter lookup
> "What does `McuTimeout` mean and what's its default?"

`peripheral_name="Mcu"`, `query="McuTimeout"` - returns the quoted
`<set id="McuGeneralConfiguration.McuTimeout">50000</set>` line plus the
nearest `<description>` block.

### 3. Resolving a dynamic enum
> "Which LPSPI instances can I map under `SpiPhyUnitMapping` on
> `S32K312_172HDQFP`?"

`peripheral_name="Spi"`, `query="SpiPhyUnitMapping"`, `mcu="S32K312"`,
`package="S32K312_172HDQFP"` - follows the `<dynamic_enum ref=...>` in
`Spi.component` to
`processors/S32K312/PlatformSDK_S32K3/S32K312_172HDQFP/resource_tables/Spi.xml`,
returns `LPSPI_0..LPSPI_6`.

### 4. Getting the official PDF reference
> "Where's the full RTD MCU user manual?"

`peripheral_name="Mcu"`, `include_doc_link=true` - resolves
`doc/index.md` and returns the absolute path under
`<S32DS_INSTALL>/S32DS/software/<platform_sdk>/RTD/Mcu_TS_.../doc/RTD_MCU_UM.pdf`.

### 5. Understanding how it lands in a `.mex`
> "How will a configured `Port` instance look inside the `.mex` file?"

`peripheral_name="Port"`, `include_mex_shape=true`, `mcu="S32K312"` -
returns a short `<instance name="Port" ...> ... </instance>` excerpt
from the bundled `S32K312_default.mex` (or a graceful "no bundled
template for this MCU" message).

## Error-message catalog

| Condition | Message template |
|-----------|------------------|
| `<peripheral_folder>.component` missing | `"Peripheral '<peripheral_name>' not found under '<platform_sdk>'. Checked: <abs_path>. Verify the RTD/Platform SDK is installed and the name is spelled correctly (case-sensitive). Available peripherals: <top-N from dir listing>."` |
| `mcu_data/components/<platform_sdk>` missing | `"Platform SDK '<platform_sdk>' is not installed at '<s32ds_install>'. Available SDKs: <list of subfolders>."` |
| `mcu_data/processors/<mcu>/<platform_sdk>` missing | `"MCU '<mcu>' is not installed for SDK '<platform_sdk>'. Available MCUs: <list>."` |
| `<package>` missing under MCU | `"Package '<package>' not present for '<mcu>'. Available packages: <list>."` |
| `.component` XML parse error | `"Failed to parse '<abs_path>': <parser error>. The file may be corrupted; reinstall the RTD package."` |
| Unresolved `<dynamic_enum ref="X.Y">` | `"Dynamic enum 'X.Y' could not be resolved. Tried '<resource_tables/X.xml>' and '<resource_tables/RTD/X.xml>'. Verify that '<package>' exposes this driver."` |
| `query` matches nothing | `"No configuration entry matching '<query>' was found in '<peripheral_name>.component'. Closest matches: <top-N id suggestions>."` |
| `doc/index.md` missing/malformed (with `include_doc_link=true`) | `"Component reference doc link not available for '<peripheral_name>' (doc/index.md missing or invalid)."` - degrade gracefully, still return the main answer. |
| Bundled `.mex` missing (with `include_mex_shape=true`) | `".mex shape requested but no bundled template '<MCU>_default.mex' exists in 'skills/s32ct/s32ct-generate-mex-config/'. Generate one via s32ct-generate-mex-config or s32ct-cli -EmptyConfig -MCU <mcu> -SDKVersion <rtd> -ExportMEX, then place it next to the skill."` - degrade gracefully. |

## Notes for agent reasoning

- The `.component` schema mirrors the `.mex` `<instance>` schema 1-to-1:
  every `<set id="A.B.C">value</set>` inside a `<quick_selection>`
  corresponds to a property path that appears in the `.mex` `<instance>`
  block. Useful for explaining *what gets written* into a `.mex` before
  invoking the Peripherals CLI or `s32ct-peripherals-facade`.
- Always quote from the source files. RTD versions, MCU variants and
  package pinouts differ.
- When exploring an unfamiliar MCU/RTD, first list the available
  peripherals (`dir mcu_data/components/<platform_sdk>`) and the
  available resource tables
  (`dir mcu_data/processors/<mcu>/<platform_sdk>/<package>/resource_tables`)
  before drilling down. The intersection is the set of drivers actually
  configurable for this MCU/package combination.
- For write-side follow-ups see `authoring-instance-reference.md` and
  the write-side sibling skills listed in the main SKILL.md.
