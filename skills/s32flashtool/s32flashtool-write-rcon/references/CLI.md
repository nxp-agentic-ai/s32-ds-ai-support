# S32FlashTool Write RCON/EEPROM - CLI flow

Use this flow when:
- the user asked for CLI or a command line workflow
- the user asked for a command preview
- no GUI behavior was requested and a CLI command is the best fit

## Operation mapping (CLI)

**User intent:** write / program a hex value into the standard boot configuration (RCON/EEPROM)

- Build action: `cli_build_fprogram` (pinned operation `fprogram_cli`)
- Execute action: `cli_execute`
- RCON algorithm: normally `RCON.bin`
- Destructive: **yes**; confirmation required before executing the built command

## Action flow

1. `search_actions("program flash")` to discover `cli_build_fprogram` and its input schema.
2. `execute_action("cli_build_fprogram", { sft_folder, cli_request })` -- returns the
   ready `command` string (nothing runs on the target yet; this is the preview).
3. Show the built `command` to the user and obtain explicit confirmation.
4. `execute_action("cli_execute", { sft_folder, command })` to run it.

## Input schema (cli_request.input for fprogram)

Required:
- `target`
- `interface` (`uart` | `can` | `ethernet`)
- `transport` (object matching the selected interface)
- `algorithm` (typically `RCON.bin`)
- `addr`
- exactly one of `file` or `hex_data`

For an RCON hex write, prefer `hex_data` (ASCII hex string starting with `0x`,
even number of hex digits). Optional: `size`, `partition`, `noverify`.

## Example: build the RCON write command (preview)
```json
{
  "action": "cli_build_fprogram",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "cli_request": {
      "operation": "fprogram_cli",
      "input": {
        "target": "C:/NXP/.../targets/S32N5x.bin",
        "algorithm": "C:/NXP/.../flash/RCON.bin",
        "interface": "uart",
        "transport": { "kind": "uart", "device": "COM15", "driver": "ftdi" },
        "addr": "0x0",
        "hex_data": "0x00010203"
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
    "command": "<command string returned by cli_build_fprogram>"
  }
}
```

## Command inspection
The `cli_build_fprogram` action returns the exact command line without touching
the target, so it doubles as the command-inspection/preview step. Use it
whenever the user wants to see the exact CLI command before execution, and only
call `cli_execute` once they approve.
