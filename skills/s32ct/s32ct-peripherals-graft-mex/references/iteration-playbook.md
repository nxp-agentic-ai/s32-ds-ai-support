# Iteration playbook

A realistic estimate of how the first run of a multi-driver graft progresses,
distilled from a complete S32K312MINI-EVB session (Spi + Uart + Can + Lin +
Adc + Pwm). Use this to set expectations and to know what to try next when an
iteration doesn't immediately yield zero.

The "iteration N" labels match what you'd see in the validation report. Each
section: what the validator says, what it usually means, what the fix is.

---

## Iteration 1  --  the lift

After step 1-4 of the workflow (inventory, discover, lift, splice **without**
manual edits), validation typically reports **one `SEVERE: [TOOL]` line per
driver**, almost always with the text `The value is not available.`

This is normal and expected. Each instance carries cross-references to a
clock-ref point or to an absent driver. The example was authored against an
MCU/RTD/board with more clock points and probably an Mcl instance  --  your
target template doesn't.

**Fix**: run `scripts/sanitize.py`.

What sanitize does:

1. Redirects every value matching
   `/Mcu/Mcu/McuModuleConfiguration/<segment>/<segment2>` that doesn't already
   end in `McuClockReferencePoint_0` -> redirects to the canonical path
   `/Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/McuClockReferencePoint_0`.

2. Self-closes every `<array name="X">` whose body contains a `/Mcl/` path.
   In a typical session this empties 5-10 arrays: `SpiPhyTxDmaChannel`,
   `SpiFlexioTxAndClkChannelsConfig`, `UartDmaTxChannelRef`, `LinFlexioRxChannelRef`,
   `AdcDmaChannelRef`, etc.

3. Blanks the value of any singleton `<setting>` that points into an absent
   driver (most commonly `UartHwChannelRef` when `UartHwUsing=LPUART_IP`).

Sanitize is **idempotent**, so re-running after subsequent manual edits is
free. Don't try to reason about which array needs which fix  --  just sanitize.

---

## Iteration 2  --  what survives

After sanitize, the count of real problems typically drops by 80-90%. On a
6-driver session, you usually go from 6 -> 0 or 6 -> 1.

If you're at 0, validate Pins for regression and you're done.

If you're at 1, the survivor is almost certainly Pwm-specific. The Pwm
example may have:

- Set `EmiosChCounterBus` to a non-INTERNAL bus (BUS_A, BUS_F, etc.),
  which needs an Mcl `EmiosCommon` masterbus you don't have.
- Set `EmiosChMode` to a mode that's incompatible with INTERNAL bus.
- Used a channel that doesn't support the mode you picked.

The fix-set is:

1. Sweep all `EmiosChCounterBus` values to `EMIOS_PWM_IP_BUS_INTERNAL`.
2. Sweep all `EmiosChMode` values to `EMIOS_PWM_IP_MODE_OPWFMB`.
3. If the validator still complains about mode-not-supported-for-channel,
   drop unused channels: remove the entire `PwmEmios_<i>` struct *and* the
   matching `PwmChannel_<j>` entry, renumber the survivor to index 0.

This is the only driver that reliably needs per-channel inspection on top
of the systematic sanitize pass  --  because eMIOS channel/mode/bus is a 3D
compatibility matrix that can't be solved by global rewrite.

---

## Iteration 3  --  if you're still not at zero

If real problems remain after sanitize + Pwm fixes, the cause is almost
always one of:

1. **A driver-specific gotcha you missed during the lift.** Read the matching
   section of `per-driver-gotchas.md`. Examples:
   - Forgot to rename `CanControllerBaudrateConfig_0` per controller ->
     "destination node must be within driver".
   - Pasted `UartHwChannel` outside `DetailModuleConfiguration` ->
     "Duplicated UartHwChannel".
   - Adc channel id doesn't match the trailing number of the channel name.

2. **An ownership conflict between two drivers.** The most common case:
   `Uart` and `Lin_43_LPUART_FLEXIO` both claim the same `LPUART_<N>`. Each
   LPUART can be owned by exactly one driver  --  pick.

3. **A package-specific enum value that doesn't exist on the target.**
   Cross-check the resource table.

Match the message against `error-decision-tree.md`.

---

## Iteration 4-6  --  diagnostic strategies if you're stuck

If you've done two rounds of sanitize + targeted fix and the validator is
*still* showing the same line:

> **Warning - the steps below modify the `.mex` in place and are not
> reversible.** Instance deletion, sanitize sweeps and global `EmiosCh*`
> rewrites all overwrite the project file with no backup. Commit the
> `.mex` to version control (or copy it aside) *before* you start
> iterating, so every experiment below can be rolled back.

- **Isolate by removing drivers.** Comment out / delete one instance at a
  time and re-validate. The first removal that drops the error tells you
  which driver instance is the cause. (Save the full file before doing this
  so you can compose the fix back.)

- **Diff against the RTD example.** For the offending driver, run
  `scripts/compare_children.py` between your instance block and the example
  block. Look for missing top-level structs and missing settings.

- **Read the matching `.component` schema.** Use `s32ct-peripherals-info`
  to look up the exact declaration of the offending setting. The `<dynamic_enum
  ref="...">` will tell you which resource table to consult for legal values.

- **Switch to `s32ct-peripherals-author-mex`** for the offending driver only. The
  lift-and-adapt approach can be combined with from-scratch authoring on a
  per-driver basis  --  most drivers stay grafted, one driver gets authored
  freshly.

---

## When to stop iterating

Set a budget (the `iterate` input parameter defaults to 6) and stop if:

- **Validation passes**  --  the filtered problem count is 0. Validate Pins for
  regression and report success.
- **The same error survives 2 consecutive iterations**  --  sanitize has nothing
  more to do; further iteration without a different strategy won't help.
  Report the surviving error verbatim and hand off to the user. Don't try
  to bash the same fix in a third time; it won't work.
- **You've reached the budget.** Report the surviving errors and the smallest
  set of drivers you couldn't make pass. The user can iterate further with
  manual edits or switch to `s32ct-peripherals-author-mex`.

A successful first run on a 6-driver mix typically takes:

- **3 iterations**: lift -> sanitize -> Pwm-fix -> done (most common).
- **4-5 iterations**: lift -> sanitize -> Pwm -> driver-specific gotcha -> done
  (when the user's driver mix is unusual).
- **6+ iterations**: handoff candidate. Either the driver mix doesn't have
  good RTD examples, or there's an MCU-specific quirk this skill doesn't
  encode yet.

After a successful first run, a second run on the same MCU/package with a
new driver added typically converges in 1-2 iterations because the
sanitize pass is unchanged.
