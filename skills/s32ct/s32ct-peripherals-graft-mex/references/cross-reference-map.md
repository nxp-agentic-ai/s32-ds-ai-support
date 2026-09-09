# Cross-reference map

A catalogue of the cross-reference families that typically fail when grafting
RTD example instances into a project, with the canonical sanitize rule for
each.

`scripts/sanitize.py` encodes all of these. This file exists for human-
readable documentation of *what* the script does and *why*, so you can
extend it for new MCUs or RTD versions.

---

## `/Mcu/Mcu/McuModuleConfiguration/...`

**Pattern**:
```
value="/Mcu/Mcu/McuModuleConfiguration/<config>/<point>"
```

Where `<point>` may be:
- `McuClockReferencePoint_0` ... `McuClockReferencePoint_N`
- Named clock outputs: `LPUART_CLK`, `LPUART3_CLK`, `AIPS_PLAT_CLK`,
  `AIPS_SLOW_CLK`, `CAN_PE_CLK`, `EMIOS_CLK`, etc.
- Named configurations: `BOARD_BootClockRUN`, `BOARD_BootClockSTANDBY`, etc.

**Reality**: a freshly templated Mcu instance typically contains *only*
`McuClockSettingConfig_0/McuClockReferencePoint_0`. Every other named
clock output or configuration is a dangling reference.

**Sanitize rule**: redirect every value matching this pattern that doesn't
already end in `McuClockReferencePoint_0` to
`/Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/McuClockReferencePoint_0`.

**Per-driver fields commonly affected**:

| Driver | Field |
|---|---|
| Spi | `SpiPhyUnitClockRef`, `SpiPhyClock` |
| Uart | (none in current K3 example) |
| Can_43_FLEXCAN | `CanCpuClockRef`, `CanControllerCpuClockRef` |
| Lin_43_LPUART_FLEXIO | `LinClockRef`, `LinChannelClockRef` |
| Adc | `AdcClockRef`, `AdcGroupClockSource` |
| Pwm | `PwmMcuClockReferencePoint`, `PwmClockSource` |

**Long-term fix** (not done by this skill): use `s32ct-clocks-info` to
add the matching `McuClockReferencePoint_*` entries for `LPUART_CLK`,
`AIPS_PLAT_CLK`, etc.  --  then redirect back to the proper points so the
runtime gets the right clock frequency. The sanitize pass only ensures
validation passes; runtime correctness requires real clock points.

---

## `/Mcl/Mcl/MclConfig/...`

**Pattern**:
```
value="/Mcl/Mcl/MclConfig/<container>/<entry>"
```

Where `<container>` is most often:
- `EmiosCommon_<i>/EmiosMclMasterBus_<j>`  --  PWM eMIOS counter-bus refs.
- `FlexioCommon_<i>/FlexioMclLogicChannels_<j>`  --  FlexIO logic-channel refs
  for Uart/Spi/Lin in FlexIO mode.
- `CHANNEL_FOR_<DRIVER>_<N>`  --  DMA logic channels.

**Reality**: an Mcl driver instance is rarely in the user's `.mex` by
default. The RTD examples create one as a sibling of the main driver and
then cross-reference into it.

**Sanitize rule**:

- If the reference is inside an `<array name="X">...</array>` block, replace
  the whole array with a self-closing tag: `<array name="X"/>`. The
  validator is happy with empty arrays in most cases (DMA channels, FlexIO
  channels, etc.); it's just the dangling reference that breaks it.
- If the reference is a singleton `<setting name="Y" value="/Mcl/..."/>`, blank
  the value: `<setting name="Y" value=""/>`. The corresponding feature is
  then disabled at codegen.

**Affected arrays** (representative; the script discovers them dynamically):

| Driver | Arrays |
|---|---|
| Spi | `SpiPhyTxDmaChannel`, `SpiPhyRxDmaChannel`, `SpiPhyTxCmdDmaChannel`, `SpiFlexioTxAndClkChannelsConfig`, `SpiFlexioRxAndCsChannelsConfig` |
| Uart | `UartDmaTxChannelRef`, `UartDmaRxChannelRef` (also: `UartHwChannelRef` is a singleton) |
| Lin | `LinDmaTxChannelRef`, `LinDmaRxChannelRef`, `LinFlexioRxChannelRef`, `LinFlexioTxChannelRef`, `LinFlexioTimerChannelRef` |
| Adc | `AdcDmaChannelRef`, `AdcHwUnitDma` |
| Pwm | `PwmEmiosMasterBusRef`, `PwmEmiosCounterBusRef` (singletons or singleton arrays) |

**Long-term fix** (not done by this skill): graft an `Mcl` driver instance
from its own RTD example, then re-point the refs into it. Same lift-and-adapt
workflow as for the other drivers.

---

## Singleton ref settings

A few settings hold an Mcl/Mcu path as a single `value=` attribute (not
wrapped in an array). Blanking the value is the right fix for these,
*not* removing the setting  --  the schema may require the setting to be
present.

Known cases:

| Setting | When it's a singleton |
|---|---|
| `UartHwChannelRef` | Always (it's a single ref, only meaningful when `UartHwUsing=FLEXIO_IP`). |
| `SpiPhyClock` | When the example references a peripheral-specific clock point. |
| `PwmEmiosMasterBusRef` | When Pwm uses non-INTERNAL counter bus. |

`scripts/sanitize.py` handles the named singletons explicitly. New
singletons discovered in future RTD versions should be added to the script's
`SINGLETON_BLANK` list.

---

## Renamed cross-references inside the same driver

A separate failure mode (not handled by `sanitize.py`  --  needs manual fix
during the adapt step):

When you duplicate an example's single controller to two controllers
(typical for `Can_43_FLEXCAN`), some child structs end up sharing names
across the two parents (`CanControllerBaudrateConfig_0` under both
`CanController_0` and `CanController_1`). The cross-reference resolver then
fails with "destination node must be within driver".

**Fix during adapt**: rename per-parent. `splice.py` does this for
`Can_43_FLEXCAN`; for other drivers with the same pattern, add a rename
loop in the driver's `adapt_<driver>()` function.

| Driver | Pattern to rename per-parent |
|---|---|
| Can_43_FLEXCAN | `CanControllerBaudrateConfig_<n>` -> `_<parent_idx>` |
| Adc | `AdcChannel_<n>`, `AdcGroup_<n>` (group IDs are globally unique) |
| Lin | (usually not needed; LinChannel is the only repeated container) |

---

## How to extend this map for a new MCU / RTD

When you encounter a "value not available" that survives `sanitize.py`:

1. Grep the offending instance for cross-references.
   Windows: `findstr value=\"/ <mex_file>`.
   Linux/macOS: `grep 'value="/' <mex_file>`.
2. Look at each `/Foo/...` reference  --  does the `/Foo/` driver exist as an
   `<instance type_id="Foo">` in your `.mex`?
3. If no, the reference is dangling. Decide:
   - Is this a *new* family of references (not in this map)? Add it here
     and update `sanitize.py`.
   - Is the reference inside an array -> self-close it.
   - Is it a singleton -> blank the value.

4. Document the case so the next agent doesn't have to rediscover it.
