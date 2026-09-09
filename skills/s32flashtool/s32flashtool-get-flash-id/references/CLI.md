# S32FlashTool Get Flash ID - CLI flow

Use this flow when:
- the user asked for CLI or a command line workflow
- the user asked for a command preview
- no GUI behavior was requested and a CLI command is the best fit

## Operation mapping (CLI)

**User intent:** show identification data of the flash chip

- Build action: `cli_build_fid` (pinned operation `fid_cli`)
- Execute action: `cli_execute`
- CLI meaning: `-fid` = show identification data of flash chip
- Destructive: **no**; confirmation not required

## Action flow

1. `search_actions("flash id")` to discover `cli_build_fid` and its input schema.
2. `execute_action("cli_build_fid", { sft_folder, cli_request })` -- returns the
   ready `command` string (nothing runs on the target yet).
3. `execute_action("cli_execute", { sft_folder, command })` to run it.

## Input schema (cli_request.input for fid)

Required:
- `target`
- `interface` (`uart` | `can` | `ethernet`)
- `transport` (object matching the selected interface)
- `algorithm`

Optional:
- shared serial-boot options.

## Example: build the flash-id command
```json
{
  "action": "cli_build_fid",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.2_260522",
    "cli_request": {
      "operation": "fid_cli",
      "input": {
        "target": "C:/NXP/S32FlashTool_2.4.2_260522/targets/S32N5x.bin",
        "algorithm": "C:/NXP/.../flash/S28HS01GT.bin",
        "interface": "uart",
        "transport": { "kind": "uart", "device": "COM15", "driver": "ftdi" }
      }
    }
  }
}
```

## Example: execute the built command
```json
{
  "action": "cli_execute",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.2_260522",
    "command": "<command string returned by cli_build_fid>"
  }
}
```

## Command inspection
The `cli_build_fid` action returns the exact command line without touching the
target, so it doubles as the command-inspection/preview step. Use it whenever
the user wants to see the exact CLI command before execution.
