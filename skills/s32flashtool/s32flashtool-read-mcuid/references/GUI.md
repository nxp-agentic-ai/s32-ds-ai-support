# S32FlashTool Read MCU ID - GUI / RPC flow

## There is no GUI / RPC flow for this operation

Reading the MCU ID via S32FlashTool is **CLI-only**. This file exists so that an agent heading-scanning for `references/GUI.md` (as is common across the other operation skills in this pack) finds an explicit refusal rather than a missing file.

### Why there is no GUI / RPC flow

The documented RPC action allowlist in `s32flashtool-rpc-api/SKILL.md` does not expose any action that reads the MCU ID. In particular:

- `flash.clickGetId` reads the **flash** memory JEDEC ID, not the MCU ID. Do not substitute it.
- There is no `model.get` key that returns the MCU ID.
- There is no `flash.clickReadMcuId` or equivalent.

The absence of an RPC action is not a documentation gap that an agent can bridge -- it is an intentional pack-level constraint (rule 9 in `s32flashtool-agent-rules-minimal`: *"Use only documented RPC actions and model keys."*).

### What to do instead

Use the CLI flow documented in `references/CLI.md`:

- MCP tool: the `cli_build_<op>` + `cli_execute` actions
- via `cli_build_mcuid`

If the user explicitly asked for GUI / RPC / window operation:

1. Do **not** invent an RPC action.
2. Do **not** silently redirect the request to `flash.clickGetId`.
3. Explain clearly that MCU ID reading is not exposed by the S32FlashTool GUI RPC API.
4. Offer the CLI path as the only supported alternative and ask for explicit approval before switching modes (`s32flashtool-rpc-api` "CLI fallback rule").

### If the user is already in an active GUI RPC session

An active session does not create a GUI mcuid path. The session remains usable for the operations that *do* have documented RPC actions (`upload-file-to-flash`, `read-flash`, `read-rcon`, `write-rcon`, `erase-flash`, `get-flash-id`, `sram`). For MCU ID specifically, the correct behavior is to dispatch the CLI mcuid call in parallel with the GUI session; the CLI call does not disturb the GUI's connection state on its own, but it will occupy the same serial port. Coordinate access with the user.

### Do not

- Do not invent RPC actions or model keys.
- Do not substitute `flash.clickGetId` for MCU ID reading.
- Do not silently fall back to CLI without telling the user that GUI is not available for this operation.
- Do not treat this file as a placeholder to be filled in later. The refusal is intentional.
