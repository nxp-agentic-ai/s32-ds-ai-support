# Examples and Anti-Patterns

## Typical triggers

- program this image and then debug from flash
- flash this ELF and keep the same GDB session alive
- write the image, reset, load symbols, and continue debugging
- after flashing, continue with symbolic debug in the same session

## Example

Use the `s32flash.py` shipped with your installation. On Windows the paths
look like `C:/NXP/S32DBG.3.6.8/.../s32flash.py`; on Linux like
`/home/user/NXP/S32DBG.3.6.10/.../s32flash.py`.

```gdb
source "<install>/S32Debugger/Debugger/scripts/s32flash.py"
# configure parameters for ELF flash
# run flash write command
py reset()
flushregs
set $pc=$PC
symbol-file "<workspace>/my_project/Debug/my_project.elf"
```

## Anti-patterns

- using this for generic read, erase, verify, dump, or flash-only operations
- ending immediately with `fl_close` when the user wants same-session debug
- using `load` instead of `symbol-file` after flashing
- proceeding without a matching ELF/symbol file
- guessing flash-only vs debug-from-flash when the request is ambiguous
