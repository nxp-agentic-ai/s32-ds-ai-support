# Examples and Checks

## Typical triggers

- create a CCS script to identify the target
- make a self-contained Tcl to attach to my SoC
- generate a family-specific CCS sanity script
- GDB failed; give me a minimal CCS sanity-check script
- make a bring-up-from-reset CCS Tcl script

## Common verification cues

- probe IP is correct
- `s32dbg:` is used
- if a probe IP exists, the script models reachability plus opening a telnet
  session and issuing `who`, and hard-stops only when the `who` output lists a
  `ccs` process (no `ccs` process means the probe is ready)
- generic discovery uses `display ccs::get_target_info`
- family-specific chains do not call `get_target_info`
- the family chain uses the DAP variant resolved for that family (`dap` vs
  `dapv6`), not the `dap` token carried over from generic discovery
- all-core status uses `display ccs::all_run_mode` by default
- any per-core operation is preceded by `display ccs::get_config_chain`, and the
  core index is taken from the resolved chain position (not from the
  `ccs::all_run_mode` line order)


- critical steps emit readable evidence or explicit result markers
- no hidden KB-only paths remain
- the first readable checkpoint is the smallest sufficient one
- no exploratory wrappers are inserted before that checkpoint
- machine-readable capture, when required, matches the checkpoint type:
  Tcl result for result-returning commands, printed-output capture for
  display-oriented commands

## Minimal correct examples

### Discovery script

```tcl
config cc s32dbg:10.17.102.37
ccs::config_init_action 1 2 0 0 0 0
ccs::config_chain {s32cc dap}
display ccs::get_target_info
quit
```

### Family-status script

S32N is an RTU-based / DAP-v6 family, so the chain uses `dapv6`. Always resolve
the variant for the actual family before emitting this (see
`authoring-procedure.md` -> "Resolve the DAP variant").

```tcl
config cc s32dbg:10.17.102.37
ccs::config_init_action 1 2 0 0 0 0
ccs::config_chain {s32n7 dapv6}
display ccs::all_run_mode
quit
```

A classic (DAP) family such as S32G3 would instead use `{s32g3 dap}`.


## Anti-patterns

- emitting attach-only Tcl for a cold target
- emitting full bring-up Tcl when attach-ready was requested
- generating a family-specific attach script as the first response to an
  ambiguous GDB failure
- inheriting the generic `s32cc dap` token onto a family chain instead of
  resolving the family's DAP variant (using `dap` on a `dapv6` part such as
  S32N causes a chain "Bus error")
- addressing a core by index for any per-core op without first resolving its
  position via `display ccs::get_config_chain`; the SoC/subcore nodes shift core
  positions on every part, and `ccs::all_run_mode` line order is not the chain
  position (getting this wrong yields `Unimplemented` / `Invalid parameter`)
- using silent query commands when readable `display` output is available


- pretending a placeholder-heavy script is production-ready
- replacing `display ccs::all_run_mode` with a different command solely to make capture easier
- assuming every CCS proof command returns its visible text as a Tcl result
- adding wrappers, mixed phases, or lower-level substitutions before the
  mandated readable checkpoint
