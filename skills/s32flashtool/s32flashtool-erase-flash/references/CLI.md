# S32FlashTool Erase Flash - CLI flow

Use this flow when:
- the user asked for CLI or a command line workflow
- the user asked for a command preview
- no GUI behavior was requested and CLI is the best fit

## Operation mapping (CLI)

**User intent:** erase a block of flash or a flash memory range

- Build action: `cli_build_ferase` (pinned operation `ferase_cli`)
- Execute action: `cli_execute`
- Destructive: **yes**; confirmation required before executing the built command

## Action flow

1. `search_actions("erase flash")` to discover `cli_build_ferase` and its input schema.
2. `execute_action("cli_build_ferase", { sft_folder, cli_request })` -- returns the
   ready `command` string (nothing runs on the target yet; this is the preview).
3. Show the built `command` and the exact range to the user, obtain explicit confirmation.
4. `execute_action("cli_execute", { sft_folder, command })` to run it.

## Input schema (cli_request.input for ferase)

Required:
- `target`
- `interface` (`uart` | `can` | `ethernet`)
- `transport` (object matching the selected interface)
- `algorithm`
- `addr`

Optional:
- `size` (when erasing a range), `file`, and shared serial-boot options.

## Preview-first rule
For CLI erase, preview is the safe default. Build the command first, show it and
the exact range, then execute only after explicit user approval.

## Example: build erase command (preview)
```json
{
  "action": "cli_build_ferase",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "cli_request": {
      "operation": "ferase_cli",
      "input": {
        "target": "C:/NXP/.../targets/S32N5x.bin",
        "algorithm": "C:/NXP/.../flash/S28HS01GT.bin",
        "interface": "uart",
        "transport": { "kind": "uart", "device": "COM15", "driver": "ftdi" },
        "addr": "0x0",
        "size": "0x100"
      }
    }
  }
}
```

## Example: execute the built command after confirmation
```json
{
  "action": "cli_execute",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "command": "<command string returned by cli_build_ferase>"
  }
}
```

## Command inspection
The `cli_build_ferase` action returns the exact command line without touching the
target, so it doubles as the command-inspection/preview step. Use it whenever
the user wants to see the exact CLI command before execution, and only call
`cli_execute` once they approve.
