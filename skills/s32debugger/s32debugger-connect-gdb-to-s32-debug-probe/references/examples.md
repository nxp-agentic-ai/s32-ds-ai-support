# Examples and Checks

## Typical triggers

- show me the raw GDB CLI steps to connect to the debug probe
- which init script should I source for attach vs bareboard
- what globals do I need before `board_init()` and `core_init()`
- how do I connect GDB directly to an S32 Debug Probe
- when should I use `load` and when should I use `symbol-file`

## Example commands

Windows paths:
```gdb
py _PROBE_IP = "s32dbg:192.168.10.5"
py _SOC_NAME = "S32G274A"
py _CORE_NAME = "M7_0"
source "C:/NXP/S32DBG.3.6.8/S32Debugger/Debugger/scripts/s32g2xx/s32g2xx_generic_bareboard.py"
py board_init()
py core_init()
load "C:/workspace/my_project/Debug/my_project.elf"
symbol-file "C:/workspace/my_project/Debug/my_project.elf"
```

Linux paths (same flow; only the install/workspace paths differ):
```gdb
py _PROBE_IP = "s32dbg:192.168.10.5"
py _SOC_NAME = "S32G274A"
py _CORE_NAME = "M7_0"
source "/home/user/NXP/S32DBG.3.6.10/S32Debugger/Debugger/scripts/s32g2xx/s32g2xx_generic_bareboard.py"
py board_init()
py core_init()
load "/home/user/workspace/my_project/Debug/my_project.elf"
symbol-file "/home/user/workspace/my_project/Debug/my_project.elf"
```

## Anti-patterns

- sourcing an init script before mandatory globals are set
- guessing `_SOC_NAME` or `_CORE_NAME`
- calling `board_init()` more than once in multicore
- using `load` in attach scenarios
- using GDB `load` for physical flash programming
- treating this low-level flow as a replacement for higher-level session skills
