---
name: s32debugger-resolve-core-name-from-context
description: >
  Resolve the authoritative `_CORE_NAME`, `_SOC_NAME`, and related
  family-context values from `<family>_context.py`. Use this whenever an
  S32Debugger flow needs exact family-script values before init-sequence
  execution, config generation, core-sensitive tool parameters, or validation
  of derivative-specific startup behavior, especially when the user only knows
  the SoC or family and the flow must not guess or construct `_CORE_NAME`
  manually.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: '[s32debugger-discover-installation, s32debugger-navigate-installation]'
  tags: '[s32debugger, context, resolution]'
---

# S32Debugger Resolve Core Name from Context

Resolve authoritative family-context values such as `_CORE_NAME` and
`_SOC_NAME` from `<family>_context.py` and validate them against the family
init dispatcher when relevant. This skill exists to stop downstream flows from
guessing or constructing family-script values manually.

## When to use

Use this skill when:
- A flow needs exact `_CORE_NAME` or `_SOC_NAME` before init-sequence
  execution, config generation, or core-sensitive startup behavior.
- The user knows the SoC or family but not the exact family-script values.
- The downstream flow must validate derivative-specific init dispatch rather
  than relying on a normalized or guessed core string.

Do **not** use this skill for:
- Guessing or constructing `_CORE_NAME` from the SoC part number.
- Replacing startup execution, GDB-variant resolution, or flash workflows.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Identify the family directory first

```
Map: SoC or family hint -> <install>/S32Debugger/Debugger/scripts/<family>
Rule: if unclear, stop at the closest justified candidate and say why
```

### 3. Read the authoritative context file

```
Open: <family>_context.py
Extract: _CORE_NAME, _SOC_NAME, and other relevant top-level globals
Trace: imported constants when values are not literal strings
```

### 4. Validate against the family init dispatcher when relevant

```
Check: core branch matches _CORE_NAME
Check: derivative branch matches _SOC_NAME
Return: values verbatim, plus validation status
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Resolve authoritative family-context values only.
- Read `<family>_context.py` when available and fall back only when necessary.
- Keep authoritative values separate from normalized helper concepts.
- Validate `_CORE_NAME` and `_SOC_NAME` against the family init dispatcher when
  the downstream flow depends on that behavior.

**Destructive actions**
- Default to inspection and exact value reporting only.
- Do not rewrite authoritative family values into a normalized form.
- Do not substitute guessed values when context resolution is incomplete.

**Refuse-and-escalate**
- If the family mapping is unclear, report the closest justified candidate and
  ask before proceeding further.
- If `_CORE_NAME` or `_SOC_NAME` is assigned indirectly, trace the imported
  constant before reporting the result.
- If `_context.py` is absent or incomplete, use `<family>_cores.py` only as a
  fallback and say so explicitly.
- If dispatcher validation cannot be completed, return the extracted values and
  mark validation as incomplete instead of inventing a correction.

**Do**
- Return `_CORE_NAME` and `_SOC_NAME` exactly as defined in family files.
- Report which files were inspected.
- Extract additional relevant globals when they affect downstream behavior.

**Do not**
- Guess `_CORE_NAME` from architecture, derivative suffix, or core count.
- Guess `_SOC_NAME` instead of reading it.
- Overwrite authoritative family-script values with normalized helper values.

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm the family directory is justified from the requested SoC or family.
2. Verify `<family>_context.py` is read and `_CORE_NAME` / `_SOC_NAME` are
   extracted or traced.
3. Verify imported constants are followed to their definitions when needed.
4. Verify dispatcher validation checks both the core branch and the
   derivative-specific SoC branch when relevant.
5. Verify the returned values are verbatim family-script values.
6. Return the family directory, context file, authoritative values, additional
   relevant globals, validation status, and any fallback or remaining
   ambiguity.

## Out of scope

- Guessing family-script values.
- Rewriting authoritative values into helper-normalized forms.
- Replacing startup execution, GDB variant resolution, or flash workflows.
- Treating dispatcher validation as optional when downstream init behavior
  depends on it.

## See Also

- `references/authoring-procedure.md` - family mapping, extraction, tracing,
  fallback, and validation workflow.
- `references/examples.md` - example families, common pitfalls, and
  anti-patterns.
- Related skills: `s32debugger-resolve-gdb-variant`,
  `s32debugger-generate-gdb-config-file`,
  `s32debugger-connect-gdb-to-s32-debug-probe`,
  `s32debugger-lookup-for-soc-init-sequence`
