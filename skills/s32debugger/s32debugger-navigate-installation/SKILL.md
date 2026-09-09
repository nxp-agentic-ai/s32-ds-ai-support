---
name: s32debugger-navigate-installation
description: >
  Navigate a known S32Debugger installation root to find the right examples,
  scripts, templates, and config-generation inputs. Use this whenever the
  installation root is already known and the user wants to locate a
  `SingleCore`, `MultiCore`, or `FlashProgrammer` example, find an internal
  debugger script, choose between `S32Debugger/Examples` and
  `S32Debugger/Debugger/scripts`, or identify the best matching file by
  `soc_family`, `script_type`, or `core_name`.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: '[s32debugger-discover-installation]'
  tags: '[s32debugger, navigation, lookup]'
---

# S32Debugger Navigate Installation

Navigate inside a known S32Debugger installation root to find the right
examples, templates, and internal scripts. This skill chooses between
`S32Debugger/Examples` and `S32Debugger/Debugger/scripts`, applies family and
core filters, and explains whether the result is a user-facing example or a
lower-level debugger support script.

## When to use

Use this skill when:
- The installation root is already known and the user wants a matching example,
  template, or internal script.
- The request needs help choosing between `Examples` and `Debugger/scripts`.
- The user wants the best match by `soc_family`, `script_type`, or
  `core_name`.

Do **not** use this skill for:
- Discovering the installation root itself; use
  `s32debugger-discover-installation`.
- Claiming a support script is a config-generation template. Always check its role.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Decide whether the request is example-oriented or script-oriented

```
Examples: user-facing templates, config-generation bases, SingleCore/MultiCore/
          FlashProgrammer examples
Scripts:  lower-level init, attach, reset, connect, or helper implementation
```

### 3. Choose the first root folder accordingly

```
Examples first:          <install>/S32Debugger/Examples/<soc_family>/...
Debugger/scripts first:  <install>/S32Debugger/Debugger/scripts/<soc_family>/...
```

### 4. Narrow the match deliberately

```
Filter by: soc_family -> script_type -> core_name
Return:    best matching file(s), exact vs closest match, and why
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Navigate only inside an already known installation root.
- Clearly distinguish example templates from debugger support scripts.
- Choose the correct starting folder based on task intent.
- Explain why the selected file is the best match.

**Destructive actions**
- Default to inspection and navigation only.
- Do not perform installation discovery here.
- Do not silently choose a weak or closest match without saying so.

**Refuse-and-escalate**
- If the installation root is unknown or ambiguous, stop and use
  `s32debugger-discover-installation` first.
- If the request is ambiguous about template discovery versus script
  inspection, ask that question before searching broadly.
- If key filters such as `soc_family`, `script_type`, or `core_name` are
  missing and they materially affect the search, ask only for those missing
  details.
- If no exact match exists, explicitly return the closest viable file with the
  mismatch explained.

**Do**
- Prefer `Examples` for template and config-generation workflows.
- Prefer `Debugger/scripts` for init, attach, connect, or lower-level support
  script inspection.
- Use `soc_family` as the first strong filter.

**Do not**
- Mix up `Examples` and `Debugger/scripts` without explanation.
- Claim an internal support script is a public example template.
- Skip explaining why a particular file was selected.

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm the installation root is already known.
2. Verify the task is classified as example-oriented or script-oriented.
3. Verify the chosen root folder matches that classification.
4. Verify `soc_family`, `script_type`, and `core_name` filters are applied when
   relevant.
5. Verify the returned file is labeled correctly as an example template or a
   debugger support script.
6. Return the installation root used, searched folder, filters, best matching
   file(s), exact-vs-closest status, and suggested next step.

## Out of scope

- Discovering installations on disk.
- Treating `Debugger/scripts` results as config-generation templates by default.
- Silently selecting a weak match when stronger filtering is still possible.
- Skipping the explanation of why a file was chosen.

## See Also

- `references/authoring-procedure.md` - folder-choice rules, filtering order,
  and navigation workflow.
- `references/examples.md` - quick examples, response cues, and anti-patterns.
- Related skills: `s32debugger-discover-installation`,
  `s32debugger-generate-gdb-config-file`,
  `s32debugger-lookup-for-soc-init-sequence`
