---
name: s32debugger-adapt-existing-script
description: >
  Adapt an existing standalone S32Debugger script, launcher, startup helper,
  working flow, or previously generated automation with the smallest correct
  change set while preserving proven startup, init, bridge, connect, load,
  breakpoint, and reporting structure. Use this skill when the user says
  'adapt this script', 'same flow but...', 'keep the working launcher and
  change...', 'reuse this example but modify it', or wants to retarget an
  existing Python, shell wrapper (`.sh` on Linux, `.bat`/`.cmd` on Windows),
  GDB Python, startup helper, or report script
  instead of generating a new flow from scratch.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  tags: '[s32debugger, authoring, adaptation]'
---

# S32Debugger Adapt Existing Script

Adapt an existing standalone S32Debugger script or working flow by preserving
known-good structure and changing only what the new request requires. This
skill is for grounded evolution of a baseline, not greenfield generation. It
covers Python, shell wrappers (`.sh` on Linux, `.bat`/`.cmd` on Windows), GDB
Python, startup helpers, and report scripts.

## When to use

Use this skill when:
- The user already has a script, launcher, helper, example, or working flow.
- The request is "same flow but changed for another ELF, core, probe, output,
  breakpoint, or report behavior."
- The safest path is to preserve startup, init, bridge, and data-collection
  ordering and adapt only the necessary parts.

Do **not** use this skill for:
- New standalone automation with no real baseline; use
  `s32debugger-generate-automation-script`.
- CCS Tcl-driven adaptation; use the dedicated CCS/Tcl skill.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Identify the exact baseline before changing anything

```
Baseline may be: user file, prior generated artifact, known working session
                  pattern, config/startup helper, or example template
Rule:            do not adapt "in abstract"; name the concrete source first
```

### 3. Separate structure from mutable values

```
Keep: startup order, GTA-before-GDB lifecycle, bridge pattern, config
      generation order, connect/load/break/run ordering, report layout,
      known-good init ordering
Change: target, SoC, core, lockstep, probe IP, ELF path, breakpoint,
        hit count, output path, filenames, keep-open behavior
```

### 4. Keep the minimum adaptation sequence inline

Use this order for the minimum safe adaptation path:
1. identify the exact baseline artifact or working flow
2. mark which structure must be preserved before changing values
3. classify the requested delta as local or architectural
4. change only the grounded values or structure required by that delta
5. revalidate that the result is still recognizably derived from the baseline

### 5. Classify the delta as local or architectural

```
Local: probe IP, ELF path, breakpoint, hit count, output filename,
       metadata/report extension
Architectural: no-report -> reporting, background -> bridge-backed,
               no-init -> requires init reuse/import,
               one deliverable -> multiple deliverables
Rule: local changes preserve almost all structure; architectural changes must
      still adapt from the baseline rather than rewrite casually
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Adapt existing standalone S32Debugger automation only.
- Preserve proven structure whenever possible.
- Support Python, shell wrappers (`.sh` on Linux, `.bat`/`.cmd` on Windows),
  GDB Python, startup/config helpers, and reporting
  helpers.
- Reuse adjacent S32Debugger skills when the requested change crosses into
  their specialized domain.

**Destructive actions**
- Default to adaptation planning or artifact generation unless the user also
  asks to save or run.
- Do not silently execute an adapted script.
- Do not replace the baseline wholesale when a smaller correct edit is enough.

**Refuse-and-escalate**
- If the baseline is missing, ask for the exact file, generated artifact, or
  working flow to adapt.
- If the requested change is too broad for true adaptation, say so explicitly
  and switch to the more appropriate generation or routing skill.
- If target, core, probe, ELF, or startup intent is ambiguous in a way that can
  change behavior, stop and ask.
- If the user requests major startup, init, or bridge rewrites, classify the
  change as architectural and surface the affected structure before editing.

**Adjacent-skill triggers**
- GDB variant uncertainty -> `s32debugger-resolve-gdb-variant`
- startup/live-session behavior change -> `s32debugger-start-standalone-live-session`
- family-specific init needed -> `s32debugger-lookup-for-soc-init-sequence`
- known failure recovery -> `s32debugger-error-resolution`
- baseline is really a new automation request -> `s32debugger-generate-automation-script`
- material probe/connect mechanics change -> `s32debugger-connect-gdb-to-s32-debug-probe`

**Do**
- Preserve the working baseline whenever possible.
- Classify changes as local vs architectural.
- Make minimal necessary modifications.
- Explain the delta explicitly.
- Route to adjacent skills when the adaptation spans another specialized domain.

**Do not**
- Regenerate from scratch when adaptation is sufficient.
- Change startup sequencing without strong reason.
- Drop known-good init, bridge, or report behavior silently.
- Present a rewrite as if it were an in-place modification.

### Result contract

A good adaptation result should contain:
- baseline used
- requested adaptation summary
- preservation summary
- local-vs-architectural classification
- adapted artifact or saved file path
- assumptions and revalidation points

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm the baseline is explicit and concrete, not an abstract idea.
2. Confirm the unchanged areas are identified before editing starts.
3. Classify the request as local or architectural and state why.
4. Verify preserved structure still covers startup, init, bridge, connect,
   load, breakpoint, run, and reporting behavior where applicable.
5. Verify each changed value is grounded: target/SoC/core, probe parameters,
   ELF path, symbols, filenames, output paths, session behavior.
6. Check that the result is still recognizable as an evolution of the
   baseline, not a hidden rewrite.
7. Return a delta-oriented summary: baseline used, what changed, what was kept,
   assumptions, and revalidation points.

## Out of scope

- Greenfield automation generation with no meaningful baseline.
- Pretending a rewrite is a small in-place adaptation.
- Silent changes to working startup, init, bridge, or reporting sequencing.
- Guessing new target behavior without surfacing assumptions.
- Treating adaptation, saving, and execution as the same operation.

## See Also

- `references/authoring-procedure.md` - condensed adaptation workflow,
  change classification, and output pattern.
- `references/examples.md` - trigger examples, typical deltas, and
  verification checklist items.
- Related skills: `s32debugger-generate-automation-script`,
  `s32debugger-start-standalone-live-session`,
  `s32debugger-resolve-gdb-variant`,
  `s32debugger-lookup-for-soc-init-sequence`,
  `s32debugger-error-resolution`,
  `s32debugger-connect-gdb-to-s32-debug-probe`
