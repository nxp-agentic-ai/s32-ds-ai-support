# S32FlashTool Program Flash Memory - CLI flow

Use this flow when:
- the user asked for CLI or a command line workflow
- the user asked for a command preview
- no GUI behavior was requested and a CLI command is the best fit

## Operation mapping (CLI)

**User intent:** upload / program / write a file into flash memory

- Build action: `cli_build_fprogram` (pinned operation `fprogram_cli`)
- Execute action: `cli_execute`
- Destructive: **yes**; confirmation required before executing the built command

## Action flow

CLI programming is a two-step, build-then-execute pattern:

1. `search_actions("program flash")` to discover `cli_build_fprogram` and read its input schema.
2. `execute_action("cli_build_fprogram", { sft_folder, cli_request })` -- returns a ready
   `command` string. Nothing runs on the target yet; this is the preview.
3. Show the built `command` to the user and obtain explicit confirmation.
4. `execute_action("cli_execute", { sft_folder, command })` to run it on the target.

## Input schema (cli_request.input for fprogram)

Required:
- `target` (path to target application binary)
- `interface` (`uart` | `can` | `ethernet`)
- `transport` (object matching the selected interface)
- `algorithm` (flash algorithm path)
- `addr` (decimal or hex string)
- exactly one of `file` or `hex_data`

Optional:
- `size`, `partition`, `noverify`, and shared serial-boot options
  (`secure_bootloader`, `xosc`, `xoscmode`, `log_comm`, `waitboot`,
  `boot_default_baudrate`)

## Preview-first rule
For CLI programming, preview is the safe default. Build the command first, show
it, and only call `cli_execute` after explicit user approval.

## CLI Path Rules

If the workflow started with the CLI build/execute actions, preserve the CLI path for subsequent device operations whenever possible.

1. Do not silently switch from CLI to GUI/RPC for ordinary follow-up steps.
2. If the requested action is not available through the CLI path, say so explicitly and ask whether to fall back to GUI/RPC.
3. Before preparing any device operation (program/read/CRC/erase/boot configuration), ask whether the user wants serial boot settings first.
4. If the user says yes, provide serial boot guidance before preparing the CLI operation.
5. If the user says no, continue with CLI.
6. When preparing a programming operation on the CLI path:
   - resolve target / flash algorithm / file without guessing
   - build a preview command first
   - require explicit user confirmation before execution
7. Do not jump directly to GUI model inspection if the workflow started on CLI.
8. Still remind the user to expect serial boot mode, and mention restart/re-power-cycle requirements when a new flash algorithm, destination, or boot configuration requires it.

## Example: build the programming command (preview)
```json
{
  "action": "cli_build_fprogram",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.1",
    "cli_request": {
      "operation": "fprogram_cli",
      "input": {
        "target": "C:/NXP/.../targets/S32G2xx.bin",
        "algorithm": "C:/NXP/.../flash/EMMC.bin",
        "interface": "uart",
        "transport": { "kind": "uart", "device": "COM3", "driver": "ftdi" },
        "addr": "0x00000000",
        "file": "C:/example/path/image.bin"
      }
    }
  }
}
```

The action returns a `command` string. Show it to the user for confirmation.

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
The `cli_build_fprogram` action already returns the exact command line without
touching the target, so it doubles as the command-inspection/preview step. Use
it whenever the user wants to see the exact CLI command before execution, and
only call `cli_execute` once they approve.
