---
name: s32debugger-start-singlecore-standalone-live-debug-session
description: >
  Execute the dedicated standalone S32Debugger live-debug workflow for one
  explicit core instance. Use this whenever the user wants a single-core
  standalone debug session, names one core such as `M7_0` or `A53_0_0`, wants
  to load one ELF, asks for an interactive or keep-open session, or wants
  breakpoint validation and follow-up control for exactly one target core.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: '[s32debugger-generate-gdb-config-file, s32debugger-resolve-core-name-from-context, s32debugger-resolve-gdb-variant]'
  tags: '[s32debugger, singlecore, execution]'
---

# S32Debugger Start Single-Core Standalone Live Debug Session

Execute the dedicated single-core standalone live-debug workflow. This skill is
for already-classified single-core requests: resolve the exact core instance,
select the right GDB variant, generate the best matching single-core startup
shape, validate bridge and breakpoint behavior when requested, and keep the
session open for follow-up control.

## When to use

Use this skill when:
- The request is clearly for one explicit target core in a standalone
  S32Debugger live session.
- The user wants one ELF or symbol target loaded for one core and expects a
  keep-open or interactive session.
- The user wants breakpoint validation and follow-up control for exactly one
  core.

Do **not** use this skill for:
- Requests that are actually multicore or still ambiguous about topology.
- Accepting an all-cores startup shape without challenge for a clearly
  single-core request.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Resolve the exact single-core identity

```
Examples: M7_0, M7_1, A53_0_0
Rule: use the normalized family for variant selection, but preserve the full
      explicit core instance for startup and client identity
```

### 3. Generate a true single-core startup shape

```
Find: best matching Python example template
Generate: base config with generate.gdb_config_file (REST bridge embedded)
Reject: accidental all-cores or multicore bring-up when a single-core path fits
```

### 4. Keep the minimum single-core startup sequence inline

Use this order for the minimum safe single-core startup path:
1. inspect any existing target transport ports (target GDB server port, CCS port) and choose a bridge port distinct from them
2. generate the base config with `generate.gdb_config_file`, passing the chosen bridge port (the bridge is embedded in the generated config)
3. start GDB for the explicit single-core client identity with `control.start_gdb` (it launches GTA automatically)
4. validate bridge responsiveness
5. validate requested breakpoint or session state
6. keep the session open unless the user asks to stop it

```
Order: choose distinct bridge port -> generate base config (bridge embedded) -> control.start_gdb (auto-starts GTA + GDB) -> bridge validation -> breakpoint/session validation
Result: keep the session open unless the user asks to stop it
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Execute only the dedicated single-core live-debug workflow.
- Preserve the exact core instance and use it as the explicit client identity.
- Choose the GDB variant from the core family, not from the SoC alone.
- Prefer a true single-core startup shape and validate that the generated
  config does not accidentally become all-cores or multicore.
- Treat the generated base config's target GDB server port as a transport port,
  not as the bridge port.
- Treat the bridge port as a separate local control endpoint for MCP follow-up
  control.

**Destructive actions**
- Default to keeping the session open after successful startup.
- Inspect the generated base config and preserve any target transport ports it
  already defines when choosing the bridge port.
- Do not invent or hand-write a config when template discovery plus config
  generation is available.
- Do not report success before bridge or breakpoint/session validation is done
  when those validations are part of the request.

**Refuse-and-escalate**
- If the request no longer looks single-core, route back to the standalone
  router or the multicore skill instead of forcing it through this workflow.
- If the exact core instance is missing, ask only for that missing detail.
- If the generated config points to an all-cores path for a clearly single-core
  request, stop and regenerate from a better single-core source.
- For authoritative family-context values or low-level probe-connection rules,
  defer to the family-context and probe-connection skills rather than
  reconstructing them here.

**Do**
- Use bridge-backed startup for interactive keep-open requests.
- Choose a bridge port that is distinct from the generated config's target GDB
  server port, distinct from the CCS port, and not already in use.
- Preserve the explicit client identity from the first `start_gdb` call.
- Validate bridge responsiveness and breakpoint/session state before claiming
  success.

**Do not**
- Rely on client inference in single-core interactive sessions.
- Collapse `M7_0` to plain `M7` and lose instance identity.
- Close the session automatically after startup when the user asked for a live,
  open session.
- Reuse the generated config's target GDB server port as the bridge port.

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm the request is truly single-core and the exact core instance is
   resolved.
2. Verify the GDB variant is selected from the core family.
3. Verify the chosen example template and generated config reflect single-core
   intent rather than all-cores or multicore behavior.
4. Verify the bridge port is distinct from the generated config's target GDB
   server port, distinct from the CCS port, and not already in use.
5. Verify the explicit client identity is used from the first GDB start.
6. Verify bridge responsiveness and requested breakpoint/session state.
7. Return the resolved core instance, selected variant, chosen template,
   generated config path, bridge use, selected bridge port, startup results,
   validation results, and confirmation that the session remains open.

## Out of scope

- Multicore orchestration.
- Accepting a mismatched all-cores startup shape without challenge.
- Guessing the exact core instance when it is materially required.
- Inventing a manual config when the template-plus-tool path exists.

## See Also

- `references/authoring-procedure.md` - single-core workflow, template
  priority, and failure handling.
- `references/examples.md` - quick scenarios and anti-patterns.
- Related skills: `s32debugger-start-standalone-live-session`,
  `s32debugger-resolve-gdb-variant`,
  `s32debugger-resolve-core-name-from-context`,
  `s32debugger-connect-gdb-to-s32-debug-probe`,
  `s32debugger-error-resolution`
