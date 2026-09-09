# S32FlashTool SRAM Execute - CLI flow

Use this flow when:
- the user asked for CLI or a command line workflow
- full SRAM execution is needed now
- GUI RPC does not expose the final execute action

## Operation mapping (CLI)

**User intent:** load an image into SRAM and execute it via the BootROM protocol

- Build action: `cli_build_boot` (pinned operation `boot_cli`)
- Execute action: `cli_execute`
- Destructive: no persistent flash write; still confirm the intended effect

## Action flow

1. `search_actions("boot sram image")` to discover `cli_build_boot` and its input schema.
2. `execute_action("cli_build_boot", { sft_folder, cli_request })` -- returns the
   ready `command` string (nothing runs on the target yet; this is the preview).
3. `execute_action("cli_execute", { sft_folder, command })` to run it.

## Input schema (cli_request.input for boot)

Required:
- `target`
- `interface` (`uart` | `can` | `ethernet`)
- `transport` (object matching the selected interface)
- `file` (SRAM image)
- `addr`

Optional:
- `entrypoint`, `frb` (three thresholds `[frb0, frb1, frb2]`), and shared serial-boot options.

Do not supply `algorithm` for SRAM operations; the tool does not use a flash
algorithm for SRAM loading.

## Preview-first rule
For CLI SRAM execution, build and review the invocation (SRAM address / entry
point / FRB thresholds if any) before running. Do not claim "executed
successfully" beyond what the tool reports; side-channel confirmation from the
target is usually required.

## Example: build SRAM boot command
```json
{
  "action": "cli_build_boot",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "cli_request": {
      "operation": "boot_cli",
      "input": {
        "target": "C:/NXP/.../targets/S32N5x.bin",
        "interface": "uart",
        "transport": { "kind": "uart", "device": "COM3", "driver": "ftdi" },
        "addr": "0x40",
        "entrypoint": "0x1CC0",
        "file": "C:/example/path/image.bin"
      }
    }
  }
}
```

## FRB note
If the image requires FRB thresholds, pass them via the `frb` input as three
threshold values. Do not guess FRB values; use exactly what is documented for
the target family.

## Example: build SRAM boot command with FRB thresholds (CAN)
```json
{
  "action": "cli_build_boot",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "cli_request": {
      "operation": "boot_cli",
      "input": {
        "target": "C:/NXP/.../targets/S32N5x.bin",
        "interface": "can",
        "transport": { "kind": "can", "adapter": "vector" },
        "addr": "0x40",
        "entrypoint": "0x1CC0",
        "file": "C:/example/path/image.bin",
        "frb": ["0x0", "0x0", "0x0"]
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
    "command": "<command string returned by cli_build_boot>"
  }
}
```
