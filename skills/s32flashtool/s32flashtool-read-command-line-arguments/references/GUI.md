# S32FlashTool Read Command Line Arguments - GUI / RPC flow

## There is no GUI / RPC flow for this operation

Reading the S32FlashTool command line arguments is **CLI-only**. This file exists so that an agent heading-scanning for `references/GUI.md` (as is common across the other operation skills in this pack) finds an explicit refusal rather than a missing file.

### Why there is no GUI / RPC flow

The documented RPC action allowlist in `s32flashtool-rpc-api/SKILL.md` does not expose any action that returns the CLI help/argument text. In particular:

- There is no `model.get` key that returns the executable's usage/help output.
- There is no `cli.clickHelp`, `app.getArguments`, or equivalent RPC action.
- The GUI is a graphical front end; it does not surface the command-line executable's argument list over RPC.

The absence of an RPC action is not a documentation gap that an agent can bridge -- it is an intentional pack-level constraint (rule 9 in `s32flashtool-agent-rules-minimal`: *"Use only documented RPC actions and model keys."*).

### What to do instead

Use the CLI flow documented in `references/CLI.md`:

- MCP tool: the `cli_build_<op>` + `cli_execute` actions
- called with only `s32flashtool_folder` (no operation arguments)

If the user explicitly asked for GUI / RPC / window operation:

1. Do **not** invent an RPC action.
2. Do **not** silently redirect the request to an unrelated RPC action.
3. Explain clearly that argument introspection is not exposed by the S32FlashTool GUI RPC API.
4. Offer the CLI path as the only supported alternative and ask for explicit approval before switching modes (`s32flashtool-rpc-api` "CLI fallback rule").

### If the user is already in an active GUI RPC session

An active session does not create a GUI argument-introspection path. The session remains usable for the operations that *do* have documented RPC actions. For reading command line arguments specifically, dispatch the CLI call directly; it does not require or disturb the GUI's connection state and needs no board communication.

### Do not

- Do not invent RPC actions or model keys.
- Do not substitute an unrelated RPC action for reading CLI arguments.
- Do not silently fall back to CLI without telling the user that GUI is not available for this operation.
- Do not treat this file as a placeholder to be filled in later. The refusal is intentional.
