# Authoring Procedure

## Preconditions

- GTA started before GDB
- GDB with Python support is running
- probe/session connection is already established
- `s32flash.py` is available
- a valid bareboard init script path is available

## Workflow

1. Source the flash programmer:
   `source "<S32Debugger>/Debugger/scripts/gdb_extensions/flash/s32flash.py"`
2. Read required parameter names from `check_fp_global_parameters()` and
   `setup()` in `s32flash.py`.
3. Configure the requested operation using a full absolute bareboard init path.
4. Run the requested flash action.
5. End with `fl_close`.

## Init script rules

- use a full absolute path
- use a bareboard script
- do not use attach scripts

## Key rule

`fl_close` is the correct flash-only end state. It closes the flash-programmer
session cleanly and resets the board. Do not replace it with `disconnect`,
`quit`, or partial manual cleanup.
