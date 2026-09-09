# Execution Procedure

## Resolve paths first

1. Use an explicit CCS executable path if the user provided one
   (`ccs` on Linux, `ccs.exe` on Windows).
2. Otherwise derive it from the S32Debugger installation root:
   `<installation_path>/S32Debugger/Debugger/Server/CCS/bin/ccs.exe` (Windows)
   or `<installation_path>/S32Debugger/Debugger/Server/CCS/bin/ccs` (Linux).
3. Verify the Tcl script exists.
4. Verify the output/log destination is writable.
5. Stop immediately if any required path is missing.

## Fast probe triage sequence

The probe-availability check is: open a telnet session to the probe, then issue
the `who` command inside that telnet session and inspect its output. A `ccs`
process in the `who` output means another CCS client already owns the probe (not
available); no `ccs` process means the probe is ready for a connection.

When a probe IP is available, preserve this order:
1. Check reachability.
2. Open a telnet session to the probe and issue `who` inside it.
3. If the `who` output shows a `ccs` process, the probe is busy: stop
   immediately.
4. If no `ccs` process is present, the probe is ready: launch CCS.

If early triage was impossible and a later probe connect fails, open telnet and
run `who` as a fallback before diagnosing anything deeper. The telnet client's
own entry in `who` is not a `ccs` process and does not indicate occupancy.

## Required launcher form

Use only the CCS executable with `-script`:
`ccs.exe -script <script.tcl>` (Windows) or `ccs -script <script.tcl>` (Linux)

## Launch and proof sequence

### Headless proof sequence

Use this as the default evidence path for automated proof, GDB-failure
comparison, and family-specific sanity.

1. Launch the CCS executable with `-script <script.tcl>`
   (`ccs.exe` on Windows, `ccs` on Linux).
2. Verify the process actually starts.
3. Verify the Tcl script is accepted and begins execution.
4. Capture the first meaningful proof checkpoint reached by the script.
5. If this workflow started the CCS process, terminate it at request completion
   unless the user explicitly asked to keep CCS open.

### Visible mode sequence

Use only when the user explicitly wants the UI.

1. Launch visible CCS.
2. Verify the UI/process started.
3. Verify the script was actually run, not merely that the UI opened.
4. Treat UI launch alone as insufficient proof.

### Alternate port sequence

1. Use `-port` only when there is a real conflict or a concrete isolation need.
2. Record why the alternate port was required.
3. Do not add `-port` without a reason.

## Mandatory checkpoint discipline

### Discovery checkpoint

Use only:
1. `config cc s32dbg:<probe-ip>`
2. `ccs::config_init_action 1 2 0 0 0 0`
3. `ccs::config_chain {s32cc dap}`
4. `display ccs::get_target_info`
5. stop if sufficient

### Family-status checkpoint

Only after family identification, use a separate script:
1. `config cc s32dbg:<probe-ip>`
2. `ccs::config_init_action 1 2 0 0 0 0`
3. `ccs::config_chain {<family> dap}`
4. `display ccs::all_run_mode`
5. stop

## Output capture procedure

Before interpreting missing text as a target failure, classify the checkpoint
command.

### Result-returning checkpoint

- Capture with `set x [command]`.
- Write the value to a proof file if needed.
- Example pattern: `set ti [ccs::get_target_info]`.

### Display-oriented checkpoint

- Treat `display ...` commands as print-oriented by default.
- Treat `ccs::all_run_mode` as print-oriented by default.
- Do not assume redirected stdout/stderr from the CCS executable's `-script` run will contain
  the visible text.
- Do not assume command substitution will return the visible text.
- Use Tcl-side `puts` interception when machine-readable evidence is required.

### Failure pattern: visible in CCS, empty in capture

If the user confirms that a command displays text in CCS, but:
- `set x [command]` is empty, and
- redirected stdout/stderr are empty,

then the shallowest failing layer is the **capture path**, not the target.

Required next proof step:
1. confirm the command executed
2. confirm whether the command returns a Tcl result
3. if not, capture the printed output inside Tcl
4. only then revisit target, family-chain, or init hypotheses

### Standard Tcl-side capture pattern

For display-oriented proof commands, prefer a local wrapper that mirrors Tcl
`puts` output to a file while preserving the original command sequence.

Example pattern:
```tcl
rename puts __orig_puts
set fp [open "capture.txt" w]
proc puts {args} {
    global fp
    uplevel 1 __orig_puts $args
    # normalize args and mirror printed text to $fp
}
```

This wrapper is preferred over replacing the mandated checkpoint with a
non-equivalent query.

## Ordered proof ladder

Report the deepest proven layer without collapsing later layers into earlier
ones.

1. CCS connection attempted.
2. Probe triage completed.
3. CCS executable (`ccs` / `ccs.exe`) started.
4. Tcl script executed.
5. `config cc` succeeded.
6. `ccs::config_server` succeeded.
7. Generic or family-specific `ccs::config_chain` succeeded.
8. Target-info, core-status, attach, or later action succeeded.

## Ordered interpretation rules

### Generic discovery succeeds

1. Conclude the lower generic probe/target path is working.
2. If the request was discovery-only, this may already answer it.
3. Do not claim family-specific attach/init or higher-level debugger success.

### Family-specific chain fails after generic discovery

1. Preserve the fact that generic visibility is already proven.
2. Localize suspicion to the family chain token, local family support, init
   sequence, or attach readiness.
3. Do not collapse the failure back into generic probe reachability.

### Family-specific chain and core-status succeed

1. Conclude more than generic discovery has been proven.
2. Treat attach readiness as demonstrated.
3. Do not treat this as proof of load/run, breakpoints, reset behavior, or full
   bring-up.

### GDB failed, CCS generic discovery succeeds

1. Remove lower probe/visibility layers from the leading-suspect position.
2. Shift suspicion upward to GDB launch, bridge/session handling, target
   assumptions, or family-specific attach behavior.
3. Keep the interpretation evidence-based rather than declarative beyond the
   proven layer.

## Forbidden drift

Do not do help probing, stdin experiments, or lower-level substitutions first.
