# Examples and Questions

## Typical triggers

- create a CCS Tcl script
- run this Tcl with the CCS executable (`ccs` on Linux, `ccs.exe` on Windows)
- connect CCS to my probe and identify the target
- get target info
- get core status through CCS
- GDB failed; use CCS to sanity-check the target
- run a family-specific attach sanity check

## Smallest blocking questions

- Do you want generic discovery, attach-ready control, family-specific
  attach/status sanity, full bring-up from reset, or post-GDB-failure sanity?
- Do you want Tcl generation only, execution of an existing script, or both?
- What probe IP should be used?
- If this follows a failed GDB flow, what failed and at which stage?
- If family-specific attach is requested, what family chain token should be
  used and do you want all-core status or one specific core?
- If later execution evidence is required, should the checkpoint be treated as
  result-capture or display-capture?

## Correct flow for target identification plus all-core status

This is also the preferred flow for observational requests when no interactive
session is already active.

1. probe triage
2. generic discovery
3. `ccs::config_chain {s32cc dap}`
4. `display ccs::get_target_info`
5. if family status is still needed, start a separate family-status phase
6. `ccs::config_chain {<family> dap}`
7. `display ccs::all_run_mode`
8. report each phase with its own evidence
9. stop

If machine-readable execution capture is later required, preserve this flow but
mark the family-status phase as display-capture mode.

## Anti-patterns

- invoking `ccs` / `ccs.exe` directly via `execute_command` or any shell
  command instead of using the `control.run_ccs_tcl` MCP action; always search
  the S32Debugger MCP catalog first and use the action if it is present
- generating attach-only Tcl for a cold target
- generating full init Tcl when the user asked to just attach
- skipping generic discovery when identification/readiness is the real goal
- treating `config cc` success as proof that attach/init will succeed
- preferring `cwtap:` in new flows
- continuing CCS retries even though `who` shows another CCS client
- treating family-specific core-status collection as proof of load/run or full
  bring-up behavior
- moved the discovery checkpoint onto the wrong chain
- mixed two mandated workflows into one unlabeled script
- replaced the mandatory readable checkpoint
- continued below the first sufficient answer
- reporting a combined fast-report result that makes evidence attribution
  ambiguous
- routing `ccs::all_run_mode` as if it were guaranteed to behave like a
  result-returning query
- changing the family-status checkpoint instead of changing the capture method

## Required response if blocked

If the agent cannot use the mandated checkpoint, it must say:

`I cannot follow the mandated CCS skill path because <reason>.`

Then either stop or ask whether to troubleshoot deeper.
