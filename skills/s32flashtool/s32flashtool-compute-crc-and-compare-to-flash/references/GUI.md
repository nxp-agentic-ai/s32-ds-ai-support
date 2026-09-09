# S32FlashTool Compute CRC and Compare - GUI / RPC flow

## There is no GUI / RPC flow for this operation

Computing a CRC on a file and comparing it against a flash region via S32FlashTool is **CLI-only**. This file exists so that an agent heading-scanning for `references/GUI.md` (as is common across the other operation skills in this pack) finds an explicit refusal rather than a missing file.

### Why there is no GUI / RPC flow

The documented RPC actions listed in `s32flashtool-rpc-api/SKILL.md` does not expose any action that computes a file-vs-flash CRC comparison. In particular:

- There is no `flash.clickCompareCrc` or equivalent CRC-compare RPC action.
- There is no `model.get` key that returns a computed CRC.
- `flash.clickDownloadFromDevice` reads back flash contents; it does not perform a CRC comparison. Do not substitute it and then compute a CRC yourself outside the documented tool.

The absence of an RPC action is not a documentation gap that an agent can bridge -- it is an intentional pack-level constraint (rule 9 in `s32flashtool-agent-rules-minimal`: *"Use only documented RPC actions and model keys."*).

### What to do instead

Use the CLI flow documented in `references/CLI.md`:

- MCP tool: `cli_build_fcrc` + `cli_execute`, or
- `cli_build_fcrc` + `cli_execute`

If the user explicitly asked for GUI / RPC / window operation:

1. Do **not** invent an RPC action.
2. Do **not** silently redirect the request to a read-back plus local CRC.
3. Explain clearly that file-vs-flash CRC comparison is not exposed by the S32FlashTool GUI RPC API.
4. Offer the CLI path as the only supported alternative and ask for explicit approval before switching modes (`s32flashtool-rpc-api` "CLI fallback rule").

### If the user is already in an active GUI RPC session

An active session does not create a GUI CRC-compare path. The session remains usable for the operations that *do* have documented RPC actions. For CRC comparison specifically, the correct behavior is to dispatch the CLI `fcrc` call; the CLI call does not disturb the GUI's connection state on its own, but it will occupy the same serial port. Coordinate access with the user.

### Do not

- Do not invent RPC actions or model keys.
- Do not substitute a read-back plus locally computed CRC for the documented `fcrc` comparison.
- Do not silently fall back to CLI without telling the user that GUI is not available for this operation.
- Do not treat this file as a placeholder to be filled in later. The refusal is intentional.
