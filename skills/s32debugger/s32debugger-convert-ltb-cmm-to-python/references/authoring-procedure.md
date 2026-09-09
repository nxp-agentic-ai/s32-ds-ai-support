# Authoring Procedure

## Translation modes

Choose exactly one primary mode for the response:
- Mode A - Literal init translation
- Mode B - Normalized init translation
- Mode C - Family-aligned review
- Mode D - Full runnable standalone wrapper

Default to Mode A init-only translation unless the user explicitly asks for
normalization, comparison, or a runnable wrapper.

Mode discipline rules:
- Do not silently drift from Mode A, B, or C into Mode D.
- Do not emit runnable connect/attach/load orchestration unless the user asked
  for it.
- Do not let missing connection identity block Mode A, B, or C output.
- If the user asks for both translation and wrapper generation, translation
  still comes first and wrapper generation is secondary.

## Output target

Treat the primary output target as a reusable Python init module or helper set
that can later be integrated into an S32Debugger pipeline.

Common outputs include:
- `partition_init()`
- `sram_init()`
- `core_init_sequence()`
- `install_boot_stubs()`
- `board_init()`
- small reusable helpers that preserve the original init intent

Optional outputs may include:
- a standalone wrapper around the translated init logic
- a connect/attach layer
- automation helpers for ELF load/run/breakpoints
- a comparison report against shipped family scripts

Do not treat those wrapper or automation outputs as mandatory unless the user
explicitly requests them.

## Workflow

Follow this order.

1. Inspect the CMM for explicit evidence.
   Extract only what the CMM explicitly states:
   - register addresses, values, masks
   - polling conditions and waits
   - helper blocks, labels, and repeated sequences
   - boot addresses and release-from-reset logic
   - explicit SoC/core names if present
   - comments that clarify bitfield or sequencing intent
2. Record what the CMM does not specify.
   Examples:
   - missing SoC family confirmation
   - missing derivative or core map
   - missing AP/context identity
   - unclear width or endianness intent
   - uncertain reset semantics
3. Separate content into buckets:
   - pure init behavior
   - attach/connect behavior
   - load/run/debug automation
   - TRACE32-only UI/PRACTICE behavior
   - ambiguous or unresolved items
4. Normalize the sequence into semantic operations before writing Python.
   Examples:
   - assert reset
   - clear reset
   - write register
   - masked set or clear bits
   - wait until ready
   - initialize SRAM/TCM
   - enable partition
   - write boot address
   - install boot stub
   - release core reset
5. Inspect shared utility modules before inventing raw low-level GDB access.
   - Never invent syntax.
   - Always search the installed S32Debugger Python API, shared utility
     modules, and shipped usage examples for exact syntax, call shape,
     parameter style, and sequencing before emitting code.
6. Inspect shipped family scripts for reference, style, comparison, and helper
   idioms only.
7. Generate Python that preserves hardware intent.
8. Mark each construct as one of:
   - translated directly
   - normalized into a semantic helper
   - omitted as TRACE32-only UI/PRACTICE behavior
   - moved to optional automation
   - blocked on missing user-supplied identity for wrapper generation
   - unresolved due to ambiguity

## Common translation targets

Typical translated init behavior includes:
- SRAM/TCM initialization
- reset-related register programming
- MC_ME / RGM / RDC programming
- partition enablement
- boot address programming
- core release from reset
- polling loops and readiness checks
- boot stub installation
- other low-level bring-up logic explicitly present in the CMM

## Non-negotiable rules

- Treat init-sequence translation as the default and primary product.
- Convert behavior, not TRACE32 syntax.
- Preserve family neutrality unless identity is explicit in the CMM or
  explicitly confirmed by the user.
- Use shipped family scripts for reference, style, comparison, and helper
  idioms only, never as proof of family identity.
- Missing connection identity blocks only wrapper generation, not init
  translation itself.
- Explicitly call out ambiguity instead of inventing a family-specific answer.

## Utility-selection rules

Inspect shared utility modules before inventing raw low-level GDB access,
local access helpers, thin forwarding wrappers, or API syntax.

Never invent syntax. Always search the installed S32Debugger Python API,
shared utility modules, and shipped usage examples for exact syntax, call
shape, parameter style, and sequencing before emitting code.

Prefer shared utility modules such as:
- `mcme_init_utils`
- `mem_reg_utils`
- `gta_lib`
- `check_global_variables`
- `errors`

Prefer direct shared utility calls where they already express the required
hardware operation.
Prefer direct calls such as:
- `mcme.write_reg32(...)`
- `mcme.set_reg(...)`
- `mcme.check_reg(...)`
- `utils.write_mem32(...)`
- `utils.write_mem32_le(...)`
- `utils.read_mem32(...)`

Do not create thin forwarding wrappers like `_write32()`, `_read32()`, or
`_check()` when an existing helper already expresses the same action.

`Data.Set` width/endianness flags must map to the exact helper that preserves
byte-order behavior:

| CMM flags                           | Width  | Byte order    | S32Debugger helper          |
|-------------------------------------|--------|---------------|-----------------------------|
| `%LE %Long`                         | 32-bit | little-endian | `utils.write_mem32_le(...)` |
| `%BE %Long` or `%Long` (default BE) | 32-bit | big-endian    | `utils.write_mem32(...)`    |
| `%LE %Word`                         | 16-bit | little-endian | `utils.write_mem16_le(...)` |
| `%BE %Word` or `%Word`              | 16-bit | big-endian    | `utils.write_mem16(...)`    |
| `%LE %Byte` or `%Byte`              | 8-bit  | n/a           | `utils.write_mem8(...)`     |

Key facts:
- `write_mem32_le()` calls `Swap32()` internally - it does apply a byte swap.
- `write_mem32()` does not apply a byte swap.
- Using `write_mem32()` for `%LE %Long` silently produces wrong byte order.
- Using `write_mem32_le()` for `%BE %Long` silently produces wrong byte order.

For AP-routed `mem_reg_utils` helpers, use this fixed argument convention:

```python
utils.write_mem32_le(dap_context, ap_string, address, value)
utils.write_mem32(dap_context, ap_string, address, value)
utils.read_mem32(dap_context, ap_string, address)
```

Where:
- `dap_context` is the CCS DAP session context string from
  `<family>_context.py`, typically `context.CORE_DAP_CONTEXT`. It resolves to a
  string such as `":ccs:<SoC>:DAP#0"`. It is a CCS session string, not a bus
  identifier.
- `ap_string` is the AP bus identifier used to route the access. It can be any
  bus type - APB (`"apb4"`, `"apb_mem"`), AHB (`"ahb"`, `"ahb_m7"`), or other
  family-specific port names, taken from the AP dictionaries defined in
  `<family>_init_sequence.py` (for example `AP_DICT["PORT"]`). It is a bus
  identifier string, not a context string.
- These two arguments are never interchangeable. Swapping them produces a
  silent wrong-target access with no Python error.
- Never pass a bus identifier as the first argument.
- Never use `"physical"` as the second argument for AP-routed operations.

Canonical annotated pattern from shipped family scripts
(`<family>_init_sequence.py`):

```python
dap_ctx = context.CORE_DAP_CONTEXT               # CCS DAP context string
utils.write_mem32_le(dap_ctx, AP_DICT["PORT"], base_addr, value)
#                    ^^^^^^^  ^^^^^^^^^^^^^^^
#                    context  bus identifier (from AP dict in family init_sequence)
```

A local helper is acceptable only when it adds semantic meaning from the CMM,
for example:
- `partition_init()`
- `sram_init()`
- `core_enable()`
- `install_boot_stubs()`
- `core_init_sequence()`

The generated Python should use only:
- standard Python modules
- `gdb` when needed
- imports from `S32Debugger/Debugger/scripts/utils`

Do not import family modules into the default generated result.
Do not use family-module imports as a substitute for translating the provided
CMM logic.
The generated Python should not import SoC-family modules such as:
- `s32g2xx_*`
- `s32g3xx_*`
- `s32n55_*`
- `s32k*_*`
- or equivalent family packages

## Pre-connect rule for Mode D

When generating a full runnable wrapper:
- `init_mc_me()` runs before full GDB/GTA session establishment
- only pre-connect-safe utilities are allowed there
- `mcme_init_utils` is allowed there because it is pre-connect-safe
- `mem_reg_utils` is not allowed there because it requires an active GDB
  session

If a shipped `<family>_init_sequence.py` already contains `_prologue()` that
covers the required pre-connect logic (debug-enable, halt groups, etc.) via
`mcme_init_utils`, `init_mc_me()` must delegate to it instead of reimplementing
the same logic inline with the wrong utility class:

```python
import <family>_init_sequence as init

def init_mc_me():
    init._prologue()
```

When a translated `mcme_init_utils` helper is wrapped into a full runnable
standalone script, it must be invoked from `init_mc_me()` before
`monitor ctx connect`. Do not generate this incorrect shape:

```python
def board_init():
    if not isAttached:
        connect()
    translated_cmm_init_using_mcme()   # WRONG: runs after monitor ctx connect
```

Use this pattern instead:

```python
def init_mc_me():
    translated_cmm_init_using_mcme()   # CORRECT: runs before connect

def connect():
    gta_lib.establish_connection(..., init_mc_me, ...).unwrap()
```

## Assumption control

Do not assume or hardcode any of the following unless they are explicit in the
CMM or explicitly provided by the user:
- SoC family
- derivative
- CCS SoC context strings
- CCS core context strings
- AP selector values
- target identity
- core maps
- family-specific naming conventions

Missing connection identity blocks only wrapper generation, not init
translation itself.

## Pipeline integration guidance

When the user appears to want a translation artifact for later integration,
prefer output that is modular, reusable, easy to import, low on hidden global
state, and parameterized where useful.

Preferred style:
- small helpers such as `sram_init()`, `partition_init()`, `core_enable()`
- explicit parameters such as `timeout`, `opmode`, or `wait_for_completion`
- comments preserving original CMM bitfield intent
- optional entry-point wrappers such as `run_init()` only when helpful

Avoid forcing a complete standalone script shape when the user mainly wants a
reusable init translation.

## Practical TRACE32-to-Python mapping hints

Use these as intent-level hints, not mandatory literal rewrites.

- `Data.Set <addr> ...` -> register write, masked update, memory fill, or
  boot-stub install helper depending on surrounding evidence
- `Wait (Data.Long(...) & mask) == value` -> poll helper such as
  `mcme.check_reg(...)` when grounded in the installed API or shipped examples
- `GoSub <helper>` -> Python helper function preserving semantic grouping
- `System.CPU ...` -> metadata or user-facing note unless it directly affects
  runtime translation
- `System.Mode Prepare` -> often orchestration-adjacent; do not force an init
  equivalent unless clearly needed
- `System.Mode.Attach` -> attach/connect layer, not init by default
- `Data.Load.Elf ...` -> automation layer, optional unless explicitly requested
- `Go <symbol>` -> automation layer, optional unless explicitly requested
- `Break`, `List.Auto`, `Register.View`, `Term.*`, `WinCLEAR` -> usually omit
  and label as TRACE32 UI/PRACTICE behavior

## Ambiguity policy

Explicitly call out, rather than silently resolve:
- width or endianness uncertainty
- `%Long` vs `%LE %Long`
- 32-bit vs 64-bit helper choice
- full overwrite vs masked update uncertainty
- optional or commented-out wait behavior
- reset semantics
- whether a boot-stub write is required or merely defensive
- whether a helper should use a shared utility directly or a semantic local
  helper
- whether a reset-related command implies a broader debug prologue
- whether the CMM line makes `%LE` / `%BE` explicit enough to choose an exact
  `mem_reg_utils` helper
- whether a string in the shipped Python is a CCS DAP context or an AP bus
  selector for APB/AHB memory-space routing

When possible:
- preserve literal behavior in Mode A
- normalize only when the selected mode calls for it
- expose alternate interpretations as comments or optional parameters
- do not invent family-specific semantics to resolve ambiguity

## Output expectations

A good result should contain:
1. Evidence extracted from the CMM
2. Selected translation mode
3. Classification summary
4. Utility/reference baseline used
5. Generated Python result
6. Ambiguities and follow-up notes

If the user asked for a full wrapper and connection identity is missing:
- still return the init translation artifact
- explicitly identify the missing connection data
- state that the wrapper layer is blocked pending those values

## Minimal conversion checklist

- [ ] The provided CMM init logic was inspected for explicit evidence.
- [ ] The request was classified into Mode A, B, C, or D.
- [ ] Pure init behavior was separated from connect/attach/load/run/UI
      behavior.
- [ ] Shared utility modules were checked before inventing local helpers or API
      syntax.
- [ ] Shared utility calls were emitted directly whenever they already matched
      the required operation.
- [ ] No thin forwarding wrappers were introduced around existing shared helper
      calls.
- [ ] No API syntax, helper names, call patterns, or wrapper usage were
      invented.
- [ ] Family scripts were used only for reference, style, comparison, and
      helper idioms, not identity inference.
- [ ] Missing connection identity was treated as non-blocking for init
      translation.
- [ ] Ambiguities were called out explicitly.
- [ ] No SoC family, derivative, AP/context identity, or core map was assumed
      unless explicit in the CMM or provided by the user.
- [ ] For Mode D, `init_mc_me()` used only pre-connect-safe utilities.
- [ ] For Mode D, if `<family>_init_sequence._prologue()` existed and covered
      pre-connect init, `init_mc_me()` delegated to it rather than
      reimplementing the logic inline.
- [ ] For Mode D, any translated helper using `mcme_init_utils` is invoked
      from `init_mc_me()` before `gta_lib.establish_connection()` completes,
      not only from post-connect `board_init()` code.
- [ ] For Mode D, the wrapper does not defer required mcme-based init until
      after `connect()`.
