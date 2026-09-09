# Authoring Procedure

## Workflow

1. Identify the family directory from the SoC or family hint.
2. Open `<family>_context.py`.
3. Extract `_CORE_NAME` and `_SOC_NAME`.
4. Trace imported constants when the values are indirect.
5. Inspect `<family>_init_sequence.py` and validate:
   - `_CORE_NAME` matches a top-level core-name branch
   - `_SOC_NAME` satisfies derivative-specific branch logic when relevant
6. Fall back to `<family>_cores.py` only when `_context.py` is missing or
   incomplete.
7. Return the authoritative values verbatim with validation status.

## Additional relevant globals

When they matter downstream, also extract values such as:
- `_RESET_DELAY`
- `_GDB_SERVER_PORT`
- security or lifecycle-related globals

## Fallback rules

- use `<family>_cores.py` only as a fallback source for canonical core strings
- if family mapping is uncertain, stop at the closest justified candidate
- if dispatcher validation cannot be completed, say so explicitly
