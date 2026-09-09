# Routing Procedure

## Core rule

Route first, generate or execute second.
The route is procedural and mandatory.

## CCS-first observational rule

If the request is only for probe sanity, target information, or core states,
and no interactive debug session is already active, CCS is the first-choice
workflow, not a fallback after GDB.

## Classification model

Choose one execution goal:
- generate Tcl only
- run existing Tcl
- generate and run Tcl
- inspect why a CCS Tcl flow failed
- diagnose a failed GDB flow using CCS sanity checks
- validate a family-specific attach/core-status sanity flow

Choose one target state:
- generic discovery
- attach-ready
- needs initialization
- post-GDB-failure diagnostic isolation
- family-specific attach/core-status sanity validation

Choose one capture mode when later execution evidence matters:
- result-capture mode
- display-capture mode

## Fast probe triage

The probe-availability check is: open a telnet session to the probe, then issue
the `who` command inside that telnet session and inspect its output.
- If the `who` output lists a `ccs` process, the probe is already owned by
  another CCS client and is NOT available: stop.
- If the `who` output contains no `ccs` process, the probe is free and ready for
  a connection: continue.

When a probe IP is available:
1. check reachability
2. open a telnet session to `<probe-ip>` and issue `who` inside it
3. if the `who` output shows a `ccs` process, the probe is busy: stop
4. otherwise (no `ccs` process in the output) the probe is ready: continue to
   CCS routing/execution

If early triage was impossible and CCS connect later fails, open telnet and run
`who` as the fallback busy discriminator before going deeper.
The presence of the telnet client itself in `who` output is not a `ccs` process
and is not proof of occupancy; only a `ccs` process means the probe is busy.

## Capability ladder

1. Probe configured
   - `config cc s32dbg:<probe-ip>`
2. Generic chain configured
   - set init action
   - `ccs::config_chain {s32cc dap}`
   - `display ccs::get_target_info`
3. Family-specific chain configured
   - `ccs::config_chain {<family> dap}`
4. Family-specific attach/status completed
   - prefer `display ccs::all_run_mode`
   - use `display ccs::core_run_mode <core>` only for one-core requests

Do not request deeper actions than the current proven layer supports.

## Output semantics rule

For observational requests, do not assume every mandated checkpoint has the
same capture behavior.

- `display ccs::get_target_info` may be paired with result capture if the local
  implementation returns a Tcl value
- `display ccs::all_run_mode` should be assumed display-oriented until proven otherwise

If capture semantics affect downstream execution, preserve the checkpoint but
choose a capture-aware execution path.

## Mandatory checkpoint rule

For quick sanity, identification, or all-core status requests, the router must
select the first readable sufficient checkpoint and stop there.

Mandatory readable checkpoints:
- generic discovery: `display ccs::get_target_info` after `ccs::config_chain {s32cc dap}`
- family all-core status: `display ccs::all_run_mode` after `ccs::config_chain {<family> dap}`

These bindings are mandatory. Do not move a checkpoint onto a different chain.

## Forbidden substitution and mixing rule

Do not replace the mandated readable checkpoint with:
- `ccs::core_run_mode`
- per-core loops
- `ccs::get_config_chain`
- raw chain parsing
- custom Tcl parsing

Do not mix the generic discovery checkpoint and the family all-core checkpoint
into one unlabeled script or one unlabeled report.
Do not run `display ccs::get_target_info` under a family chain.
Do not run `display ccs::all_run_mode` under `s32cc dap`.

Exception: only after explicit escalation conditions are met.

## Route expectations by state

When a state includes ordered operational steps, preserve that order. Do not
collapse an execution sequence into unordered bullets when later generation or
execution depends on command order.

### Generic discovery sequence

1. Check probe reachability.
2. Open a telnet session to `<probe-ip>` and issue `who` inside it.
3. If the `who` output shows a `ccs` process, report the probe as busy and stop
   immediately; if no `ccs` process is listed, the probe is ready, so continue.
4. Run `config cc s32dbg:<probe-ip>`.
5. If the grounded flow supports it, apply optional `ccs::config_server ...`.
6. Set an init sequence before chain creation; the minimum fallback is
   `ccs::config_init_action 1 2 0 0 0 0`.
7. Run `ccs::config_chain {s32cc dap}`.
8. Run `display ccs::get_target_info`.
9. Do not call `display ccs::get_config_chain` for the generic chain unless a
   grounded flow explicitly requires it.

### Attach-ready sequence

1. Confirm the request is really attach-ready and does not require bring-up
   from reset.
2. Choose a minimal attach/status Tcl path.
3. Avoid bring-up logic.
4. Keep output scoped to attach/status behavior.
5. Do not use `get_target_info` on family-specific chains.

### Needs initialization sequence

1. Confirm the target is not safely handled by an attach-ready path.
2. Require KB-backed init logic before selecting the bring-up path.
3. Keep the Tcl self-contained or source only verified local files.
4. Stop if the required init behavior cannot be grounded.

### Post-GDB-failure isolation sequence

1. Start with fast probe triage.
2. Run generic discovery before deeper family-specific attach/init logic.
3. Escalate only when generic visibility is already proven or the user asks.

### Family-specific attach/core-status sanity sequence

1. Require a known family chain.
2. Decide whether the request is all-core status or one-core status.
3. Prefer readable status output.
4. Keep the scope narrower than full bring-up or load/run validation.
5. Classify the mandated checkpoint as result-capture or display-capture when
   later machine-readable evidence is required.

## Escalation conditions

Escalation is permitted only when:
- the mandated display command failed
- the output was ambiguous
- the user explicitly requested deeper analysis
- the display command is unavailable in the proven environment

The reason must be stated explicitly.

## Mandatory family-status path

If the request is family-specific all-core status:
1. complete or report generic discovery first when identification is still unproven
2. configure the family chain
3. run `display ccs::all_run_mode`
4. report that output directly
5. stop

## Final audit

Before answering:
- confirm the mandated checkpoint was selected
- confirm the checkpoint was used with the correct chain
- confirm no forbidden substitution or forbidden mixing was used
- confirm the route stops at the first sufficient readable result
- confirm the capture mode is identified when it affects downstream execution
