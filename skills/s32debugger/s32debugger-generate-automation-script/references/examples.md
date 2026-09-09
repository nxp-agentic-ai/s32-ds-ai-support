# Examples and Anti-Patterns

## Typical triggers

- generate a Python automation script for S32Debugger
- make a launch wrapper (`.sh` on Linux, `.bat`/`.cmd` on Windows) that launches GTA/GDB/config for target X
- create a GDB Python automation script
- create two automation approaches: external Python and in-GDB Python
- automate this standalone debug flow
- make a script for repeated breakpoint capture

## Packaging patterns

- external Python launcher plus in-GDB Python helper
- shell launcher (`.sh` on Linux, `.bat`/`.cmd` on Windows) plus Python worker
- config-generation helper plus report parser
- one standalone script with embedded reporting

## Anti-patterns

- generating CCS Tcl here
- inventing a new startup sequence when a working one already exists
- silently executing generated scripts when the user asked only for generation
- pretending guessed paths, symbols, or breakpoints are authoritative
- blurring generation, saving, and execution state
