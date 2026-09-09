# Authoring Procedure

## Workflow

1. Resolve the family directory under:
   `<install>/S32Debugger/Debugger/scripts/<family>`
2. Inspect `<family>_generic_bareboard.py` first.
   - confirm import of the init-sequence module when present
   - confirm the init entry path used by connect/board/core init logic
3. Inspect `<family>_init_sequence.py`.
   - identify `init_sequence_by_core_name(...)` when present
   - identify exported public entry points if the family uses another model
   - identify helper functions such as `_prologue()`, `_common()`,
     core-specific helpers, partition helpers, SRAM/TCM helpers, and SoC
     branches
4. Inspect related family files when needed.
   - `<family>_cores.py`
   - `<family>_context.py`
   - `<family>_generic_bareboard_all_cores.py`
   - `<family>_attach.py`
5. Explain the sequence in operations, not only filenames.
6. If adapting, copy the nearest helper from the same family and change only
   required register writes, delays, AP selections, or boot flow.
7. Preserve dispatcher compatibility.

## Common pattern

Many families follow this shape:
- `<family>_generic_bareboard.py` imports `<family>_init_sequence as init`
- `init_mc_me()` calls `init.init_sequence_by_core_name(_CORE_NAME, _SOC_NAME, ... )`
- `connect()` passes that path into the connection flow
- `board_init()` / `core_init()` rely on the same bring-up path

Always verify the actual local files before assuming the pattern.

## Adaptation rules

- preserve family helper/API style
- preserve comments and naming style when practical
- update dispatcher logic when adding a new helper branch
- explain why any new register writes or delays differ from the baseline
