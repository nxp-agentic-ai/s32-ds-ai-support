---
name: s32debugger-convert-ltb-cmm-to-python
description: >
  Translate Lauterbach TRACE32 `.cmm` init sequences into Python suitable for
  later incorporation into an S32Debugger pipeline. Use this whenever the user
  wants a TRACE32 bring-up or init script converted to reusable Python,
  normalized into helpers such as `partition_init()` or `sram_init()`,
  compared against shipped S32Debugger family scripts, or optionally wrapped in
  a fuller connect/attach/load flow. Keep the translation family-neutral unless
  the CMM or the user explicitly confirms SoC identity.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: [s32debugger-lookup-for-soc-init-sequence]
  tags: [s32debugger, translation, trace32]
---

# S32Debugger Convert LTB CMM to Python

Translate a TRACE32 `.cmm` init sequence into Python that preserves hardware
bring-up intent and can later be integrated into an S32Debugger pipeline. This
skill defaults to init-sequence translation, not full standalone debugger
orchestration, and must stay family-neutral unless identity is explicit in the
CMM or explicitly confirmed by the user.

## When to use

Use this skill when:
- The user wants a Lauterbach TRACE32 `.cmm` init or bring-up flow converted
  into Python.
- The user wants reusable init helpers such as `partition_init()`,
  `sram_init()`, `core_init_sequence()`, `install_boot_stubs()`,
  `board_init()`, or `core_enable()` rather than a full debug wrapper.
- The user wants the translation compared with shipped S32Debugger family
  scripts for reference without assuming family identity from resemblance.
- The user wants a family-neutral translation artifact first and wrapper logic
  only if explicitly requested.

Do **not** use this skill for:
- CCS Tcl generation.
- Literal TRACE32/PRACTICE syntax preservation as the primary goal.
- Recreating TRACE32 UI layout behavior as a primary outcome.
- Forcing every conversion into a fully runnable standalone debug script when
  the user only asked for init translation.
- Using shipped family modules as a substitute for translating the provided
  CMM behavior.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.

### 2. Classify the translation target

```
Modes: A literal init | B normalized init | C family-aligned review |
       D full runnable standalone wrapper
Default: Mode A init-only translation unless the user explicitly asks for more
```

### 3. Extract behavior from the CMM before translating syntax

```
Capture: register writes, masks, waits, helper blocks, boot addresses,
         partition/core enablement, release-from-reset logic, comments
Separate: init behavior vs connect/attach vs load/run vs TRACE32 UI actions
Record:  what the CMM does not specify and what remains ambiguous
```

### 4. Keep the minimum conversion sequence inline

Use this order for the minimum safe conversion path:
1. classify the request into Mode A/B/C/D
2. extract explicit evidence from the CMM
3. separate pure init from connect/attach/load/run/UI behavior
4. inspect shared utilities and shipped examples before inventing anything
5. keep the result family-neutral unless identity is explicit
6. block only the wrapper layer when connection identity is missing
7. explicitly mark translated, normalized, omitted, optional, unresolved, and
   user-supplied parts in the final result

### 5. Preserve key ambiguity and utility rules inline

```
Prefer: direct shared utility calls when they clearly fit
Prefer: installed S32Debugger Python API syntax and usage examples over
        invented helper syntax
Avoid:  guessed family identity, thin forwarding wrappers, hidden assumptions,
        invented API syntax
Rule:   missing connection identity blocks wrapper generation, not init
        translation itself
Rule:   Mode D init_mc_me() may use only pre-connect-safe utilities
Rule:   if shipped <family>_init_sequence._prologue() covers pre-connect init,
        delegate to it rather than reimplementing it inline
Rule:   never invent syntax; always search the installed S32Debugger Python
        API and shipped examples for exact syntax and usage before emitting code
```

## Guardrails

**Scope**
- Treat init-sequence translation as the default product.
- Convert behavior, not TRACE32 syntax.
- Keep init logic separate from connect, attach, load, run, and UI behavior
  unless the user explicitly asks for a fuller wrapper.
- Use shipped family scripts for reference, style, comparison, and helper
  idioms only, never as proof of family identity.
- The default output is a reusable Python init module/helper set or other
  family-neutral translation artifact for later pipeline integration; detailed
  output-target and translated-target guidance live in
  `references/authoring-procedure.md`.

**Destructive actions**
- Default to translation artifacts and reusable helpers, not execution.
- Do not force a complete runnable wrapper unless the user requests it.
- Use only standard Python modules, `gdb` when needed, and imports from
  `S32Debugger/Debugger/scripts/utils` unless the user explicitly requests a
  different grounded structure.
- Do not import family modules into the final generated result by default.
- Do not replace real translation with family-module wrappers that merely
  import shipped scripts.

**Refuse-and-escalate**
- If the references have not been reviewed, stop and review them first.
- If SoC family, derivative, AP values, contexts, or target identity are not
  explicit, keep the translation family-neutral instead of guessing.
- If the user asks for a full runnable wrapper but connection identity is
  missing, continue translating init logic and mark the missing connection data
  as a blocker only for the wrapper layer.
- If width, endianness, reset semantics, helper choice, context-vs-bus
  identity, or optional waits are ambiguous, surface that ambiguity explicitly
  rather than inventing a family-specific answer.
- For Mode D, if pre-connect behavior cannot be grounded in installed
  S32Debugger Python API/examples, stop rather than emitting an invalid
  wrapper.

**Resource limits**
- Use this file as the compact operational contract.
- Use `references/authoring-procedure.md` as the canonical detailed workflow,
  mapping, ambiguity, output-target, and checklist source.
- Use `references/examples.md` as the canonical trigger/example/anti-pattern
  source.

**Secrets**
- Do not echo sensitive connection identities, proprietary memory maps, or
  board-specific secrets into generated examples unless the user explicitly
  provides and requests them.

**Utility-selection rules**
- Inspect shared utility modules before inventing raw low-level GDB access.
- Never invent syntax. Always search the installed S32Debugger Python API,
  shared utility modules, and shipped usage examples for exact syntax, call
  shape, parameter style, and sequencing before emitting code.
- Prefer direct shared utility calls where they already express the required
  hardware operation, and do not introduce thin local wrappers that only
  forward to existing shared helpers without adding domain meaning.
- A local helper is acceptable only when it captures a meaningful semantic
  operation from the CMM, such as `partition_init()`, `sram_init()`,
  `core_enable()`, or `install_boot_stubs()`.
- For Mode D, choose `mcme_init_utils` vs `mem_reg_utils` by whether the
  translated operation executes before or after
  `gta_lib.establish_connection()` has completed.
- `init_mc_me()` runs before the GDB/GTA session is fully established, so only
  pre-connect-safe utilities are allowed there. Use `mcme_init_utils` before
  or during `gta_lib.establish_connection()`, and `mem_reg_utils` only after it
  returns.
- `%LE` / `%BE` / width flags on `Data.Set` must map to the exact helper that
  preserves byte-order behavior; see `references/authoring-procedure.md` for
  the exact helper table.
- For AP-routed `mem_reg_utils` calls, the first argument is the CCS DAP
  context string and the second is the AP bus selector from the family init
  sequence. These are never interchangeable. Never use `"physical"` as the
  second argument for AP-routed operations.
- If shipped `<family>_init_sequence.py` already contains `_prologue()` that
  covers required pre-connect init, delegate to it rather than reimplementing
  it with the wrong utility class.
- If a translated helper uses `mcme_init_utils` and is later wrapped into a
  full runnable standalone script, it must be invoked from `init_mc_me()` / the
  pre-connect callback, not only from post-connect `board_init()` logic.

**Assumption control**
- Do not assume or hardcode any of the following unless they are explicit in
  the CMM or explicitly provided by the user: SoC family, derivative, CCS
  SoC/core context strings, AP selector values, target identity, core maps, or
  family-specific naming conventions.
- Missing connection identity blocks only connect/attach wrapper generation,
  not init-sequence translation itself.

## Translation modes

### Mode A - Literal init translation
Use when the user mainly wants the init sequence translated.

Characteristics:
- preserve the CMM ordering closely
- translate register writes, masked updates, polling loops, helper blocks, and
  low-level bring-up logic directly
- omit connect, attach, load, run, and UI logic unless explicitly requested
- keep family assumptions out of the result

### Mode B - Normalized init translation
Use when the user wants cleaner reusable Python for later pipeline
integration.

Characteristics:
- preserve the CMM intent while reorganizing it into reusable helpers
- use shared `Debugger/scripts/utils` helpers where they clearly fit
- refactor into functions such as `sram_init()`, `partition_init()`,
  `core_enable()`, or `install_boot_stubs()`
- remain family-neutral unless identity is explicitly confirmed

### Mode C - Family-aligned review
Use when the user wants comparison against shipped scripts.

Characteristics:
- inspect the nearest family script for reference only
- explain similarities, deltas, and possible normalization opportunities
- do not assume family identity merely from resemblance
- allow the user to confirm whether family-style normalization is desired

### Mode D - Full runnable standalone script
Use only when the user explicitly asks for connect/attach/load/run flow.

Characteristics:
- may include `setup()`, `connect()`, `board_init()`, `core_init()`, or
  `init_mc_me()`
- requires explicit user-provided connection identity when the CMM does not
  provide it
- remains secondary to the init translation itself
- must obey the pre-connect utility restrictions

## Validation loop

1. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
2. Confirm the request is classified as Mode A, B, C, or D.
3. Verify the CMM was inspected for explicit evidence.
4. Verify pure init behavior was separated from connect/attach/load/run/UI
   behavior.
5. Verify shared utility modules were considered before inventing raw or local
   helper layers.
6. Verify family neutrality is preserved unless identity is explicit in the CMM
   or confirmed by the user.
7. Verify missing connection identity is treated as non-blocking for init
   translation and blocking only for wrapper generation.
8. Verify Mode D keeps `init_mc_me()` restricted to pre-connect-safe utilities,
   delegates to `_prologue()` when applicable, and places mcme-based helpers in
   the pre-connect path.
9. Verify no API syntax, helper names, call patterns, or wrapper usage were
   invented; confirm they were grounded in the installed S32Debugger Python API
   or shipped examples.
10. Verify the generated result uses only standard Python, `gdb` when needed,
    and `S32Debugger/Debugger/scripts/utils` imports unless the user explicitly
    requested a different grounded structure.
11. Use the detailed checklist in `references/authoring-procedure.md` as the
    final lossless verification source.

## Out of scope

- Treating shipped family scripts as proof of SoC identity.
- Recreating TRACE32 UI layout behavior as a primary goal.
- Blocking init translation just because connection identity is incomplete.
- Emitting an invalid pre-connect wrapper that uses post-connect-only helpers.
- Importing family modules into the default generated result.

## See Also

- `references/authoring-procedure.md` - canonical detailed workflow, mapping
  guidance, ambiguity policy, output-target detail, and full checklist.
- `references/examples.md` - trigger examples, output examples, anti-patterns,
  and reminder-style checks.
- Related skills: `s32debugger-lookup-for-soc-init-sequence`,
  `s32debugger-generate-automation-script`
