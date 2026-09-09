# Per-driver authoring contract & critical pitfalls

This file is the lookup table referenced from `SKILL.md` of
`s32ct-peripherals-author-mex`. It holds the per-driver verified snippets and
the catalogue of critical pitfalls that any author of a Peripherals-tool
`<instance>` block must cross-check.

> All concrete values below were verified by running `-ShowProblems` against
> an **S32K312MINI-EVB `.mex`** and reading each driver's K344 RTD example.
> **For any other MCU/RTD, re-verify against the matching RTD example
> before you trust a constant.** The structural rules (which container
> holds which setting, what's a ref array vs a struct array, what
> `min_expr="1"` requires) carry over; the literal enum strings and
> ModuleIds may not.
>
> **ModuleIds are RTD-version-dependent.** Read the
> `<integer id="ModuleId">` from the `.component` of your specific RTD
> instead of taking the numbers below as gospel.

---

## Per-driver authoring contract (the lookup table)

### `Spi` (verified ModuleId 83, no VendorApiInfix)

Structural notes for the snippet below:

- `SpiPhyUnit` lives inside the `SpiGeneral` struct, **not** inside
  `SpiDriver`.
- Emit one `SpiPhyUnit` struct per controller. Legal `SpiPhyUnitMapping`
  values come from `resource_tables/Spi.xml` for the target PACKAGE.
- `CommonPublishedInformation` is required - see Critical pitfall #1.

```xml
<instance name="Spi" uuid="..." type="Spi" type_id="Spi" mode="autosar" ...>
  <config_set name="Spi">
    <setting name="Name" value="Spi"/>
    <struct name="ConfigTimeSupport">
      <setting name="Name" value="ConfigTimeSupport"/>
      <setting name="POST_BUILD_VARIANT_USED" value="false"/>
      <setting name="IMPLEMENTATION_CONFIG_VARIANT" value="VARIANT-PRE-COMPILE"/>
    </struct>
    <struct name="SpiGeneral">
      <setting name="Name" value="SpiGeneral"/>
      <setting name="SpiTimeoutMethod" value="OSIF_COUNTER_DUMMY"/>
      <setting name="SpiDevErrorDetect" value="false"/>
      <setting name="SpiCancelApi" value="true"/>
      <setting name="SpiHwStatusApi" value="true"/>
      <setting name="SpiInterruptibleSeqAllowed" value="false"/>
      <setting name="SpiLevelDelivered" value="2"/>
      <setting name="SpiSupportConcurrentSyncTransmit" value="false"/>
      <setting name="SpiVersionInfoApi" value="true"/>
      <setting name="SpiGlobalDmaEnable" value="false"/>
      <array name="SpiPhyUnit">
        <struct name="0">
          <setting name="Name" value="SpiPhyUnit_0_LPSPI_0"/>
          <setting name="SpiPhyUnitMapping" value="LPSPI_0"/>
          <setting name="SpiPhyUnitMode" value="SPI_MASTER"/>
          <setting name="SpiPhyUnitAsyncUseDma" value="false"/>
        </struct>
      </array>
    </struct>
    <struct name="SpiDriver"> <setting name="Name" value="SpiDriver"/> </struct>
    <struct name="SpiAutosarExt"> ... </struct>
    <struct name="CommonPublishedInformation">
      <setting name="Name" value="CommonPublishedInformation"/>
      <setting name="ModuleId" value="83"/>
      <setting name="VendorId" value="43"/>
      <setting name="VendorApiInfix" value=""/>
      <setting name="ArReleaseMajorVersion" value="4"/>
      <setting name="ArReleaseMinorVersion" value="9"/>
      <setting name="ArReleaseRevisionVersion" value="0"/>
      <setting name="SwMajorVersion" value="7"/>
      <setting name="SwMinorVersion" value="0"/>
      <setting name="SwPatchVersion" value="1"/>
    </struct>
  </config_set>
</instance>
```

### `Uart` (verified ModuleId 255, no VendorApiInfix)

Key surprises:

- `UartHwUsing` in **`LPUART_IP`** or **`FLEXIO_IP`**  -  *not* the channel
  number.
- The hardware channel selector is **`UartHwChannel`** with values
  **`LPUART_<N>`** (with underscore!)  -  and it lives **inside
  `DetailModuleConfiguration`**, not on the `UartChannel` directly.
- Enum constants are prefixed: `LPUART_UART_BAUDRATE_115200`,
  `LPUART_UART_IP_USING_INTERRUPTS`, `LPUART_UART_IP_PARITY_DISABLED`,
  `LPUART_UART_IP_ONE_STOP_BIT`, `LPUART_UART_IP_8_BITS_PER_CHAR`.
- `UartDmaTxChannelRef`/`UartDmaRxChannelRef` must be present as **empty
  arrays** even when DMA is disabled  -  otherwise validator complains "at
  least one DMA channel ref must be configured".

```xml
<array name="UartChannel">
  <struct name="0">
    <setting name="Name" value="UartChannel_0_LPUART_6"/>
    <setting name="UartHwUsing" value="LPUART_IP"/>
    <setting name="UartChannelId" value="0"/>
    <array name="UartChannelEcucPartitionRef"/>
    <struct name="DetailModuleConfiguration">
      <setting name="Name" value="DetailModuleConfiguration"/>
      <setting name="UartHwChannel" value="LPUART_6"/>
      <setting name="DesireBaudrate" value="LPUART_UART_BAUDRATE_115200"/>
      <setting name="UartInteruptDmaMethod" value="LPUART_UART_IP_USING_INTERRUPTS"/>
      <array name="UartDmaTxChannelRef"/>
      <array name="UartDmaRxChannelRef"/>
      <setting name="UartParityType" value="LPUART_UART_IP_PARITY_DISABLED"/>
      <setting name="UartStopBitNumber" value="LPUART_UART_IP_ONE_STOP_BIT"/>
      <setting name="UartWordLength" value="LPUART_UART_IP_8_BITS_PER_CHAR"/>
      <setting name="UartInternalLoopbackEnable" value="false"/>
      <setting name="UartTimeoutEnable" value="false"/>
    </struct>
  </struct>
</array>
```

### `Can_43_FLEXCAN` (verified ModuleId 80, VendorApiInfix `FLEXCAN`)

Key surprises:

- The hardware channel field is **`CanHwChannel`** (NOT
  `CanControllerHwChannel`, which doesn't exist). Values: `FLEXCAN_0` ...
  `FLEXCAN_<N>` from `resource_tables/Can.xml` for the target PACKAGE.
- `CanControllerId` is the **sequential array index** (0, 1, 2, ...), not
  the FlexCAN module number. Using `1`/`4` for two controllers -> "value
  out of range".
- **Each controller's `CanControllerDefaultBaudrate` must reference a
  unique `CanControllerBaudrateConfig_*` node.** If both controllers use
  a baudrate config named `CanControllerBaudrateConfig_0`, the validator
  emits "The destination node referenced must be within Can_43_FLEXCAN
  Driver". Use `CanControllerBaudrateConfig_<controller_index>` per
  controller.
- `CanGeneral` needs a `CanMainFunctionRWPeriods` array with at least one
  entry containing `Name` and `CanMainFunctionPeriod`.
- Per-controller you must also emit `CanCpuClockRef` pointing at an
  existing `McuClockReferencePoint_*` in the `.mex`.
- `CanHardwareObject` array (sibling of `CanController` at `CanConfigSet`
  level) must contain at least one entry per controller, each with at
  least one `CanHwFilter` sub-entry.
- Sub-structs `CanPartialNetwork` and `CanXLController` need explicit
  `Name` even if otherwise empty.

Reading the snippet below: `CanHwChannel` is the correct field name
(`CanControllerHwChannel` does not exist); `CanControllerId` is the
sequential array index; the first `CanControllerBaudrateConfig` name must be
unique per controller (`..._0` under `CanController_0`, `..._1` under
`CanController_1`); and the elided regions stand for the remaining
`<quick_selection>` bool/enum defaults and the full 14-setting baud-rate
config.

```xml
<struct name="CanConfigSet">
  <setting name="Name" value="CanConfigSet"/>
  <array name="CanController">
    <struct name="0">
      <setting name="Name" value="CanController_0"/>
      <setting name="CanHwChannel" value="FLEXCAN_1"/>
      <setting name="CanControllerBaseAddress" value="0"/>
      <setting name="CanControllerId" value="0"/>
      <setting name="CanControllerActivation" value="true"/>
      <setting name="CanControllerDefaultBaudrate"
               value="/Can_43_FLEXCAN/Can/CanConfigSet/CanController_0/CanControllerBaudrateConfig_0"/>
      <array name="CanControllerEcucPartitionRef"/>
      <setting name="CanCpuClockRef"
               value="/Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/McuClockReferencePoint_0"/>
      <array name="CanControllerBaudrateConfig">
        <struct name="0">
          <setting name="Name" value="CanControllerBaudrateConfig_0"/>
        </struct>
      </array>
      <array name="CanRamBlock"/>
      <array name="CanRxFiFo"/>
      <array name="CanControllerTimeStamp"/>
      <struct name="CanPartialNetwork">
        <setting name="Name" value="CanPartialNetwork"/>
        <setting name="CanPnEnabled" value="false"/>
      </struct>
      <struct name="CanXLController">
        <setting name="Name" value="CanXLController"/>
      </struct>
    </struct>
    <struct name="1">
      <setting name="Name" value="CanController_1"/>
      <setting name="CanHwChannel" value="FLEXCAN_4"/>
      <setting name="CanControllerId" value="1"/>
      <setting name="CanControllerDefaultBaudrate"
               value="/Can_43_FLEXCAN/Can/CanConfigSet/CanController_1/CanControllerBaudrateConfig_1"/>
      <array name="CanControllerBaudrateConfig">
        <struct name="0">
          <setting name="Name" value="CanControllerBaudrateConfig_1"/>
          ...
```

### `Lin_43_LPUART_FLEXIO` (verified ModuleId 82, VendorApiInfix `LPUART_FLEXIO`)

Enum values **completely different** from what their schema labels suggest
(verified on K312; other RTDs may rename  -  always cross-check with the
example mex):

- `LinNodeType` = `MASTER`  *(not `LIN_MASTER_NODE`)*
- `BreakLength` = `BL_13`   *(not `BREAK_13_BITS`)*
- `DetectedBreakLength` = `BL_11`  *(not `DETECTED_BREAK_11_BITS`)*
- `LinInteruptDmaMethod` = `LIN_IP_USING_INTERRUPTS`  *(not `USING_INTERRUPTS`)*
- `LinHwChannel` in `LPUART_IP_<0..N>` for LPUART-LIN, `FLEXIO_IP_<0..M>` for
  FlexIO-LIN.

`LinClockRef` cross-ref: in many `.mex` templates only
`McuClockReferencePoint_0` exists  -  point at that. If the application later
adds an `LPUART_CLK` reference point, repoint it.

### `Adc` (verified ModuleId 123, no VendorApiInfix)

Key surprises:

- `AdcHwUnitId` in `ADC0`, `ADC1`, `ADC2` (no underscore, no `_HwUnit`
  suffix). Read the per-package list from `resource_tables/Adc.xml`.
- `AdcChannelName` uses the form **`P<N>_ChanNum<N>`** for physical analog
  pins (`P1_ChanNum1` for `ADC0_P1`)  -  discovered from the
  `<PACKAGE>/resource_tables/Adc.xml` data array. **Not** `AN_1` (the
  K312-AE variant naming) and not the bare integer. Other MCUs/packages
  may use yet another naming  -  always read the actual `<array>` entries
  from the package's `Adc.xml`.
- `AdcGroupId` must be **globally unique** across all HwUnits, not just
  within one. Two groups both named "0" -> "Group id must be unique among
  all Groups in all Hw Units".
- `AdcChannel` and `AdcGroup` arrays both have `min_expr="1"`  -  at least
  one entry each, per `AdcHwUnit`.
- `AdcGroupDefinition` is a **ref array**, not a struct array  -  emit as
  `<setting name="0" value="/Adc/Adc/AdcConfigSet/<HwUnitName>/<ChannelName>"/>`,
  not as nested struct/Name pairs.
- The required sub-structs `AdcGroupConversionConfiguration` and
  `AdcAlternateGroupConvTimings` each need their own `Name`.
- `AdcHwConfiguration` is a **top-level array directly under
  `<config_set name="Adc">`**, sibling of `AdcConfigSet`. One entry per
  ADC HW unit, with `AdcHwConfiguredId="ADC0"` / `ADC1`.
- Leave `AdcHwTrigger` and `BctuHwUnit` arrays present-but-empty under
  `AdcConfigSet` so the validator doesn't auto-create unnamed elements.
- The top-level published-info struct is **`AdcPublishedInformation`**
  (Adc is one of the few drivers with both `AdcPublishedInformation`
  and `CommonPublishedInformation`).

### `Pwm` (verified ModuleId 121, no VendorApiInfix)

Key surprises:

- `PwmPeriodDefault` is **a tick count (uint16)**. If
  `PwmPeriodInTicks=false` it's interpreted in seconds x bus_clock and
  almost always overflows (`period 120 000 000 ticks > max 65 534`).
  Always set `PwmPeriodInTicks=true` and use a tick value <= 65534.
- The hardware-side container hierarchy is
  `PwmChannelConfigSet -> PwmEmios[] -> PwmEmiosChannels[]`. Each
  `PwmEmios` represents one eMIOS instance (`PwmEmios_0`, `PwmEmios_1`),
  each `PwmEmiosChannels` is one channel within it.
- `EmiosChCounterBus="EMIOS_PWM_IP_BUS_INTERNAL"` is the simplest valid
  counter source.
- `ConfigTimeSupport.IMPLEMENTATION_CONFIG_VARIANT` is `VARIANT-POST-BUILD`
  for Pwm (different from the others which are `VARIANT-PRE-COMPILE`).

### Other drivers (Wdg, Icu, Ocu, Gpt, Eth, Mcl, Crypto, ...)

The 5-source rule applies unchanged. For any driver not listed above:

1. Find its folder under `<S32DS_INSTALL>/S32DS/software/<PLATFORM_SDK>/RTD/`
    -  the prefix tells you the canonical instance type (`Wdg_43_INSTANCE`,
   `Icu_43_GPT`, ...).
2. Read `<integer id="ModuleId">` from its `.component` for the table
   below.
3. Read its **example `.mex`** as the structural template  -  this is
   non-negotiable. Driver-specific containers always have surprises that
   no schema dump reveals.

---

## Critical pitfalls (the bugs that cost 25+ validation iterations)

> Preserve verbatim  -  every entry was paid for in real debugging time on
> the S32K312MINI-EVB session. The literals (e.g. `LPUART_6`, `FLEXCAN_1`,
> `P1_ChanNum1`) are S32K312-specific; the **shape** of each pitfall (which
> container is missing, which field is misnamed, which array must be empty
> but present) is universal.

### 1. **Missing `CommonPublishedInformation`** -> "Name must be a valid C identifier"

Every AUTOSAR driver `<config_set>` needs a
`<struct name="CommonPublishedInformation">` sibling with **all 10
sub-settings populated**. If you omit it, the validator auto-creates the
struct with `Name=""` and emits the cryptic *"Name must be a valid C
identifier"* error  -  which doesn't point at the actual missing element.

To diagnose: enumerate the top-level children of `<config_set>` in your
`.mex` and compare to the matching RTD example mex. Use the helper
`compare_children.py` (in `scripts/`). If anything is in the example but
not in yours, add it  -  even if it's "just metadata".

**ModuleIds (verified on S32K312 / PlatformSDK_S32K3 / `TS_T40D34M70I1R0`**  - 
read each `.component`'s `<integer id="ModuleId" min_expr="..." max_expr="..."/>`
on your target to confirm**):**

| Driver | ModuleId | VendorApiInfix |
|---|---|---|
| Spi | 83 | (empty) |
| Uart | 255 | (empty) |
| Can_43_FLEXCAN | 80 | FLEXCAN |
| Lin_43_LPUART_FLEXIO | 82 | LPUART_FLEXIO |
| Adc | 123 | (empty) |
| Pwm | 121 | (empty) |

All use VendorId 43, AR 4.9.0, SW 7.0.1 **for the RTD versions tested**.
Different RTD versions ship different AR/SW version numbers  -  read them
from the `.component` of your target RTD.

### 2. **Cross-reference paths reusing names** -> "destination node must be within Driver"

If two parent structs each contain a child named
`CanControllerBaudrateConfig_0`, and a third structure's
`CanControllerDefaultBaudrate` ref tries to point at either one, the
validator gets confused and reports the ref as out-of-driver even though
the path syntactically resolves. **Make every named child in the `.mex`
globally unique within its driver instance**  -  suffix names with the
parent's index (e.g. `CanControllerBaudrateConfig_0` under
`CanController_0`, `CanControllerBaudrateConfig_1` under `CanController_1`).

### 3. **Enum value casing & prefixing**

The single most common silent-failure mode. The schema label in the
`.component` looks like `"Lin Master Node"` but the actual XML value is
`MASTER`. Sources of truth:

- `<dynamic_enum>` -> look up the linked `<resource_table>` `<array>`
  `<setting value="..."/>` entries.
- `<enum>` -> the inline `<value id="..."/>` entries.
- **Best of all**: open the matching RTD example `.mex` and read the exact
  string. Do this *before* writing your first `<setting>`.

Confirmed gotchas from the S32K312 run (re-verify on other targets):

| Schema label intuition | WRONG | RIGHT |
|---|---|---|
| Map an LPSPI controller to LPSPI0 | `LPSPI0` | `LPSPI_0` |
| Select LPUART hardware channel 6 | `LPUART6` | `LPUART_6` |
| Use LPUART_IP_5 for LIN | (any) | `LPUART_IP_5` |
| LIN master node | `LIN_MASTER_NODE` | `MASTER` |
| LIN 13-bit break | `BREAK_13_BITS` | `BL_13` |
| ADC channel 1 on ADC0 | `1` or `AN_1` | `P1_ChanNum1` |
| FlexCAN module 1 hw channel | `CanControllerHwChannel="FLEXCAN1"` | `CanHwChannel="FLEXCAN_1"` |
| 115200 baud | `BAUDRATE_115200` | `LPUART_UART_BAUDRATE_115200` |
| Interrupt-driven UART | `USING_INTERRUPTS` | `LPUART_UART_IP_USING_INTERRUPTS` |

### 4. **`AdcGroupDefinition` as ref array, not struct array**

`<array name="AdcGroupDefinition">` contains
`<setting name="0" value="/Adc/.../AdcChannel_X"/>` entries  -  flat
key/path pairs. Many other ref-arrays in the same driver (e.g.
`AdcGroupEcucPartitionRef`, `LinDmaRxChannelRef`) follow the same
pattern. If you wrap them in `<struct>` elements, the parser swallows the
value silently.

### 5. **Pwm period overflow** -> "period <N> ticks > max 65 534"

`PwmPeriodDefault` is a uint16. Either:
- set `PwmPeriodInTicks=true` and choose a value <= 65534 (recommended), or
- if `PwmPeriodInTicks=false`, the unit is **seconds** and S32CT
  internally multiplies by the channel's input clock to compute ticks  - 
  almost always blows the uint16 ceiling.

### 6. **Pin-routing conflicts that bleed into the Peripherals tool**

On many S32 packages the same physical pin is the *only* option for two
different peripherals (e.g. on S32K312 172HDQFP the only CAN0 pins are
PTB0/PTB1, which are also the only LPSPI0 PCS0/SOUT pins). If a board
mux'd the pins for one peripheral via `s32ct-pins-author-mex`, the Peripherals
tool will still let you instantiate a *driver* for the conflicting
peripheral, but it will be unreachable at runtime. **Cross-check your
driver list against the actual Pins-tool routing in the `.mex`** before
adding instances. Either drop the conflicting driver or re-route in pins.

### 7. **`UartHwUsing` semantics**

`UartHwUsing` selects the *back-end type* (`LPUART_IP` vs `FLEXIO_IP`),
**not** the physical channel. The physical channel goes in
`DetailModuleConfiguration/UartHwChannel`. Putting `LPUART_6` directly
into `UartHwUsing` produces "value not available" + "duplicated
UartHwChannel" because every channel falls through to the same default.

### 8. **`LinClockRef` / `CanCpuClockRef` target existing clock points**

These refs point into
`Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/McuClockReferencePoint_<N>`.
The bundled `<MCU>_default.mex` template typically ships with **only
`McuClockReferencePoint_0`**  -  any path to `LPUART_CLK`, `FLEXIO_CLK`,
`CAN_CLK`, etc. resolves to null and the validator reports "value not
available". Either:

- Point the refs at `McuClockReferencePoint_0` (works for AUTOSAR
  validation but driver C-source generation needs a properly typed clock
  ref), or
- Add the needed `McuClockReferencePoint_<N>` to the Mcu instance  -  see
  the separate `s32ct-clocks-info` skill for that.

### 9. **DMA channel refs must be empty arrays, not absent**

Several `*_DmaChannelRef` arrays have `min_expr="0"` but the validator
emits *"at least one DMA channel ref must be configured"* if the array
tag is **missing entirely**. Emit them as
`<array name="UartDmaTxChannelRef"/>` (empty, single self-closing tag)
when DMA is disabled.

### 10. **The `s32ct_*` MCP wrappers truncate stderr**

`stderr_tail` is ~3 KB and starts from the beginning  -  you'll see the
launch preamble, not the `[TOOL]` problems at the bottom. Always validate
via the `.bat` wrapper, **never** through the MCP wrapper alone.
