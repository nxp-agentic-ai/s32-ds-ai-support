# Error-handling decision tree

This file is the error catalogue referenced from `SKILL.md` of
`s32ct-peripherals-author-mex`. When `-ShowProblems` validation fails,
follow this tree instead of guessing. Every entry traces to a real bug
encountered during the S32K312MINI-EVB hardening session.

```
SEVERE: [TOOL] ... "destination node referenced must be within <Driver>"
  -> look at the offending ref path. Two candidates:
      a) The target name doesn't exist in the .mex anywhere
         -> grep for it and either fix the path or add the target node.
      b) Two siblings have the same name and the ref is ambiguous
         -> suffix names with parent index so each is globally unique.

SEVERE: [TOOL] ... "Name must be a valid C identifier"
  -> run find_bad_names.py first; if it returns 0 hits, the offending
    Name="" is on an auto-created struct that you forgot to emit. Run
    compare_children.py against an RTD example .mex of the same driver
    to spot the missing top-level container. 90% of the time it's
    CommonPublishedInformation.

SEVERE: [TOOL] ... "Value out of range" / "duplicated"
  -> you've used a non-sequential index (e.g. CanControllerId=4 when only
    2 controllers exist) OR two controllers have the same hw-channel
    selector (e.g. both at CanHwChannel default). Make every
    dynamic_enum value unique.

SEVERE: [TOOL] ... "value not available"
  -> an enum value you set isn't a member of the enum's allowed list.
    Open the matching RTD example .mex and grep for the actual value
    string.

SEVERE: [TOOL] ... "period <N> ticks > max <M>"
  -> Pwm tick-count overflow. Set PwmPeriodInTicks=true and use <= 65534.

SEVERE: [TOOL] ... "Adc Physical Channel ID must equal number after ChanNum"
  -> AdcChannelId must match the trailing number of AdcChannelName
    (e.g. AdcChannelId=1 paired with AdcChannelName=P1_ChanNum1).

SEVERE: [TOOL] ... "ADC channel must be mapped on the same Hw Unit Group"
  -> AdcGroupDefinition's ref path points at a channel under a different
    HwUnit. Make sure the path's HwUnit segment matches the parent
    group's HwUnit.

SEVERE: [TOOL] ... "Group id must be unique among all Groups in all Hw Units"
  -> AdcGroupId is GLOBALLY unique, not per-unit. Use a running counter.

SEVERE: [TOOL] ... "Out of baudrate configuration for current controller"
  -> CanController has no CanControllerBaudrateConfig child. Add at least one.

SEVERE: [TOOL] ... "At least one HwFilter Need to be assigned per HW Object"
  -> CanHardwareObject needs at least one CanHwFilter child.

SEVERE: [TOOL] ... "Hardware Channel must be unique across all CAN controllers"
  -> multiple CanControllers default to FLEXCAN_0. Set CanHwChannel
    explicitly on each, with distinct values.

SEVERE: [TOOL] ... "Duplicated UartHwChannel" or "LPUART HW channel is being
                    used by UART driver"
  -> either you set UartHwChannel in the wrong place (must be inside
    DetailModuleConfiguration), or LPUART<N> is claimed by both your
    Uart instance and your Lin instance. Each LPUART can be owned by
    exactly one driver  -  pick.

SEVERE: [Generation error: PwmChannelId ...]
  -> see pitfall #5 in per-driver-reference.md.
```

If a problem doesn't match any of the patterns above, **do not guess**.
Open the matching RTD example `.mex` for the offending driver and read
the canonical XML  -  it will show the missing/misshapen field.


---

## Appendix: framework-noise catalog (drop before interpreting output)

The following SEVERE lines appear on any clean project and are NOT real
problems. Filter them out before interpreting the `-ShowProblems`
output:

- `Cannot get container for IPath ...`
- `[TOOL] No script file found while trying to recompile the codegeneration script for SerDes Config Tool` (only if SERDES is enabled)
- `Error in expression parsing. Missing right bracket ')' ... in expression: (featureDefined(...) && ...)`
- `Problem occurred during invocation of function derefAsr: TypeError: ...`
- `[DATA] [Siul2_Port] Trying to apply item defaults or quick selection on setting with id "...PortPinPcr" that is of type "InfoSetting"`
- `Problem occurred during invocation of function Port_GetNumOfPinConfig: TypeError: null has no such function "getChildren"`
- `Problem occurred during invocation of function getTotalNumOfChans` / `getTotalNumOfGroups`: `TypeError: null has no such function "getChildById"`

After stripping these, any remaining `SEVERE: [TOOL]` or `SEVERE:
[Generation` lines are real and match the decision tree above.
