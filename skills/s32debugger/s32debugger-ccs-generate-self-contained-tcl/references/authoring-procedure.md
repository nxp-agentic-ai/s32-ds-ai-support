# Authoring Procedure

## Script classes

Choose exactly one:
- generic discovery
- attach-ready
- family-specific attach/core-status sanity
- needs initialization
- post-GDB-failure sanity

## Capability ladder

### Level 0
- probe reachability
- open a telnet session to the probe and issue `who` inside it
- if the `who` output lists a `ccs` process, the probe is busy: stop
- if no `ccs` process appears in the `who` output, the probe is ready: continue

### Level 1
- `config cc s32dbg:<probe-ip>`

### Level 2
- set init action
- `ccs::config_chain {s32cc dap}`
- `display ccs::get_target_info`

### Level 3
- resolve the DAP variant first (see "Resolve the DAP variant"), then
  `ccs::config_chain {<family> <dap-variant>}`
- no `get_target_info` on the family chain
- do NOT inherit the `dap` token from the Level 2 generic chain; the generic
  `s32cc` chain always uses `dap`, but the family chain may require `dapv6`


### Level 4
- `display ccs::all_run_mode` for all-core status
- `display ccs::core_run_mode <core>` only for one-core requests
- keep the scope at status/inspection sanity

### Level 4.5 (required before any per-core operation)
- `display ccs::get_config_chain` to resolve the real chain position of every
  core/subcore before addressing one by index (see "Resolve the chain position
  before per-core operations")

### Level 5
- deeper family-specific attach/init or bring-up behavior (per-core
  `stop_core` / `run_core` / `read_mem` / `write_mem` / `read_reg` /
  `write_reg`), which requires the chain positions resolved at Level 4.5



Stop at the lowest level that answers the request.

## Mandatory minimal-path rule

Generate only the smallest script needed to reach the first sufficient readable
checkpoint.

### Discovery script core

```tcl
config cc s32dbg:<probe-ip>
ccs::config_init_action 1 2 0 0 0 0
ccs::config_chain {s32cc dap}
display ccs::get_target_info
quit
```

### Family-status script core

The `<dap-variant>` is `dap` or `dapv6` and MUST be resolved per family (see
"Resolve the DAP variant" below). Do not default it to `dap`.

```tcl
config cc s32dbg:<probe-ip>
ccs::config_init_action 1 2 0 0 0 0
ccs::config_chain {<family> <dap-variant>}
display ccs::all_run_mode
quit
```

## Resolve the DAP variant

The family chain (Level 3+) needs the correct DAP variant token. The generic
`s32cc` chain always uses `dap`, but this MUST NOT be inherited onto the family
chain: RTU-based / DAP-v6 SoCs require `dapv6`, and using `dap` on them produces
a "Bus error" while building the debug chain.

Resolution order (stop at the first that yields an answer):
1. Read the target family's init-script header in the KB
   (`knowledge/s32debugger/tcl_scripts/<family>_init*.tcl`, chunk_index 0). The
   header comment block states the exact chain, e.g.
   `ccs::config_chain { s32s250 dapv6 }` or `ccs::config_chain {s32g3 dap}`.
   Use that variant verbatim.
2. If no header is available, apply the family heuristic below.
3. If still ambiguous, surface the uncertainty rather than guessing.

Family heuristic (evidence-backed; verify against the header when possible):
- `dapv6`: RTU-based / newer families - S32N (s32nz / S32N5x), S32S (S32S250),
  and other SoCs whose init scripts use large APSEL addresses (e.g. `0x5BFE8`,
  `0x5BE94`, `0x1C20`).
- `dap`: classic families - S32G / S32G3, S32R (S32R41 / S32R47), S32K, SAF86xx,
  and other SoCs whose init scripts use small AP indices (e.g. `0`, `2`, `0xC`).

Quick tell: if the family init sequence selects APs with 4-5 hex-digit
addresses, it is a DAP-v6 part and the chain token is `dapv6`.

## Resolve the chain position before per-core operations

Any per-core operation - `ccs::stop_core`, `ccs::run_core`, `ccs::read_mem`,
`ccs::write_mem`, `ccs::read_reg`, `ccs::write_reg`, `ccs::config_template`,
`ccs::core_run_mode` - takes a chain position, NOT a core-enumeration index.
Before emitting any of them, resolve the real positions with:

```tcl
display ccs::get_config_chain
```

Always use the `display ccs::get_config_chain` form, never the bare
`ccs::get_config_chain`. The bare result-returning form returns NUMERIC core
type codes (e.g. `357 312 274 312 274 335 232`), so any attempt to match a core
by its human-readable name against that output fails silently. The `display`
form prints each node with its position AND its readable name (e.g.
`Chain Position 1: Cortex-M7`), which is what the per-core binding requires.

This prints every node on the chain with its position, including SoC / subsystem
/ subcore nodes that are NOT debuggable cores. Use that output to bind each
per-core call to the correct position.


Critical pitfalls this avoids:
- The chain can include non-core nodes (SoC / subsystem / subcore), so the first
  debuggable core is not necessarily at position 0. For example, on S32N5 /
  s32nz the SoC node is at position 0 and the FSS M7 is at position 1.
- `ccs::all_run_mode` lists ONLY cores, so its printed line order does NOT equal
  the chain position once any non-core node is present. Never derive a per-core
  index from the `all_run_mode` line number.
- Symptom of getting this wrong: per-core calls aimed at a non-core node fail
  with `Unimplemented` or `Invalid parameter`, even though the same command is
  valid on a real core. These errors mean "wrong chain position", not "command
  unsupported by connectionless CCS". Every CCS command is supported under
  `-script`.


Resolution order:
1. Emit `display ccs::get_config_chain` and map names to positions.
2. Cross-check against the family init script (e.g.
   `knowledge/s32debugger/tcl_scripts/<family>.tcl` / `<family>_init.tcl`),
   which encodes the expected position layout (M7 cores first, then subsystem /
   RTU cores at computed offsets).
3. Only then address cores by their resolved positions.

## Capture-aware script authoring


When the requested proof command is display-oriented:
1. keep the mandated command in place
2. avoid replacing it with a non-equivalent helper query
3. if machine capture is needed, add a minimal local `puts` mirror wrapper
4. keep the wrapper narrower than the target command sequence itself

Example use case:
- family status still uses `display ccs::all_run_mode`
- capture support is added around Tcl `puts`, not by changing the checkpoint

## Generation rules

1. Search KB material for CCS syntax, family support, and init examples.
2. Keep the final Tcl self-contained.
3. Source only verified local files; never rely on hidden KB-only paths.
4. Prefer readable `display` output for user-facing query/status steps.
5. Add result/log markers and `catch` around critical operations when they do
   not obscure the first sufficient readable checkpoint.
6. If the requested proof command is result-returning, capture through Tcl
   result assignment.
7. If the requested proof command is display-oriented, preserve it and capture
   the printed output rather than changing the command.
8. Surface uncertainty explicitly instead of guessing.
9. Do not add CLI archaeology, launcher probing, stdin piping, extra logging,
   or lower-level probing before the mandated checkpoint.

## Class guidance

### Generic discovery
- use `s32cc dap`
- prefer `display ccs::get_target_info`
- do not add `display ccs::get_config_chain` here (it is a status-only class;
  `get_config_chain` is instead required at Level 4.5 before per-core operations
  in bring-up / needs-initialization scripts)


### Attach-ready
- avoid bring-up logic
- use family-specific chain only when justified
- prefer readable status output

### Family-specific sanity
- use known family chain
- resolve the DAP variant per "Resolve the DAP variant" before emitting the
  chain; never inherit `dap` from the generic discovery step
- prefer `display ccs::all_run_mode`

- do not mix in load/run or full bring-up by default
- treat `ccs::all_run_mode` as display-oriented unless grounded local evidence
  proves it returns the displayed text directly

### Needs initialization
- inline grounded init logic or source a verified local file
- stop if required init behavior cannot be emitted safely

### Post-GDB-failure sanity
- default to the narrowest script: fast probe triage plus generic discovery
- escalate only after generic visibility is proven or explicitly requested
