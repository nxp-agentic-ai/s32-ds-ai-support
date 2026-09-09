---
name: s32debugger-generate-automation-script
description: >
  Generate standalone S32Debugger automation scripts from grounded existing
  flows rather than inventing them from scratch. Use this whenever the user
  wants a new automation script or script set for standalone S32Debugger, such
  as Python, shell launch wrappers (`.sh` on Linux, `.bat`/`.cmd` on Windows),
  in-GDB Python, launch wrappers, data-collection helpers,
  or mixed deliverables that automate config generation, GTA/GDB startup, ELF
  load, breakpoints, repeated capture, and report/log creation. Excludes CCS
  Tcl generation.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: '[s32debugger-generate-gdb-config-file, s32debugger-resolve-gdb-variant, s32debugger-lookup-for-soc-init-sequence]'
  tags: '[s32debugger, automation, authoring]'
---

# S32Debugger Generate Automation Script

Generate grounded standalone S32Debugger automation deliverables by adapting
known-good flows instead of improvising new ones. This skill covers Python,
shell launch wrappers (`.sh` on Linux, `.bat`/`.cmd` on Windows), in-GDB
Python, helper wrappers, mixed deliverables, and report/log
collection around standalone debugger workflows.

## When to use

Use this skill when:
- The user wants a new standalone S32Debugger automation script or script set.
- The request involves config generation, GTA/GDB startup, ELF load,
  breakpoints, repeated capture, reporting, or wrapper automation.
- The user describes the task informally as "make a script", "automate this
  debug flow", or "create a launcher/report script".

Do **not** use this skill for:
- CCS Tcl generation.
- Inventing a new startup approach when a known-good S32Debugger flow already
  exists and can be adapted.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Clarify the requested deliverable and execution intent

```
Need: Python | shell wrapper (.sh Linux / .bat|.cmd Windows) | in-GDB Python | mixed deliverables
Need: generation only | generate and save | generate and execute
Need: target/core/probe/ELF/startup/report requirements
```

### 3. Keep the authoring split inline

| Situation | Behavior |
| --- | --- |
| existing working flow or example exists | adapt from it |
| family init already exists | reuse/import it instead of inventing |
| request is generation only | generate and save, do not execute |
| request asks for multiple deliverables | emit each deliverable explicitly |
| key values are missing | ask only for those blockers |

### 4. Keep the minimum authoring sequence inline

Use this order for the minimum safe authoring path:
1. determine deliverable type and execution intent
2. choose the grounded base pattern or nearest justified working flow
3. resolve required startup, variant, and init dependencies
4. preserve config/startup/connect/load/breakpoint/run/collect ordering
5. generate one or more deliverables without blurring their roles
6. execute only if the user explicitly requested execution

### 5. Preserve base-pattern and packaging rules

```
Prefer: reuse startup skill guidance, variant resolution, family init guidance,
        known working examples/configs, and prior successful runs
Preserve: config/startup/connect/load/breakpoint/run/collect ordering
Support: one-script or multi-deliverable packaging without blurring roles
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Generate standalone S32Debugger automation only.
- Support Python, shell launch wrappers (`.sh` on Linux, `.bat`/`.cmd` on
  Windows), in-GDB Python, helper wrappers, and mixed
  deliverables.
- Match the wrapper flavor to the host OS: emit `.sh` for Linux and
  `.bat`/`.cmd` for Windows; if the target OS is unknown, ask or emit both.
- Preserve proven ordering for config, startup, connect, load, breakpoint,
  run, and collection steps.
- Include or reuse init logic only when requested or required.

**Destructive actions**
- Default to generation or save-only behavior unless the user also asks for
  execution.
- Do not silently execute generated scripts if the user asked only for
  generation.
- Do not blur together generation, saving, and execution state.

**Refuse-and-escalate**
- If key values are missing and they block grounded generation, ask only for
  those values.
- If the request is really for CCS Tcl, route to the dedicated CCS skill.
- If the script depends on guessed symbols, paths, breakpoints, or init logic,
  mark those assumptions explicitly instead of presenting them as authoritative.
- If a narrower specialized skill is the right fit, reuse or defer to it rather
  than replacing it.

**Authoring rules**
- Prefer adaptation from existing working flows over greenfield invention.
- When init is needed, prefer reuse/import of existing initialization logic
  before embedding new inline init.
- Support multi-deliverable requests cleanly, but keep each deliverable's role,
  runtime environment, and execution intent explicit.
- If the user asks to generate but not run, obey that constraint and save only.

**Do**
- Reuse known-good standalone S32Debugger patterns.
- Use the correct GDB variant for the selected core.
- Include bridge-backed behavior when the workflow requires interactive
  keep-open control.
- Include report metadata when the user asks for data collection.

**Do not**
- Generate CCS Tcl here.
- Invent a new startup sequence when a working one already exists.
- Claim scripts are execution-ready if key values were inferred.

### Result contract

A good authoring result should contain:
- deliverable type(s)
- execution intent: generate-only vs save vs execute
- grounded base pattern used
- preserved vs adapted parts
- generated script(s)
- assumptions and verification checklist

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm the deliverable type and execution intent are explicit.
2. Verify the target/core/probe/ELF/startup requirements are grounded enough
   for script generation.
3. Verify the chosen base pattern is identified and that preserved ordering is
   deliberate.
4. Verify init logic is included, reused, or omitted for a stated reason.
5. Verify the final response distinguishes generated-only, saved, and executed
   state.
6. Return the automation plan, adaptation summary, generated script(s),
   save/execute status, assumptions, and verification checklist.

## Out of scope

- CCS Tcl generation.
- Presenting guessed paths or symbols as authoritative.
- Silently executing scripts when the user asked only for generation.
- Replacing narrower specialized skills without need.

## See Also

- `references/authoring-procedure.md` - workflow, output-style selection, and
  adaptation rules.
- `references/examples.md` - trigger examples, packaging patterns, and
  anti-patterns.
- Related skills: `s32debugger-start-standalone-live-session`,
  `s32debugger-connect-gdb-to-s32-debug-probe`,
  `s32debugger-generate-gdb-config-file`, `s32debugger-resolve-gdb-variant`,
  `s32debugger-lookup-for-soc-init-sequence`,
  `s32debugger-error-resolution`
