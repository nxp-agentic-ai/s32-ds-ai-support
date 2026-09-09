---
name: s32debugger-lookup-for-soc-init-sequence
description: >
  Identify, inspect, explain, and family-consistently adapt S32Debugger SoC
  init sequences by starting from the existing family generic and init scripts
  and preserving dispatcher compatibility. Use this whenever the user asks
  which init sequence a family uses, wants the bring-up path explained, needs
  the real helper or dispatcher entry point, or wants an existing family init
  sequence adapted for a derivative, core, or mode.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: '[s32debugger-resolve-core-name-from-context]'
  tags: '[s32debugger, init, inspection]'
---

# S32Debugger SoC Init Sequence

Identify, inspect, explain, and family-consistently adapt S32Debugger init
sequences by starting from the real family files. This skill is for lookup,
explanation, and baseline-preserving adaptation of SoC-family bring-up logic,
not for executing a live debug session.

## When to use

Use this skill when:
- The user wants to know which init sequence a SoC family or core uses.
- The user wants the actual bring-up path, helper functions, or dispatcher
  entry point explained from real S32Debugger family files.
- The user wants a family-consistent init-sequence adaptation for a derivative,
  core, or mode.

Do **not** use this skill for:
- Live debug startup, flash programming, or general session routing.
- Inventing a new init style when a family baseline already exists.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Resolve the family first

```
Map: soc_name or family -> <install>/S32Debugger/Debugger/scripts/<family>
Rule: if family is ambiguous, stop at the closest justified candidate and say why
```

### 3. Keep the minimum ordered inspection sequence inline

Use this order for the minimum safe inspection path:
1. resolve the family directory
2. read `<family>_generic_bareboard.py`
3. read `<family>_init_sequence.py`
4. read `<family>_context.py`, `<family>_cores.py`,
   `<family>_generic_bareboard_all_cores.py`, or `<family>_attach.py` only as
   needed to resolve ambiguity
5. identify the dispatcher or real public init entry point
6. only then explain or adapt the family init flow

```
Read first:   <family>_generic_bareboard.py
Read second:  <family>_init_sequence.py
Read when needed: <family>_context.py, <family>_cores.py,
                  <family>_generic_bareboard_all_cores.py, <family>_attach.py
Find:         dispatcher or real public init entry point
```

### 4. Preserve the public model actually used by the family

```
Common case:  init_sequence_by_core_name(...)
Exception:    direct public entry points or another dispatcher model
Rule:         report the real model; do not force the common one
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Work inside the standalone S32Debugger scripts tree under the current local
  installation.
- Inspect generic, init-sequence, and related family files before explaining
  or adapting behavior.
- Preserve family helper style, dispatcher compatibility, and baseline
  sequencing when proposing changes.
- Explain the init sequence in terms of real operations, not only file names.

**Destructive actions**
- Default to lookup, explanation, and conservative adaptation guidance.
- Do not present startup execution as if this skill performs it directly.
- Do not modify unrelated families when the request is SoC-specific.

**Refuse-and-escalate**
- If the family mapping is unclear, report the closest justified candidate,
  explain the ambiguity briefly, and ask before proceeding.
- If the family does not use `init_sequence_by_core_name(...)`, report the real
  public model instead of forcing the common pattern.
- If no exact baseline exists for authoring, use the nearest justified helper
  and say explicitly that the baseline is approximate.
- If the request is really for live startup or flash execution, hand off to the
  startup or flash skills instead.

**Preservation rules**
- If the generic script calls `init_sequence_by_core_name(_CORE_NAME,
  _SOC_NAME, ...)`, any new or modified helper must remain reachable from that
  dispatcher or its family-equivalent.
- Preserve the family helper/API style such as the existing `mcme` utility
  layer rather than replacing it with a new abstraction.
- Explain authoring deltas in terms of baseline helper used, changed register
  operations, sequencing changes, and dispatcher impact.

**Do**
- Inspect `<family>_generic_bareboard.py` first.
- Inspect `<family>_init_sequence.py` and related context/core files when
  needed.
- Preserve family helper/API style such as the existing `mcme` utility layer.

**Do not**
- Invent helper names or entry points without reading the files.
- Assume attach and init flows are interchangeable.
- Present machine-specific install paths as generic guidance unless a concrete
  local path is explicitly requested.

### Result contract

A good lookup/adaptation result should contain:
- resolved family
- exact generic script path
- exact init-sequence path
- dispatcher or public init entry point
- relevant helper path or operation summary
- adaptation delta when changes are requested

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm the family directory is justified from the requested SoC or family.
2. Verify the family generic script and init-sequence script were both
   inspected.
3. Verify the dispatcher or actual public init entry point is identified from
   the real files.
4. Verify the explanation or adaptation follows the existing family helper
   style and baseline structure.
5. If authoring/adaptation is requested, verify dispatcher compatibility is
   preserved or explicitly updated.
6. Return the resolved family, exact file paths, relevant helper/dispatcher
   functions, operation summary, and any adaptation delta.

## Out of scope

- Executing live-debug startup or flash workflows.
- Guessing a family or helper naming scheme without inspection.
- Forcing the common dispatcher model onto a family that uses another pattern.
- Inventing a new initialization style unrelated to the family baseline.

## See Also

- `references/authoring-procedure.md` - family resolution, inspection steps,
  and adaptation rules.
- `references/examples.md` - common family patterns, example families, and
  anti-patterns.
- Related skills: `s32debugger-resolve-core-name-from-context`,
  `s32debugger-adapt-existing-script`,
  `s32debugger-start-standalone-live-session`
