---
name: s32debugger-discover-installation
description: >
  Resolve the correct S32Debugger installation root for MCP use. Use this
  whenever the user wants to find S32Debugger on disk, set or confirm the
  installation path, gives a path under `S32Debugger` or `S32DS/tools`,
  mentions an NXP install under `C:/NXP`, or needs the path normalized before
  template lookup, config generation, standalone debug startup, or CCS
  sanity-check execution.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  tags: '[s32debugger, installation, discovery]'
---

# S32Debugger Discover Installation

Resolve and normalize the S32Debugger installation root that should be passed
into MCP tooling. This skill prefers explicit user context first, normalizes
subpaths to the correct root, distinguishes standalone and S32DS-embedded
layouts, and only falls back to filesystem discovery when needed.

## When to use

Use this skill when:
- The user wants to find, set, or confirm the S32Debugger installation root.
- The user provides a path under `S32Debugger`, `S32DS/tools`,
  `Debugger/Server`, or `Debugger/scripts` that needs normalization.
- A later step needs a validated installation root before template lookup,
  startup, or CCS sanity execution.

Do **not** use this skill for:
- Searching inside an already known installation for examples or scripts; use
  `s32debugger-navigate-installation`.
- Ignoring a clear user-provided path in favor of blind disk search.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Prefer normalization over search when the user already gave a path

```
Fast paths: .../S32DS/tools -> validate directly
            .../S32DS/tools/S32Debugger/... -> normalize up to .../S32DS/tools
            .../S32DBG.../S32Debugger/... -> normalize up to standalone root
```

### 3. Validate the candidate root against expected structure

```
Need: S32Debugger/... plus sibling gdb or gdb-arm folder at the same root
Check: gta and CCS under S32Debugger/Debugger/Server
Output: normalized root ready for set_installation_path
```

### 4. Fall back to filesystem discovery only if needed

```
Search:  C:/NXP first (Windows) or ~/NXP first (Linux)
Prefer:  validated user path, prior successful session path, then strong
         standalone S32DBG* or S32DS/.../S32DS/tools candidates
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Resolve the installation root only.
- Distinguish standalone S32Debugger installs from S32DS-embedded tools roots.
- Explain whether the result came from normalization or fresh discovery.
- If CCS execution is the immediate next step, also confirm whether the
  resolved root contains `S32Debugger/Debugger/Server/CCS/bin/ccs` (Linux) or
  `S32Debugger/Debugger/Server/CCS/bin/ccs.exe` (Windows).

**Destructive actions**
- Default to normalization and inspection, not broad search.
- Do not silently choose among multiple strong candidates without explanation.
- Do not set the root to only `.../S32Debugger` when sibling GDB folders must
  also be reachable from the true installation root.

**Refuse-and-escalate**
- If a user-provided path cannot be normalized to a valid candidate, say so and
  then fall back to discovery.
- If multiple strong candidates remain, list them and ask or explain the
  ranking rather than silently picking one.
- If the user needs in-installation file lookup after root resolution, hand off
  to `s32debugger-navigate-installation`.
- If the next step is CCS execution, explicitly report whether the CCS
  executable (`ccs` on Linux, `ccs.exe` on Windows) was confirmed or is missing.

**Do**
- Prefer explicit user context before filesystem discovery.
- Normalize the shortest valid upward path and stop once validation succeeds.
- On Windows prefer `C:/NXP` as the first filesystem search location; on Linux
  prefer `~/NXP`, unless the user says otherwise.

**Do not**
- Assume standalone installs are the only valid layout.
- Assume `.../S32Debugger` itself is always the correct MCP root.
- Claim a candidate is valid without checking the expected debugger structure.

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm whether a concrete user path already exists and can be normalized.
2. Verify the normalized candidate exposes both `S32Debugger/...` and sibling
   `gdb/...` or `gdb-arm/...` from the same root.
3. Verify key debugger evidence exists, especially `Debugger/Server/gta` and
   `Debugger/Server/CCS` under `S32Debugger`.
4. If CCS execution is the next step, verify `.../CCS/bin/ccs` (Linux) or `.../CCS/bin/ccs.exe` (Windows) exists.
5. If discovery was needed, verify candidates were ranked by user context,
   prior success, structural strength, and only then version recency.
6. Return the source of discovery, normalized root, install type, evidence,
   readiness for `set_installation_path`, and any remaining ambiguity.

## Out of scope

- Navigating examples or scripts inside an already known installation.
- Ignoring a valid user-provided path and searching blindly.
- Quietly picking one version when several strong installs are plausible.
- Confusing installation discovery with in-installation file discovery.

## See Also

- `references/authoring-procedure.md` - normalization rules, discovery
  heuristics, and ranking logic.
- `references/examples.md` - quick examples, response cues, and anti-patterns.
- Related skills: `s32debugger-navigate-installation`
