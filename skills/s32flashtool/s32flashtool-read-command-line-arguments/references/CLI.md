# S32FlashTool Read Command Line Arguments - CLI flow

Use this flow for **all** read-command-line-arguments requests. This skill is CLI-only; there is no GUI/RPC equivalent. See `references/GUI.md` in this same folder for the explicit refusal to invent one.

## Operation mapping (CLI)

**User intent:** list supported CLI arguments / verify a flag exists in the installed version / reconcile docs vs. observed behavior

- Primary action: `cli_execute` run with no operation arguments
- Invocation: pass only `sft_folder` and a bare command (the executable with no flash-operation flags)
- Algorithm / target / port: **not used** (do not pass any)
- Destructive: **no**; confirmation not required; no board communication

## Action flow

Running S32FlashTool CLI binary (`S32FlashTool.exe` on Windows, `S32FlashTool` on Linux) without operation parameters prints its help/version
text. Reach this via `cli_execute` with a command that carries no operation
flags:

1. `search_actions("run flash tool command")` to discover `cli_execute` and its schema.
2. `execute_action("cli_execute", { sft_folder, command })` where `command` is the
   bare executable invocation (no target/algorithm/interface/port/operation args).

The installed S32FlashTool CLI binary then returns its produced text, which typically
includes:
- version/build identification
- command line syntax
- supported options/arguments

## Parameters

Required:
- `sft_folder`
- `command` (bare executable invocation, no operation flags)

Explicitly NOT used for argument introspection:
- `target` / `algorithm` -- not needed to print help; do not include them.
- `interface` / `port` -- no board communication happens; do not include them.
- `addr` / `size` / `file` -- no memory range or file is involved; do not include them.
- any flash operation flag -- omit; running with no flash command yields the help/version text.

## Decision rules for agents

- Prefer live tool output over assumptions from older examples.
- Treat the installed executable output as version-specific evidence.
- If documentation and the live executable output differ, call out the discrepancy explicitly.
- Do not guess that a flag exists because it existed in another S32FlashTool release.
- Do not require hardware access for this check.
- Do not add operation parameters to `cli_execute` when the goal is only to
  inspect supported arguments.

## Example: read command line arguments (Windows)
```json
{
  "action": "cli_execute",
  "params": {
    "sft_folder": "C:/NXP/S32FlashTool_2.4.2",
    "command": "S32FlashTool.exe"
  }
}
```

## Example: read command line arguments (Linux)

On Linux the executable has no `.exe` suffix and paths use the native layout:

```json
{
  "action": "cli_execute",
  "params": {
    "sft_folder": "/opt/nxp/S32FlashTool_2.4.2",
    "command": "S32FlashTool"
  }
}
```


## Expected output shape

The command returns S32FlashTool stdout as text, typically including:
- product name
- version/build
- supported command line options
- parameter hints

Example beginning:

```text
S32 Flash Tool 2.4.2. Build 260424. Copyright ...
Usage: ...
...
```

## Relationship to static documentation

Use this skill together with the static resource:
- `s32flashtool_command_line_arguments.md`

Recommended interpretation order:
1. Use the static documentation for normalized agent guidance.
2. Use `cli_execute` without extra operation arguments to confirm what the local
   installation actually exposes.
3. If there is a conflict, prefer the installed executable output and mention the mismatch.

This is not redundant duplication:
- the **documentation** is the curated reference
- this **skill** is the live verification workflow
