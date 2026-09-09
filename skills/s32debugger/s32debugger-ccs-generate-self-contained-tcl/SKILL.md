---
name: s32debugger-ccs-generate-self-contained-tcl
description: >
  Generate a self-contained CCS Tcl script for execution by the CCS executable
  (`ccs` on Linux, `ccs.exe` on Windows). Use this
  whenever the user asks for a CCS script to connect to a probe, identify a
  target, get target info, check debug lock state, attach to an already
  initialized SoC, inspect target/core status, do a bring-up-from-reset flow,
  run a minimal CCS sanity check after failed GDB startup, or run a
  family-specific attach/core-status sanity test. Generate the script from the
  confirmed target state: generic discovery, attach-ready, family-specific
  attach/status sanity, needs initialization, or post-GDB-failure isolation,
  while keeping the first readable checkpoint minimal and free of exploratory
  additions.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  tags: '[s32debugger, ccs, generation]'
---

# S32Debugger Generate Self-Contained CCS Tcl

Generate a user-facing CCS Tcl script whose shape matches the confirmed target
state. This skill produces discovery, attach-ready, family-specific sanity,
bring-up, or post-GDB-failure diagnostic Tcl while keeping the result
self-contained, verifiable, and grounded in known CCS syntax and family logic.

## When to use

Use this skill when:
- The user wants a CCS Tcl script for probe connection, target discovery,
  attach, status, or bring-up.
- The user wants a minimal CCS sanity script after a failed GDB flow.
- The user wants a family-specific attach/core-status sanity script without
  immediately mixing in load/run or full bring-up behavior.

Do **not** use this skill for:
- Routing/classifying CCS requests; use `s32debugger-ccs-execution-router`.
- Executing the script and reporting runtime evidence; use
  `s32debugger-ccs-run-tcl-script`.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.

### 2. Confirm the script class from the target state

```
Classes: generic discovery | attach-ready | family-specific sanity |
         needs initialization | post-GDB-failure sanity
Input:   probe IP, family/device, target state, desired action
Output:  one script shape with no hidden assumptions
```

### 3. Build only the required CCS depth

```
L0-L2: fast probe triage -> config cc -> generic s32cc dap -> get_target_info
L3-L4: family-specific chain -> readable core-status sanity
L5:    deeper attach/init or bring-up behavior
```

### 4. Classify the checkpoint output style before generating capture logic

```
Result-returning:       capture with `set x [command]`
Display/print-oriented: preserve checkpoint and capture printed output
Default:                treat `ccs::all_run_mode` as display-oriented
```

### 5. Emit a self-verifying Tcl artifact

```
Include: readable display output, result/log markers, catch around critical ops
Verify:  script proves probe config, chain config, and requested status/result
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.

**Scope**
- Generate CCS Tcl only; do not execute it here.
- Match the output strictly to the confirmed class: generic discovery,
  attach-ready, family-specific attach/core-status sanity, needs
  initialization, or post-GDB-failure isolation.
- Keep the final script user-facing and self-contained.
- For family-specific attach or init behavior, rely on the knowledge DB rather
  than invented syntax, guessed family support, or hidden KB-only paths.
- Keep the first readable checkpoint minimal and on the correct chain.
- Preserve the mandated checkpoint command even when a different capture method
  is needed.

**Destructive actions**
- Default to the smallest script that answers the user's request.
- If the generated workflow will later start the CCS executable (`ccs` /
  `ccs.exe`), make it easy for the
  execution flow to terminate that process unless the user explicitly wants it
  kept open.
- If a telnet `who` shows a `ccs` process on the probe, generate a hard-stop
  behavior rather than retry loops; if no `ccs` process is present, the probe is
  ready.

**Refuse-and-escalate**
- If target state is unclear, ask whether the script is for generic discovery,
  attach-ready control, family-specific attach/status sanity, bring-up from
  reset, or post-GDB-failure isolation.
- If required family init logic cannot be grounded in KB evidence or verified
  local files, stop instead of inventing it.
- If early probe triage is impossible and probe connect later fails, require
  telnet `who` as fallback before deeper diagnosis.
- If a failed GDB flow has not yet proven lower layers, keep the first CCS
  diagnostic script at generic discovery scope unless explicit evidence justifies
  escalation.
- If machine-readable proof is required for a display-oriented command, add a
  narrow output mirror rather than changing the target sequence.

**Resource limits**
- Build only the minimum capability ladder depth required by the request.
- Keep placeholders explicit; do not silently guess chain tokens, core indices,
  or init sequences.

**Do**
- Prefer `s32dbg:<probe-ip>` in new flows.
- Prefer human-readable `display` forms for user-facing query and status output.
- Use `display ccs::all_run_mode` by default for all-core status requests on a
  configured family chain.
- Resolve the DAP variant (`dap` vs `dapv6`) per family before emitting a
  family chain (see `references/authoring-procedure.md` -> "Resolve the DAP
  variant").
- Before emitting any per-core operation (`ccs::stop_core`, `ccs::run_core`,
  `ccs::read_mem`, `ccs::write_mem`, `ccs::read_reg`, `ccs::write_reg`, `ccs::core_run_mode`) resolve the real chain position with
  `display ccs::get_config_chain` (see `references/authoring-procedure.md` ->
  "Resolve the chain position before per-core operations"). The SoC node is
  often at position 0, so the first core can be at position 1; never derive a
  per-core index from the `ccs::all_run_mode` line order.
- Always use the `display ccs::get_config_chain` form, never the bare
  `ccs::get_config_chain`: the bare result-returning form returns numeric core
  type codes (e.g. `357 312 274 ...`), not readable names, so matching a core
  by name against it fails. The `display` form prints each position with its
  human-readable name (e.g. `Chain Position 1: Cortex-M7`).


- Add Tcl-side output capture only when the requested proof command is display-
  oriented and machine-readable evidence is required.


**Do not**
- Add `display ccs::get_config_chain` to the generic `s32cc dap` discovery
  pattern.
- Use `get_target_info` on family-specific chains.
- Replace `display ccs::all_run_mode` with a different query only to simplify
  capture.
- Mix the first post-GDB-failure sanity script with ELF load, run control, or
  full bring-up logic.
- Add help probing, stdin-feed patterns, or exploratory wrappers before the
  first sufficient readable checkpoint.

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm target state and script class are aligned.
2. Verify transport uses `s32dbg:` and the fast path is modeled when a probe IP
   is available: reachability, then a telnet session running `who` (a `ccs`
   process in the output means busy; none means ready), then CCS connection.
3. Verify the capability ladder depth matches the request: generic discovery,
   family-specific sanity, or bring-up.
4. Verify readable evidence is built in: `display` output where appropriate,
   result/log markers, and `catch` around critical steps.
5. Verify no hidden KB-only source path or unverified helper-proc dependency
   remains in the emitted user-facing script.
6. Verify the first readable checkpoint is the smallest sufficient one and is
   bound to the correct chain.
7. If machine-readable capture is required, verify the generated capture method
   matches the checkpoint type: Tcl result for result-returning commands,
   printed-output capture for display-oriented commands.
8. Return assumptions, the generated Tcl, what was inlined vs adapted, and a
   short verification checklist.

## Out of scope

- Executing the Tcl and interpreting runtime evidence.
- Routing between CCS workflows before the target state is classified.
- Treating family-specific core-status sanity as proof of load/run, breakpoint,
  reset policy, or full bring-up behavior.
- Inventing unsupported CCS syntax or family initialization sequences.

## See Also

- `references/authoring-procedure.md` - script classes, capability ladder,
  capture-aware script authoring, and self-contained generation rules.
- `references/examples.md` - trigger examples, anti-patterns, and verification
  cues.
- Related skills: `s32debugger-ccs-execution-router`,
  `s32debugger-ccs-run-tcl-script`, `s32debugger-error-resolution`
