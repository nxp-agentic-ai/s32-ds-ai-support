# Examples and Anti-Patterns

## Quick triage examples

- `sanity check the probe and get the core states if possible` with no active
  interactive session -> do probe triage, CCS generic discovery, then
  family-specific CCS all-core status; do not start with GDB attach plumbing
- `connection to server refused` right after connect -> likely CCS/probe or
  local-service stage; check GTA/CCS order and listening endpoints; if still
  ambiguous, run CCS generic discovery
- interactive window appears but follow-up commands fail -> likely bridge
  stage; validate the generated config bridge port and bridge transcript
- breakpoint is hit but source path warning appears -> likely symbol/source
  warning; may be non-blocking if symbolic stop-state is otherwise correct
- repeated ambiguous GDB attach failures -> stop blind retries and run probe
  triage plus CCS generic discovery
- `ccs::all_run_mode` shows core states when tested manually, but automation
  captures an empty result -> likely output-capture mismatch; inspect whether
  the command prints via `display` / `puts` before changing target init or
  chain assumptions
- family chain build fails with `<part>: Bus error` (generic discovery already
  succeeded) -> likely wrong DAP variant on the family chain; the family used
  `dap` but is an RTU-based / DAP-v6 part (e.g. S32N/s32nz) that requires
  `dapv6`. Confirm the exact chain token in the family init-script header
  (`knowledge/s32debugger/tcl_scripts/<family>_init*.tcl`, chunk_index 0) and
  retry with `ccs::config_chain {<family> dapv6}`
- a per-core op (`ccs::stop_core` / `run_core` / `read_mem` / `write_mem` /
  `config_template` / `core_run_mode`) fails with `Unimplemented` or
  `Invalid parameter` while chain-level queries (`ccs::all_run_mode`) succeed ->
  the core index is a wrong chain position, not an unsupported command. The
  targeted position is likely a non-core node (SoC/subcore); every CCS command
  is supported under `-script`. Run `display ccs::get_config_chain` to get the
  real positions and retry against the resolved core position (the first core is
  often position 1, since the SoC node can occupy position 0)



## Interpretation matrix cues

- GDB failed + CCS generic discovery succeeds -> lower generic path is healthy;
  likely issue moves upward to GDB/session/configuration or deeper attach logic
- GDB failed + CCS generic discovery fails -> likely lower-layer issue
- GDB failed + generic discovery succeeds + family sanity succeeds -> lower
  path and known family chain are healthy; likely issue is above that layer
- GDB failed + generic discovery succeeds + family sanity fails -> likely issue
  is family chain, local support, init sequence, or target-state mismatch;
  if the family sanity failed with a "Bus error" while building the chain,
  check the DAP variant first (`dap` vs `dapv6`) before anything else

- visible CCS output + empty command substitution + empty redirected stdout/stderr
  -> likely output-capture mismatch, not immediate evidence of a target failure
- chain-level query works + a specific per-core op returns `Unimplemented` /
  `Invalid parameter` -> chain-position mismatch (wrong index / non-core node),
  not an unsupported command; resolve positions with
  `display ccs::get_config_chain` before concluding anything about CCS or target
  capability


## Anti-patterns

- repeatedly retrying GDB without first proving probe availability or generic
  target visibility
- escalating directly from ambiguous GDB failure to full bring-up without
  considering generic CCS discovery
- treating a failed GDB session as proof that the target requires init
- treating successful family-specific core-status output as proof of full
  load/run/reset behavior
- starting with GDB session prep for an observational-only sanity / target-info
  / core-state request when no interactive session is already active
- diagnosing a capture-path mismatch as a family-init problem without first
  checking whether the command is display-oriented
- escalating from empty redirected stdout/stderr directly to target-state
  conclusions
