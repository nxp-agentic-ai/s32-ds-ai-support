# Per-driver adaptation rules

This file documents the *minimum set of edits* needed when lifting an `<instance>`
from an RTD example `.mex` for each common AUTOSAR driver. Read the section for
the driver you're adapting; skip the rest.

All concrete enum values below were verified against
`S32K312 / PlatformSDK_S32K3 / TS_T40D34M70I1R0` (RTD examples for S32K344 used
as the lift source). For other MCU/RTD combinations the **shape** of the edits
carries over; the literal values should be confirmed against an RTD example
`.mex` for that target.

---

## Table of contents

1. [`Spi`](#spi)
2. [`Uart`](#uart)
3. [`Can_43_FLEXCAN`](#can_43_flexcan)
4. [`Lin_43_LPUART_FLEXIO`](#lin_43_lpuart_flexio)
5. [`Adc`](#adc)
6. [`Pwm`](#pwm)
7. [Other drivers (general approach)](#other-drivers-general-approach)

---

## `Spi`

**ModuleId 83** (no VendorApiInfix).

The S32K344 `Spi_Transfer.mex` example carries two `SpiPhyUnit` entries  --  one on
`FLEXIO_SPI_0`, one on `LPSPI_1`. For a typical hardware-SPI-only board you
typically want both on physical LPSPI controllers.

Edits per controller you graft:

- `SpiPhyUnitMapping`: swap `FLEXIO_SPI_0` -> your first physical controller
  (e.g. `LPSPI_0`). Legal values come from
  `resource_tables/Spi.xml` array
  `SpiGeneral.SpiPhyUnit.SpiPhyUnitMapping` for the target package.
- `SpiPhyUnitMode`: change `SPI_SLAVE` -> `SPI_MASTER` if the on-board peripheral
  is the slave (which is the common case  --  PMICs, sensors).
- `SpiPhyUnitAsyncUseDma`: set `false` unless you have an `Mcl` instance with
  DMA logical channels. The example often has `true`.
- `SpiGlobalDmaEnable`, `SpiFlexioEnable`: set `false` if you don't have Mcl /
  FlexioCommon.
- Empty out the FlexIO and DMA channel ref arrays  --  `SpiFlexioTxAndClkChannelsConfig`,
  `SpiFlexioRxAndCsChannelsConfig`, `SpiPhyTxDmaChannel`, `SpiPhyRxDmaChannel`.
  They reference `/Mcl/...` paths; absent Mcl -> validator complains.
  `scripts/sanitize.py` does this systematically.

Cross-refs that need rewriting:

- `SpiPhyUnitClockRef` -> typically points at
  `/Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/AIPS_PLAT_CLK` in the
  example. Redirect to `McuClockReferencePoint_0` unless you've added an
  AIPS_PLAT_CLK point via `s32ct-clocks-info`.

Channel/Job/Sequence (`SpiChannel`, `SpiJob`, `SpiSequence`) are
application-level; leave them as the example shipped. The validator accepts
the example's defaults.

---

## `Uart`

**ModuleId 255** (no VendorApiInfix).

The single most common adaptation: the example has one `UartChannel` struct;
you want one per LPUART instance.

Per channel you graft:

- `Name` -> `UartChannel_<idx>_LPUART_<N>`.
- `UartHwUsing` -> `LPUART_IP` (or `FLEXIO_IP` if you're driving a software
  UART on FlexIO; the user's request will tell you).
- `UartChannelId` -> sequential `0`, `1`, ... (NOT the LPUART number).
- `DetailModuleConfiguration/UartHwChannel` -> `LPUART_<N>` (with underscore, e.g.
  `LPUART_6`). This is the physical channel; it lives **inside**
  `DetailModuleConfiguration`, not on `UartChannel` directly. Putting it
  outside is silent failure mode #1.
- `UartHwChannelRef` -> blank string (`value=""`). It's only used when
  `UartHwUsing=FLEXIO_IP` to point at an Mcl FlexIO logical channel.
- `UartDmaTxChannelRef`, `UartDmaRxChannelRef` -> keep as **empty arrays**
  (`<array name="..."/>`). The validator complains if the tag is absent, even
  though it's also fine with empty.

Enum casing (verified S32K3 RTD `T40D34`):

- `LPUART_UART_BAUDRATE_115200` (not `BAUDRATE_115200`)
- `LPUART_UART_IP_USING_INTERRUPTS` (not `USING_INTERRUPTS`)
- `LPUART_UART_IP_PARITY_DISABLED`, `..._ONE_STOP_BIT`, `..._8_BITS_PER_CHAR`.

---

## `Can_43_FLEXCAN`

**ModuleId 80**, VendorApiInfix `FLEXCAN`.

Lifting two `CanController` entries from a single-controller example is the
most common task. The example block has exactly **one** `CanController` struct
inside the `CanController` array  --  you need to duplicate it.

Per controller you graft:

- `Name` -> `CanController_<idx>` (sequential 0, 1, ...).
- `CanControllerId` -> sequential index (NOT the FlexCAN module number).
- `CanHwChannel` -> `FLEXCAN_<N>` (NOT `CanControllerHwChannel`; that field
  doesn't exist). Legal values from `resource_tables/Can.xml`.
- `CanControllerBaudrateConfig_<n>` -> **rename per controller** so each is
  globally unique within the driver. Two controllers can't both contain a
  child named `CanControllerBaudrateConfig_0`  --  the cross-ref resolver gets
  confused. Suffix with the parent index.
- `CanControllerDefaultBaudrate` -> must point at *this* controller's
  baudrate config:
  `/Can_43_FLEXCAN/Can/CanConfigSet/CanController_<idx>/CanControllerBaudrateConfig_<idx>`.

Required siblings that the example already contains:

- `CanGeneral.CanMainFunctionRWPeriods` -> at least one entry. The example
  has one (`CanMainFunctionRWPeriods_0`). Keep it.
- `CanHardwareObject` array -> at least one entry per controller, each with
  at least one `CanHwFilter` child. The example often has two
  `CanHardwareObject` entries already; keep them or duplicate as needed.
  Their `CanControllerRef` should match the right `CanController_<idx>`.

Cross-refs:

- `CanCpuClockRef` -> points at `/Mcu/.../McuClockReferencePoint_0`. The
  example may use a different point; redirect.

---

## `Lin_43_LPUART_FLEXIO`

**ModuleId 82**, VendorApiInfix `LPUART_FLEXIO`.

Enum values are wildly different from what their schema labels suggest:

| Label intuition | Wrong | Right |
|---|---|---|
| LIN master node | `LIN_MASTER_NODE` | `MASTER` |
| LIN 13-bit break | `BREAK_13_BITS` | `BL_13` |
| Detected 11-bit break | `DETECTED_BREAK_11_BITS` | `BL_11` |
| Interrupt-driven | `USING_INTERRUPTS` | `LIN_IP_USING_INTERRUPTS` |

Per channel you graft:

- `Name` -> `LinChannel_<idx>_LPUART_IP_<N>`.
- `LinChannelId` -> sequential index.
- `LinHwChannel` -> `LPUART_IP_<N>` for LPUART-backed LIN, `FLEXIO_IP_<N>` for
  FlexIO-backed LIN. Read the user's request to pick.
- `LinNodeType` -> `MASTER` for master nodes (the common bring-up case).

Cross-refs:

- `LinClockRef` -> `/Mcu/.../McuClockReferencePoint_0`. Will work for
  validation; if the application needs a properly typed LPUART clock,
  add a clock point and redirect.
- `LinFlexioRxChannelRef`, `LinFlexioTxChannelRef`, `LinFlexioTimerChannelRef`,
  `LinDmaRxChannelRef`, `LinDmaTxChannelRef` -> empty out (point at /Mcl/).
  `scripts/sanitize.py` does this.

---

## `Adc`

**ModuleId 123** (no VendorApiInfix).

The example carries internal-channel choices (`BANDGAP_ChanNum48`,
`VREFH_ChanNum55`). Those are perfectly valid for validation but probably not
what the user wants if their Pins tool has routed external ADC pins.

Per HwUnit you graft (typically `ADC0` and/or `ADC1`):

- `AdcHwUnitId` -> `ADC0` or `ADC1` (no underscore, no `_HwUnit` suffix).
- `AdcChannel` array -> at least one entry per HwUnit (`min_expr="1"`).
- `AdcChannelName` -> `P<N>_ChanNum<N>` for external analog pins
  (e.g. `P1_ChanNum1` for ADC0_P1 = PTD0 on S32K312_172HDQFP). Legal values
  from `resource_tables/RTD/Adc.xml`.
- `AdcChannelId` -> **must equal the trailing number of `AdcChannelName`**.
  Mismatched pair -> "Adc Physical Channel ID must equal number after ChanNum".
- `AdcGroup` array -> at least one entry per HwUnit.
- `AdcGroupId` -> **globally unique across all HwUnits**, not per-HwUnit. Use
  a running counter.
- `AdcGroupDefinition` -> **ref array**, not struct array. Emit as
  `<setting name="0" value="/Adc/Adc/AdcConfigSet/<HwUnitName>/<ChannelName>"/>`.
  Wrapping in `<struct>` causes silent value loss.
- `AdcGroupConversionConfiguration`, `AdcAlternateGroupConvTimings` -> each
  needs a `Name`. The example has them; keep them.

Top-level structure quirk:

- `AdcHwConfiguration` is a top-level array **directly under
  `<config_set name="Adc">`**, sibling of `AdcConfigSet`  --  not nested inside
  `AdcConfigSet`. The example respects this; preserve the structure on splice.
- `AdcPublishedInformation` co-exists with `CommonPublishedInformation`. Adc
  is one of the few drivers with both. The example contains both; keep both.

If the channel name change is tricky to get right on the first pass, leaving
the example's `BANDGAP_ChanNum48` channel is a valid intermediate  --  validation
passes; the application just won't read external pins via that instance until
you fix it. Better than blocking the whole `.mex` on a single field.

---

## `Pwm`

**ModuleId 121** (no VendorApiInfix). One of the trickier drivers because eMIOS
counter-bus mode, PWM operation mode, and channel number are co-constrained.

Per channel you graft:

- `PwmChannelId` -> sequential.
- `PwmHwChannel` -> ref into `PwmChannelConfigSet/PwmEmios_<i>/PwmEmiosChannels_<j>`.
- `PwmPeriodInTicks` -> set `true`. If false, the value is in seconds and
  S32CT multiplies by the input clock to compute ticks; this *always*
  overflows the uint16 cap.
- `PwmPeriodDefault` -> <= 65534 (uint16 ceiling).
- `PwmMcuClockReferencePoint` -> `/Mcu/.../McuClockReferencePoint_0`.

Per `PwmEmios` entry:

- `PwmHwInstance` -> `Emios_0`, `Emios_1`, ...
- `PwmEmiosChannels[i].EmiosChId` -> `CH_<N>`.
- `EmiosChMode` + `EmiosChCounterBus` must be compatible. The simplest valid
  combination is `EMIOS_PWM_IP_MODE_OPWFMB` + `EMIOS_PWM_IP_BUS_INTERNAL`.
  This combination requires no `PwmEmiosBusRef` and therefore no Mcl
  EmiosCommon instance.

Channel/mode compatibility caveat:

- Not every channel supports every mode. The constraint is encoded in
  `RTD/Pwm.xml` arrays `EmiosPwmModesMappingInst_0`, `_1` as bitmasks. If you
  pick `OPWFMB` and the target channel doesn't support it, validation fails
  with *"OPWFMB mode is not available for selected channel!"*  --  switch
  channel or mode (CH_0 through CH_7 on eMIOS_0 tend to support the widest
  set of modes).

If the example has channels you don't need, **drop them entirely**  --  remove
the `PwmEmios` struct, remove the corresponding `PwmChannel` struct, renumber
the survivors. Keeping unused channels around in a graft that doesn't
validate is the most common pitfall.

`ConfigTimeSupport.IMPLEMENTATION_CONFIG_VARIANT` is `VARIANT-POST-BUILD` for
Pwm (different from most other drivers which use `VARIANT-PRE-COMPILE`).
The example has it correct; preserve it.

---

## Other drivers (general approach)

For any driver not in the list above (e.g. `Wdg_43_Instance<N>`, `Icu`,
`Gpt`, `I2c`, `Eth_43_GMAC`, `Mcl`, `Crypto`):

1. Find the matching RTD example `.mex` via `scripts/discover.py`. The
   example directory's name typically describes its scope
   (e.g. `Wdg_Example_S32K344`).
2. Extract its `<instance type_id="<Driver>">...</instance>` with
   `scripts/extract_examples.py`.
3. Inspect the block to identify the hw-channel-selector fields. Common names:
   - `<Driver>HwInstance`, `<Driver>HwUnit`, `<Driver>HwChannel`
   - Anything inside an `<array name="<Driver>Channel">` struct that picks
     a physical resource (look for fields whose value matches a string from
     `resource_tables/<Driver>.xml`).
4. Adapt those fields to the target board's routing.
5. Splice, sanitize, validate. The sanitize pass is driver-agnostic and
   will handle generic Mcl/Mcu cross-ref cleanup.

The skill exists *because* the same workflow works across all drivers. If
you find yourself doing something dramatically different for a particular
driver, it's worth pausing to ask whether `s32ct-peripherals-author-mex`
(the from-scratch path) is a better fit for that specific case.
