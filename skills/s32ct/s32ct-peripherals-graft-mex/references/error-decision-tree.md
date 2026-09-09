# Error decision tree

When `scripts/filter_problems.py` shows real `SEVERE: [TOOL]` lines, match
the message pattern below to find the targeted fix. Every entry comes from a
real session  --  the fix has been verified, not guessed.

If a problem doesn't match any pattern below, **don't guess**. Open the
matching RTD example `.mex` for the offending driver and read the canonical
XML  --  it will show the correct field name or value.

---

## "The value is not available"

This is the catch-all "you put an enum value or a cross-reference path the
validator can't resolve" error. It's the single most common pattern.

**Diagnostic step**: read the offending instance's `<setting>` values and check
each cross-reference (`value="/Foo/..."`) and each enum (`value="ENUM_NAME"`)
in turn.

**Common root causes** (in order of frequency):

1. **Clock-ref path pointing at a non-existent McuClockReferencePoint.**
   The template typically has only `McuClockReferencePoint_0`. Anything else
   (`LPUART_CLK`, `AIPS_PLAT_CLK`, `BOARD_BootClockRUN/*`, `LPUART3_CLK`, ...)
   is dangling.
   -> **Fix**: run `scripts/sanitize.py`  --  it sweeps all
   `/Mcu/Mcu/McuModuleConfiguration/...` paths and redirects to
   `McuClockReferencePoint_0`.

2. **Cross-reference into an absent driver.** Most often `/Mcl/Mcl/MclConfig/...`
   (DMA logical channel, FlexioCommon logic channel, EmiosCommon master bus).
   The grafted example expected an Mcl instance you don't have.
   -> **Fix**: run `scripts/sanitize.py`  --  it self-closes any `<array>`
   element whose body references an absent driver, and blanks singleton refs.

3. **Enum value with wrong casing or wrong prefix.** Schema label says
   "LIN Master Node" but the legal value is `MASTER`. Schema says "115200" but
   the legal value is `LPUART_UART_BAUDRATE_115200`. The example you grafted
   from has the right value already  --  if you've changed it manually, revert.
   -> **Fix**: re-extract the example block and rerun `scripts/splice.py`
   without manual enum edits.

4. **Hw-channel selector not present on the target package.** You set
   `CanHwChannel="FLEXCAN_6"` but the 100-pin package only exposes FLEXCAN_0
   through FLEXCAN_3.
   -> **Fix**: check the legal values in
   `resource_tables/<Driver>.xml`. Pick a value that exists on this package.

The error message itself rarely says *which* setting is the problem. The
fastest diagnostic is to comment out drivers one at a time (or use
`peripherals.remove`) and re-validate to isolate the offending instance,
then grep that instance for cross-refs and out-of-range enums.

---

## "Name must be a valid C identifier"

The literal `Name=""` was emitted somewhere. Common causes:

- A top-level container (most often `CommonPublishedInformation`) is missing
  entirely and the validator auto-created it with empty Name.
- A struct was emitted with `<setting name="Name" value=""/>`.

**Fix**:

- Run `scripts/find_bad_names.py` (lifted from the
  `s32ct-peripherals-author-mex` skill  --  same tool applies). It enumerates every
  `Name` setting whose value isn't a valid C identifier.
- If the result is empty, the missing container is the cause. Run
  `scripts/compare_children.py` between your instance and the matching
  example to find what's missing  --  90 % of the time the missing element is
  `CommonPublishedInformation`.

---

## "destination node referenced must be within {Driver}"

A cross-reference path that syntactically resolves but the validator rejects.
Two specific causes:

1. **Target name doesn't exist** in the destination driver's body. Grep for it.
2. **Two siblings share the same name**, and the ref is ambiguous. Most
   commonly: two `CanController_<i>.CanControllerBaudrateConfig` children both
   named `CanControllerBaudrateConfig_0`. Suffix per parent: rename one to
   `CanControllerBaudrateConfig_1`, fix the ref path.

---

## "Value out of range" / "duplicated"

You've used a non-sequential index (e.g. `CanControllerId=4` when only 2
controllers exist) or two controllers use the same hw-channel selector
(e.g. both `FLEXCAN_0` because you forgot to set the second one).

**Fix**: every `<Driver>ControllerId` / `<Driver>ChannelId` should run 0, 1,
2, ... sequentially. Every hw-channel selector must be unique per driver
instance.

---

## "OPWFMB mode is not available for selected channel!"

Pwm-specific. The eMIOS channel you picked doesn't support OPWFMB.

**Fix**: either change the channel (CH_0 through CH_7 on eMIOS_0 tend to be
safest), or change the mode. The bitmask of legal modes per channel is in
`RTD/Pwm.xml` arrays `EmiosPwmModesMappingInst_0` (eMIOS_0) and
`EmiosPwmModesMappingInst_1` (eMIOS_1).

## "period <N> ticks > max 65534"

Pwm `PwmPeriodDefault` overflows uint16.

**Fix**: set `PwmPeriodInTicks=true` and pick a value <= 65534.

## "Counter bus in internal counter mode can be used only for OPWFMB mode and OPWFM mode"

Pwm channel uses `EMIOS_PWM_IP_BUS_INTERNAL` with a non-OPWFMB mode.

**Fix**: switch `EmiosChMode` to `EMIOS_PWM_IP_MODE_OPWFMB`, or switch
`EmiosChCounterBus` to `BUS_A`/`BUS_F`/etc. (which then requires Mcl
`EmiosCommon` masterbus  --  usually more work).

## "Invalid value of channel reference. Please ... configure a channel first ... in the EmiosCommon tab in MCL driver."

Pwm channel references an Mcl `EmiosCommon` master bus that doesn't exist.

**Fix**: simplest  --  switch `EmiosChCounterBus` to `EMIOS_PWM_IP_BUS_INTERNAL`
(and the mode to `OPWFMB` per above). Alternative  --  add an Mcl instance with
the required `EmiosCommon_<i>/EmiosMclMasterBus_<j>`, using
`s32ct-peripherals-author-mex` or grafting from an Mcl example.

---

## "At least one HwFilter Need to be assigned per HW Object"

Can-specific. A `CanHardwareObject` has no `CanHwFilter` child.

**Fix**: add at least one `<struct>` to its `<array name="CanHwFilter">`. The
example block usually has these; check they survived the splice.

## "Out of baudrate configuration for current controller"

Can-specific. A `CanController` has no `CanControllerBaudrateConfig` child.

**Fix**: add at least one. The grafted example contains one by default.

## "Hardware Channel must be unique across all CAN controllers"

Multiple `CanController` entries default to the same `CanHwChannel`.

**Fix**: set `CanHwChannel` explicitly on each, with distinct values.

---

## "Duplicated UartHwChannel" / "LPUART HW channel is being used by UART driver"

Either:

- `UartHwChannel` was set on the wrong element (must be **inside**
  `DetailModuleConfiguration`, not on `UartChannel` directly), or
- The same `LPUART_<N>` is claimed by both your `Uart` instance and your
  `Lin_43_LPUART_FLEXIO` instance. Each LPUART can be owned by exactly one
  driver  --  pick.

---

## "Adc Physical Channel ID must equal number after ChanNum"

ADC channel `AdcChannelName="P1_ChanNum1"` paired with `AdcChannelId="0"`.
The id must match the trailing number of the name.

**Fix**: set both consistently (`AdcChannelName="P1_ChanNum1"` ->
`AdcChannelId=1`).

## "ADC channel must be mapped on the same Hw Unit Group"

ADC `AdcGroupDefinition` ref path points at a channel under a different
HwUnit.

**Fix**: ensure the path's HwUnit segment matches the parent group's HwUnit.

## "Group id must be unique among all Groups in all Hw Units"

`AdcGroupId` is globally unique, not per-HwUnit.

**Fix**: use a running counter (0, 1, 2, ...) across all HwUnits.

---

## Pattern not in this list

If you've matched no pattern and the message is still mysterious:

1. **Read the RTD example for the offending driver.** Diff the example's
   instance block against yours (`scripts/compare_children.py`).
2. **Check the resource table** for the driver  --  your value may not exist on
   this package.
3. **Try `s32ct-peripherals-info`** as a knowledge tool to look up the
   `.component`'s declaration for the offending setting.

When all else fails, fall back to `s32ct-peripherals-author-mex`  --  it has the
per-driver authoring deep-dive that may catch what the lift-and-adapt path
missed.
