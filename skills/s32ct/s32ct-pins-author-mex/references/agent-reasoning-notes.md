# Notes for Agent Reasoning  -  s32ct-pins-author-mex

This file is referenced from `SKILL.md`. It captures the long-form
rationale, conventions, and lessons that an agent invoking this skill
should internalise. Load it whenever you are about to author or extend
a Pins-tool `.mex` and need the canonical case/channel/conflict rules,
or when something in the main workflow seems ambiguous.

## Notes for Agent Reasoning
- **See also: `s32ct-distributions`** -- canonical reference for the
  two S32CT distributions (`desktop` with `toolsc.exe`/`tools.ini`,
  `integrated_s32ds` with `s32dsc.exe`/`s32ds.ini`) and where the MCP
  auto-discovers them at startup.

- **Always quote `signal_configuration.xml` rather than invent routings.**
  The Pins tool's `-ShowProblems` validator will reject any `(peripheral,
  signal, pin)` triple not present in the XML, and the package/RTD shipped
  with the install is the only authoritative source.
- **Case matters.** `peripheral=` is camel/upper case as in the XML
  (`LPSPI0`, `LPUART2`, `CAN0`, `eMIOS_0`, `SIUL2`). `signal=` is **lower
  case** (`lpspi0_sout`, `adc0_p1`, `gpio`). `pin_signal=` is upper case
  (`PTA0`, `PTB10`). `pin_num` is the numeric `coords` of the `<pin>`  - 
  *not* the alt-function index.
- **Channel rule.** If the XML `<peripheral_signal_ref>` element has a
  `channel="N"` attribute, the `.mex` `signal=` must be
  `"<base>, <N>"` (with `", "` separator); otherwise no comma. Examples:
  `signal="gpio, 0"` (SIUL2 GPIO 0), `signal="adc0_p1"` (channel baked
  into signal name, no comma), `signal="emios_0_ch_4_g"` (channel + group
  baked, no comma).
- **Conflict avoidance > pin-prettiness.** The skill must produce a
  conflict-free `.mex`; matching the on-board wiring is only secondary
  (controlled by `prefer_onboard`). When the two conflict, the agent
  records the rejected candidate in the *Conflict report* and continues.
- **Greedy order is fixed.** `ADC -> CAN -> LPSPI -> LPUART -> PWM`. Do not
  reorder it to optimise for a specific routing; it works for *all*
  supported MCUs because it sorts by intrinsic pin flexibility.
- **`-ShowProblems` is mandatory.** Skipping validation, or trusting
  `exit_code` alone, has masked silent failures (25 errors in a real
  session). Always follow the four-step `.bat`-wrapper / stderr-capture
  / framework-noise-filter recipe in Step 5.
- **The bundled reference templates** typically bake in the **Pins**,
  **Clocks** and **Peripherals** tools as enabled at specific RTD
  versions (e.g. Pins v17.0, Clocks v19.0, Peripherals v15.0 for S32K3).
  This skill intentionally leaves the Clocks and Peripherals sections
  untouched  -  call `s32ct-peripherals-author-mex` / `s32ct-clocks-info`
  afterwards if those tools also need configuring.
- **Hand-off chain** for a complete from-scratch driver bring-up:
  1. `s32ct-pins-author-mex` (this skill)  -  produce the Pins-populated `.mex`.
  2. **`s32ct-peripherals-author-mex`**  -  author the Peripherals-tool `<instance>`
     blocks with per-controller configuration (SpiPhyUnit, UartChannel,
     CanController + CanHardwareObject, LinChannel, AdcHwUnit + AdcChannel
     + AdcGroup, PwmEmios / PwmFlexPwm depending on the platform).
     Includes the same `-ShowProblems` validation gate that correctly
     inspects stderr.
  3. `s32ct-clocks-info` + `s32ct-clocks-facade`  -  fine-tune clock tree;
     adds `McuClockReferencePoint_*` entries that LinClockRef /
     CanCpuClockRef in step 2 will need.
  4. `s32ct-generate-code` (`ExportAll`)  -  emit all driver C/H sources.
  5. Compile + flash + (optionally) connect via FreeMASTER.
- **Performance note.** `signal_configuration.xml` is multiple MB on
  larger packages (~2.4 MB on S32K312_172HDQFP, larger on S32G/S32S
  parts). Load it **once** at the start of the run via
  `s32ct-pins-info`; do not re-parse it per candidate.
- **Extending the skill is template-only.** Adding support for additional
  MCUs/RTDs/packages requires only that a matching reference `.mex` be
  added to the `s32ct-generate-mex-config` skill (see *Extending to a new
  MCU/RTD/package*). This skill's contract  -  inputs, behavior, output  - 
  does not otherwise change.

