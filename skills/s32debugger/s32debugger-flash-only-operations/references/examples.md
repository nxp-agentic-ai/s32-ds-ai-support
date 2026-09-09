# Examples and Anti-Patterns

## Typical triggers

- flash this binary and stop
- program this ELF to flash only
- erase and verify flash
- dump the flash contents
- show flash info and close the session afterward

## Examples

Use the `s32flash.py` shipped with your installation. On Windows the paths
look like `C:/NXP/S32DBG.3.6.8/.../s32flash.py`; on Linux like
`/home/user/NXP/S32DBG.3.6.10/.../s32flash.py`.

```gdb
source "<install>/S32Debugger/Debugger/scripts/s32flash.py"
# configure parameters
# run binary-write command
fl_close
```

```gdb
source "<install>/S32Debugger/Debugger/scripts/s32flash.py"
# configure parameters
# run dump/read command
fl_close
```

## Anti-patterns

- skipping `fl_close`
- continuing into `py reset()` / `flushregs` / `set $pc=$PC`
- using attach scripts as flash init scripts
- guessing parameter names instead of reading `s32flash.py`
- guessing flash-only vs debug-from-flash when the request is ambiguous
