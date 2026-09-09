# Authoring Procedure

## Root expectation

The MCP server expects an installation root from which both of these are
reachable:
- `S32Debugger/...`
- `gdb/...` or `gdb-arm/...`

## Layouts

### Standalone S32Debugger
Use the standalone install root itself, for example:
- Windows: `C:/NXP/S32DBG.3.6.8_b2605041`
- Linux:   `/home/user/NXP/S32DBG.3.6.10`

Expected structure:
- `<root>/S32Debugger`
- `<root>/S32Debugger/Debugger/Server/gta` (executable: `gta` on Linux, `gta.exe` on Windows)
- `<root>/S32Debugger/Debugger/Server/CCS`
- `<root>/gdb` or similar sibling debugger toolchain folder

### S32DS embedding
Use `.../S32DS/tools` as the root, for example:
- Windows: `C:/NXP/S32DS.3.6.6_260111/S32DS/tools`
- Linux:   `/home/user/NXP/S32DS.3.6.11/S32DS/tools`

Expected structure:
- `<tools-root>/S32Debugger`
- `<tools-root>/S32Debugger/Debugger/Server/gta` (executable: `gta` on Linux, `gta.exe` on Windows)
- `<tools-root>/S32Debugger/Debugger/Server/CCS`
- `<tools-root>/gdb-arm`

## Fast normalization rules

- exact `.../S32DS/tools` -> validate directly
- path under `.../S32DS/tools/S32Debugger/...` -> normalize up to
  `.../S32DS/tools`
- exact standalone install root with sibling `S32Debugger` and `gdb` ->
  validate directly
- path under `.../S32DBG.../S32Debugger/...` -> normalize up to standalone root

Use discovery only when normalization fails or no usable path exists.

## Discovery fallback

Search priority (Windows):
1. `C:/NXP`
2. standalone `S32DBG*` under `C:/NXP`
3. `S32DS*`, especially `.../S32DS/tools` under `C:/NXP`

Search priority (Linux):
1. `~/NXP` (user home)
2. standalone `S32DBG*` under `~/NXP`
3. `S32DS*`, especially `.../S32DS/tools` under `~/NXP`

## Candidate ranking

1. validated explicit user path
2. prior successful session path
3. strong standalone `S32DBG*` candidate
4. strong `S32DS/.../S32DS/tools` candidate
5. newest plausible version only if no better context exists

Do not silently choose when multiple strong candidates remain.
