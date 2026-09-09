# Examples and Anti-Patterns

## Quick examples

- `.../S32DS/tools/S32Debugger` -> normalize upward to `.../S32DS/tools`
- `.../S32DBG.3.6.8/.../S32Debugger` -> normalize upward to standalone root
- no path given (Windows) -> search `C:/NXP`, rank strong standalone and S32DS candidates
- no path given (Linux) -> search `~/NXP`, rank strong standalone and S32DS candidates
- immediate CCS execution needed -> also confirm `.../CCS/bin/ccs` exists (no `.exe` on Linux)

## Good response cues

- say whether the result came from user context or disk discovery
- say whether it came from normalization or search
- identify standalone vs S32DS-based layout
- cite the structure that validated the root
- mention the CCS executable (`ccs` on Linux, `ccs.exe` on Windows) if the next step is CCS execution

## Anti-patterns

- ignoring a valid user path and jumping to search
- treating `.../S32Debugger` as the root without checking sibling GDB folders
- silently choosing among multiple strong candidates
- claiming a root is valid without checking gta/CCS structure
