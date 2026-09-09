# Authoring Procedure

## Preconditions

1. Verify GTA was started before GDB.
2. Verify GDB with Python support is running.
3. Verify probe/session connection is already established.
4. Verify `s32flash.py` is available.
5. Verify a matching ELF is available for `symbol-file`.

## Ordered same-session workflow

1. Source the flash programmer:
   `source "<S32Debugger>/Debugger/scripts/gdb_extensions/flash/s32flash.py"`
2. Configure the required flash-programmer parameters using names and kwargs
   from `s32flash.py`.
3. Run the write/program operation and wait for completion.
4. Continue into debug-from-flash in this exact order:
   1. `py reset()`
   2. `flushregs`
   3. `set $pc=$PC`
   4. `symbol-file "<matching-elf>"`
5. Keep the session open for follow-up debug actions.

## Do-not-break ordering rules

1. Do not insert `fl_close` before the post-flash debug continuation sequence.
2. Do not replace the post-flash symbol step with `load`.
3. Do not reorder `py reset()`, `flushregs`, `set $pc=$PC`, and
   `symbol-file`.
4. Do not continue without a matching ELF/symbol file.

## Key rule

Do not call `fl_close` here. That is the flash-only end state, not the
post-flash debug continuation state.

## Interpretation

1. `py reset()` resets the core to begin from the flashed image.
2. `flushregs` refreshes GDB register cache.
3. `set $pc=$PC` repositions the current PC from reset-vector state.
4. `symbol-file` restores symbolic debug context without rewriting memory.
5. The session remaining open is part of the success condition, not an optional
   cosmetic detail.
