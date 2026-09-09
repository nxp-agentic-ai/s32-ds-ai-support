# Authoring Procedure

## Workflow

1. Clarify the automation request.
   - deliverable type: Python, shell wrapper (`.sh` on Linux, `.bat`/`.cmd`
     on Windows), in-GDB Python, or mixed
   - generation only vs generation plus execution
   - target family, core, lockstep, probe, ELF/binary, startup mode
   - breakpoint, collection, and report requirements
2. Reuse the right building blocks.
   - standalone live-session behavior
   - GDB variant resolution
   - family init-sequence guidance
   - error-resolution guidance
   - existing examples or prior successful runs
3. Decide whether init logic is needed.
4. Choose the closest working pattern.
5. Generate by adaptation, not invention.
6. Support one or many deliverables explicitly.
7. Include report/log behavior when requested.
8. Explain assumptions and verification points.

## Output-style selection

### Python
Prefer for orchestration, repeated loops, metadata capture, and multi-step
reporting.

### GDB Python
Prefer for logic that should run inside the debugger, breakpoint callbacks, or
stop-time capture.

### Shell launch wrappers
Prefer for OS launch wrappers, environment setup, and reproducible local
invocation. Emit `.sh` shell scripts on Linux and `.bat`/`.cmd` batch files on
Windows; if the host OS is unknown, ask or provide both variants.

### Mixed
Use when the request explicitly asks for multiple approaches or roles.

## Adaptation rules

Preserve when grounded:
- config/startup/connect/load/breakpoint/run ordering
- GTA-before-GDB lifecycle
- bridge-backed setup for interactive keep-open sessions
- family init ordering
- working report/log structure

Adapt as needed:
- target/core/lockstep
- GDB variant
- probe IP
- ELF path
- breakpoint symbol
- hit count
- report path
- config/output names
- keep-open behavior
