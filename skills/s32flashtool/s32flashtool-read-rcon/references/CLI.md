# S32FlashTool Read RCON/EEPROM - CLI flow

Use this flow when:
- the user asked for CLI or a command line workflow
- the user asked for a command preview
- no GUI behavior was requested and a CLI command is the best fit

## Operation mapping (CLI)

**User intent:** read the standard boot configuration (RCON/EEPROM)

- Build action: `cli_build_fread` (pinned operation `fread_cli`)
- Execute action: `cli_execute`
- Required algorithm type: `RCON.bin`
- Destructive: **no**; confirmation not required

## Action flow

1. `search_actions("read flash")` to discover `cli_build_fread` and its input schema.
2. `execute_action("cli_build_fread", { sft_folder, cli_request })` -- returns the
   ready `command` string (nothing runs on the target yet).
3. `execute_action("cli_execute", { sft_folder, command })` to run it.

## Input schema (cli_request.input for fread)

Required:
- `target`
- `interface` (`uart` | `can` | `ethernet`)
- `transport` (object matching the selected interface)
- `algorithm` (typically `RCON.bin`)
- `addr`
- `size`

Optional:
- `binary_output`, `file`, and shared serial-boot options.

## Example: build RCON read command (read to output)
```json
{
  "action": "cli_build_fread",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "cli_request": {
      "operation": "fread_cli",
      "input": {
        "target": "C:/NXP/.../targets/S32G2xx.bin",
        "algorithm": "C:/NXP/.../flash/RCON.bin",
        "interface": "uart",
        "transport": { "kind": "uart", "device": "COM3", "driver": "ftdi" },
        "addr": "0x0",
        "size": "0x18",
        "binary_output": false
      }
    }
  }
}
```

## Example: build RCON read command (read to file)
```json
{
  "action": "cli_build_fread",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "cli_request": {
      "operation": "fread_cli",
      "input": {
        "target": "C:/NXP/.../targets/S32G2xx.bin",
        "algorithm": "C:/NXP/.../flash/RCON.bin",
        "interface": "uart",
        "transport": { "kind": "uart", "device": "COM3", "driver": "ftdi" },
        "addr": "0x0",
        "size": "0x18",
        "binary_output": true,
        "file": "C:/Users/username/Downloads/rcon_dump.bin"
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
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "command": "<command string returned by cli_build_fread>"
  }
}
```

## Command inspection
The `cli_build_fread` action returns the exact command line without touching the
target, so it doubles as the command-inspection/preview step. Use it whenever
the user wants to see the exact CLI command before execution.
