# Examples and Anti-Patterns

## Typical triggers

Use this skill for prompts such as:
- translate this CMM init sequence into Python
- convert this Lauterbach init script for later S32Debugger pipeline use
- rewrite this TRACE32 bring-up sequence as reusable Python helpers
- compare this translated init against the shipped family script
- omit connect logic; I just want the init sequence in Python
- normalize this CMM init into reusable functions
- keep this translation family-neutral unless I confirm the family
- generate a full wrapper too, but only after translating the init logic

## Default outputs

Typical default outputs include:
- an init-only helper module
- a set of reusable Python functions
- a translation artifact for later pipeline integration
- a comparison-oriented translation draft

Common helper names include:
- `partition_init()`
- `sram_init()`
- `core_init_sequence()`
- `install_boot_stubs()`
- `board_init()`

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

## Mode cues

### Mode A - Literal init translation
Typical cues:
- translate this init sequence
- preserve the original order
- keep it close to the CMM
- I only want the init logic

Expected behavior:
- preserve ordering closely
- translate hardware behavior directly
- omit connect/attach/load/run/UI logic unless explicitly requested

### Mode B - Normalized init translation
Typical cues:
- normalize this into reusable functions
- refactor this bring-up into helpers
- make this suitable for later pipeline integration

Expected behavior:
- preserve intent while reorganizing into semantic helpers
- use direct shared utility calls when they clearly fit
- avoid thin forwarding wrappers

### Mode C - Family-aligned review
Typical cues:
- compare this against the shipped family script
- align this with the existing family style
- show me similarities and differences first

Expected behavior:
- inspect the nearest shipped family script for reference only
- report overlap, shared register blocks, sequence differences, and gaps
- do not treat resemblance as proof of family identity

### Mode D - Full runnable standalone wrapper
Typical cues:
- generate a runnable standalone script
- add connect/attach/load flow
- wrap this in setup/connect/board_init/core_init

Expected behavior:
- only generate wrapper/orchestration when explicitly requested
- require explicit user-provided connection identity if the CMM does not
  provide it
- keep the translated init logic as the primary artifact
- ensure `init_mc_me()` uses only pre-connect-safe utilities

## Practical mapping examples

Use these as intent-level hints:
- `Data.Set <addr> ...` usually maps to register write, masked update, memory
  fill, or boot-stub installation logic
- `Data.Set <addr> %LE %Long <value>` should map to
  `utils.write_mem32_le(...)`, not `utils.write_mem32(...)`
- `Data.Set <addr> %Long <value>` or `%BE %Long` should map to
  `utils.write_mem32(...)`, not `utils.write_mem32_le(...)`
- AP-routed `mem_reg_utils` calls use `(dap_context, ap_string, address, ... )`
  where the first argument is the CCS DAP context and the second is the APB/AHB
  bus selector from the family init script
- `Wait (Data.Long(...) & mask) == value` usually maps to a polling helper
- `GoSub <helper>` usually maps to a Python helper function
- `System.Mode.Attach` usually belongs to attach/connect logic, not init logic
- `Data.Load.Elf ...` and `Go <symbol>` usually belong to optional automation
- `Break`, `List.Auto`, `Register.View`, `Term.*`, and `WinCLEAR` usually map
  to omitted TRACE32 UI/PRACTICE behavior

## Common ambiguity cues

Explicitly call these out when present:
- `%Long` vs `%LE %Long`
- whether a `Data.Set` is full overwrite or masked update
- whether commented-out waits should stay omitted or become optional
- whether a boot-stub write is required or just defensive
- whether reset-related commands imply a broader debug prologue
- whether width, byte order, or helper choice is actually explicit
- whether missing target identity affects only the wrapper layer or the whole
  translation

## Good patterns

- translate init behavior even when target identity is incomplete
- separate init logic from attach/connect/load/run/UI behavior
- preserve meaningful ordering in Mode A
- normalize only when Mode B or user intent calls for it
- never invent syntax; search the installed S32Debugger Python API, shared
  utility modules, and shipped usage examples before emitting code
- use direct shared utility calls when they already express the operation
- create local helpers only when they add semantic meaning
- mark translated, normalized, omitted, optional, unresolved, and
  user-supplied parts explicitly
- use shipped family scripts for reference, style, comparison, and helper
  idioms only
- keep the default output family-neutral unless identity is explicit
- for Mode D, keep `init_mc_me()` limited to pre-connect-safe utilities only
- use only standard Python, `gdb` when needed, and
  `S32Debugger/Debugger/scripts/utils` imports unless a different grounded
  structure was explicitly requested

## Anti-patterns

- inferring family identity solely from resemblance
- requiring connection identity just to translate init logic
- forcing every conversion into a full standalone debug script
- importing family modules into the final generated result by default
- using shipped family modules instead of translating the provided CMM logic
- inventing AP values, contexts, derivatives, target identity, core maps, or
  API syntax
- silently normalizing away meaningful CMM ordering differences
- creating thin forwarding wrappers around existing shared utility calls
- using `mem_reg_utils` inside `init_mc_me()` before connection is established
- emitting a Mode D wrapper without grounding the pre-connect utility choice
- emitting Python that was not grounded in installed S32Debugger API syntax or
  shipped usage examples
- importing SoC-family modules such as `s32g2xx_*`, `s32g3xx_*`, `s32n55_*`,
  `s32k*_*`, or equivalent family packages into the default generated result
- translating `%LE %Long` with `utils.write_mem32(...)` instead of
  `utils.write_mem32_le(...)`
- swapping the DAP context argument with the APB/AHB bus selector in an
  AP-routed `mem_reg_utils` call
- using `"physical"` as the second argument for an AP-routed memory-space
  access that should use a family AP selector

## Assumption-control reminders

Do not assume or hardcode any of the following unless explicit in the CMM or
provided by the user:
- SoC family
- derivative
- CCS SoC context strings
- CCS core context strings
- AP selector values
- target identity
- core maps
- family-specific naming conventions

## Response-shape reminder

A strong response usually includes:
1. Evidence extracted from the CMM
2. Selected translation mode
3. Classification summary
4. Utility/reference baseline used
5. Generated Python result
6. Ambiguities and follow-up notes

## Checklist reminder

Before finishing, verify:
- no API syntax was invented
- no thin forwarding wrappers were introduced without semantic value
- family scripts were used only for reference, not identity inference
- missing connection identity blocked only wrapper generation, not init
  translation
- ambiguities were called out explicitly
- Mode D kept `init_mc_me()` restricted to pre-connect-safe utilities
