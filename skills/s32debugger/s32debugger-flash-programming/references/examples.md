# Examples and Anti-Patterns

## Quick routing examples

- flash this ELF and stop after programming -> `s32debugger-flash-only-operations`
- erase this flash device and verify the result -> `s32debugger-flash-only-operations`
- program this image and then debug it from flash -> `s32debugger-debug-from-flash`
- write this binary and keep the same debug session alive afterward ->
  `s32debugger-debug-from-flash`

## Response cues

- classified flash scenario
- chosen downstream skill
- whether startup/probe context is already present
- whether the resulting session should close or remain open
- key next step

## Anti-patterns

- using one blended flow for both flash scenarios
- calling `fl_close` when the user wants same-session debug-from-flash
- skipping `fl_close` for flash-only work
- using debug-from-flash continuation for erase, verify, read, or dump
- pretending missing GDB/GTA/probe context is already satisfied
