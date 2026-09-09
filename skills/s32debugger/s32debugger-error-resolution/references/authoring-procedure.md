# Authoring Procedure

## Failure-layer model

Classify by the shallowest unproven layer:
- Layer 0: probe reachability and occupancy
- Layer 1: CCS generic discovery / generic DAP visibility
- Layer 2: family-specific attach/core-status sanity readiness
- Layer 3: family-specific attach or initialization readiness beyond simple
  status collection
- Layer 4: GDB bridge/session startup and attach orchestration
- Layer 5: ELF, symbol, load, reset, breakpoint, and run-control behavior

Do not spend time on higher layers when a lower layer is still unproven.

## CCS-first observational rule

If the request is observational only, and no interactive session is already
active, begin with Layers 0-2 through CCS before any GDB live-session path.
Treat this as the primary path rather than a fallback.

## First-pass categories

- pre-launch/config problem
- GTA/local debugger service problem
- CCS/probe connection problem
- interactive bridge problem
- target execution state problem
- symbol/ELF problem
- lower-layer ambiguity after failed GDB flow
- output-capture-path mismatch

## Fallback rule

If a GDB connect/attach/startup failure is ambiguous and lower layers are not
proven, prefer:
1. probe reachability check
2. telnet `who`
3. minimal CCS generic discovery
4. family-specific attach/core-status sanity only if generic discovery already
   succeeded and the next question is chain readiness

## Additional failure pattern: capture-path mismatch

A CCS command may succeed and display text in the CCS console, yet still appear
empty to automation if the agent uses the wrong capture method.

Typical signals:
- the command is visible to a human in CCS
- `set x [command]` is empty
- redirected stdout/stderr from the CCS executable's `-script` run are empty

Interpretation:
- lower CCS layers may already be proven
- the missing layer is output collection, not probe reachability or family support

Required recovery order:
1. prove the command executed
2. inspect whether the command is result-returning or display-oriented
3. switch to Tcl-side capture for display-oriented commands
4. only then revisit target-state or family-init hypotheses

## Blocking vs non-blocking

### Blocking
- connect failure
- startup failure
- bridge failure
- missing symbol file when symbolic validation is required

### Often non-blocking
- source lookup warning after a correct symbolic stop at the intended
  breakpoint
- empty command-substitution result for a display-oriented CCS command, until
  the display-output capture path has also been tested

## Standard recovery sequence

1. stop the current debugger session cleanly
2. confirm target core and GDB variant
3. rediscover or confirm the intended template
4. regenerate the config with `generate.gdb_config_file` (REST bridge embedded)
5. start GDB with `control.start_gdb` (launches GTA automatically)
6. validate bridge if interactive
7. if lower layers remain unproven, use probe triage and CCS generic discovery
8. if visible CCS output is central to the complaint, validate the capture
   path before changing target assumptions
9. validate breakpoint or stop-state
