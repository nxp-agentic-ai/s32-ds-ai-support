# Outcomes and Anti-Patterns

## Common outcomes

- telnet `who` output lists a `ccs` process -> another CCS client owns the
  probe; it is busy; stop (no `ccs` process in the output means it is ready)
- `config cc` succeeds, later chain fails -> lower connectivity may be fine,
  deeper chain/init logic is failing
- generic `s32cc dap` discovery succeeds -> generic target visibility is proven
- family-specific chain succeeds and readable status works -> attach sanity is
  proven above generic discovery
- visible CCS opens but no log/result file appears -> UI launch alone is proven
- `ccs::get_target_info` captured via `set x [ccs::get_target_info]` -> this
  proves the command returns a Tcl value
- `ccs::all_run_mode` visible in CCS but empty via `set x [ccs::all_run_mode]`
  -> likely display-oriented output, not a failed target command
- redirected stdout/stderr empty even for Tcl `puts` -> likely CCS executable
  `-script` output-capture-path mismatch, not target failure

## Minimal correct executions

### Discovery execution

Always use the `control.run_ccs_tcl` MCP action. Do not invoke `ccs.exe` or
`ccs` directly via shell. Before calling the action, confirm that
`control.set_installation_path` has been called for this session:

```
s32debugger_execute_action("control.set_installation_path",
                           {"installation_path": "<S32Debugger root>"})
s32debugger_execute_action("control.run_ccs_tcl",
                           {"tcl_script_path": "<absolute path to discovery.tcl>"})
```

Where `discovery.tcl` contains only:
```tcl
config cc s32dbg:10.17.102.37
ccs::config_init_action 1 2 0 0 0 0
ccs::config_chain {s32cc dap}
display ccs::get_target_info
quit
```

### Family-status execution

Use the same `control.run_ccs_tcl` action for the family-status script:

```
s32debugger_execute_action("control.run_ccs_tcl",
                           {"tcl_script_path": "<absolute path to family-status.tcl>"})
```

## Reporting cues

- say which launch mode was used and why
- separate process start from Tcl execution evidence
- separate probe availability from chain success
- separate generic discovery from family-specific attach sanity
- state explicitly what remains unproven
- state how the requested checkpoint was captured: Tcl result, printed output,
  or both

## Anti-patterns

- invoking `ccs` / `ccs.exe` directly via `execute_command` or any shell
  command instead of using the `control.run_ccs_tcl` MCP action; search the
  S32Debugger MCP catalog first and use the action if it is present
- claiming success because the UI opened
- retrying CCS even though `who` already shows probe occupancy
- treating `config cc` success as full-workflow success
- treating successful family core-status output as proof of load/run or bring-up
- retrying GDB repeatedly after an ambiguous failure without comparing against a
  minimal CCS sanity result first
- using `-help`, stdin piping, mixed-phase scripts, or lower-level substitutions
  before the mandated readable checkpoint
- treating `ccs::all_run_mode` as if it must return the displayed text as a Tcl result
- escalating to family init changes before proving whether the failure is only in output capture
- concluding target failure because the CCS executable's `-script` redirected stdout/stderr are empty
