# S32FlashTool Read MCU ID - CLI flow

Use this flow when:
- the user asked for CLI or a command line workflow
- the user asked for a command preview
- no GUI behavior was requested (there is no GUI/RPC flow for MCUID)

## Operation mapping (CLI)

**User intent:** read the MCU identification from the device

- Build action: `cli_build_mcuid` (pinned operation `mcuid_cli`)
- Execute action: `cli_execute`
- Algorithm: **not used** (do not pass one)
- Destructive: **no**; confirmation not required

## Action flow

1. `search_actions("mcu id")` to discover `cli_build_mcuid` and its input schema.
2. `execute_action("cli_build_mcuid", { sft_folder, cli_request })` -- returns the
   ready `command` string (nothing runs on the target yet).
3. `execute_action("cli_execute", { sft_folder, command })` to run it.

## Input schema (cli_request.input for mcuid)

Required:
- `target`
- `interface` (`uart` | `can` | `ethernet`)
- `transport` (object matching the selected interface)

Do not pass `algorithm`, `addr`, or `size` -- MCU ID reading does not consume a
flash algorithm.

## Example: build the mcuid command
```json
{
  "action": "cli_build_mcuid",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.2",
    "cli_request": {
      "operation": "mcuid_cli",
      "input": {
        "target": "C:/NXP/S32FlashTool_2.4.2/targets/S32N5x.bin",
        "interface": "uart",
        "transport": { "kind": "uart", "device": "COM31" }
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
    "sft_folder": "C:/NXP/S32FlashTool_2.4.2",
    "command": "<command string returned by cli_build_mcuid>"
  }
}
```

## Command inspection
The `cli_build_mcuid` action returns the exact command line without touching the
target, so it doubles as the command-inspection/preview step. Use it whenever
the user wants to see the exact CLI command before execution.
