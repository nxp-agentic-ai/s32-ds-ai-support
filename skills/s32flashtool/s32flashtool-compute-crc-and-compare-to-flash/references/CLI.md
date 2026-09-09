# S32FlashTool Compute CRC and Compare to Flash - CLI flow

Use this flow when:
- the user asked for CLI or a command line workflow
- the user asked for a command preview
- no GUI behavior was requested and a CLI command is the best fit

## Operation mapping (CLI)

**User intent:** compute CRC32 over a flash region and compare it to a file

- Build action: `cli_build_fcrc` (pinned operation `fcrc_cli`)
- Execute action: `cli_execute`
- Destructive: **no**; confirmation not required

## Action flow

1. `search_actions("crc flash")` to discover `cli_build_fcrc` and its input schema.
2. `execute_action("cli_build_fcrc", { sft_folder, cli_request })` -- returns the
   ready `command` string (nothing runs on the target yet).
3. `execute_action("cli_execute", { sft_folder, command })` to run it.

## Input schema (cli_request.input for fcrc)

Required:
- `target`
- `interface` (`uart` | `can` | `ethernet`)
- `transport` (object matching the selected interface)
- `algorithm`
- `addr`
- `size`

Optional:
- `file` (binary file to compare against), and shared serial-boot options.

## Example: build the CRC command
```json
{
  "action": "cli_build_fcrc",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "cli_request": {
      "operation": "fcrc_cli",
      "input": {
        "target": "C:/NXP/.../targets/S32G2xx.bin",
        "algorithm": "C:/NXP/.../flash/EMMC.bin",
        "interface": "uart",
        "transport": { "kind": "uart", "device": "COM3", "driver": "ftdi" },
        "addr": "0x00000000",
        "size": "0x100",
        "file": "C:/path/image.bin"
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
    "command": "<command string returned by cli_build_fcrc>"
  }
}
```

## Command inspection
The `cli_build_fcrc` action returns the exact command line without touching the
target, so it doubles as the command-inspection/preview step. Use it whenever
the user wants to see the exact CLI command before execution.
