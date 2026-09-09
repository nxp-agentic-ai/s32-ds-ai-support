# Examples and Anti-Patterns

## Quick routing examples

- `sanity check the probe`, `get target info`, or `get core states` with no
  interactive session already active -> `s32debugger-ccs-execution-router`
- one core such as `M7_0`, one ELF, interactive keep-open intent ->
  `s32debugger-start-singlecore-standalone-live-debug-session`
- multiple coordinated cores such as `M7_0` and `M7_1` ->
  `s32debugger-start-multicore-standalone-live-debug-session`
- `flash this image` with no request to continue debugging -> establish needed
  startup context if required, then `s32debugger-flash-programming`
- `program this ELF and then debug from flash` -> establish matching startup
  path first, then `s32debugger-flash-programming`

## Anti-patterns

- treating the router as a detailed executor
- skipping request-shape classification
- skipping programming/debug-intent classification
- routing a sanity-check, target-info, or core-state request into a GDB
  live-session flow when no interactive session is already active
- routing directly to flash execution as if no startup context were needed
- embedding the detailed `s32flash.py` flow directly in the router
- asking extra questions when the route is already obvious
