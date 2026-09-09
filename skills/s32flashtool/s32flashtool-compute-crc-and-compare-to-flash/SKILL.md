---
name: s32flashtool-compute-crc-and-compare-to-flash
description: Compute CRC on a binary file and compare it against the corresponding flash memory region on an NXP S32 device using S32FlashTool.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32flashtool
  depends_on: '["s32flashtool-agent-rules-minimal", "s32flashtool-workflow-index"]'
  tags: '["s32flashtool", "cli", "crc", "verification", "flash", "read-only", "fast"]'
---

# S32FlashTool Compute CRC and Compare Against Flash

Quickly validate that a binary file (or a chunk of it) matches a region of
supported flash memory on an NXP S32 target, using the `fcrc` command.

Instead of reading the whole region back and comparing byte-by-byte, this skill
asks S32FlashTool to compute a CRC directly on the flash region and compares it
to the CRC of the file. This is a **read-only** and fast verification path.

Use MCP tools instead of raw shell commands whenever possible.

## When to use this skill

Use this skill when the user wants to:

- quickly validate that a range of flash matches the content in a file
- confirm a prior programming operation succeeded without a full read-back
- CRC-check a specific chunk of flash against a file

## When not to use

Do **not** use this skill for:

- Reading flash contents into a buffer or file. Use `s32flashtool-read-flash`.
- Writing / programming a file to flash. Use `s32flashtool-upload-file-to-flash`.
- Erasing flash. Use `s32flashtool-erase-flash`.
- Reading or writing RCON/EEPROM. Use `s32flashtool-read-rcon` / `s32flashtool-write-rcon`.
- Semantic interpretation of the compared region (boot header parsing, application signature checking). Report the raw pass/fail and hand off.
- Any workflow that "auto-fixes" a mismatch by writing. Confirm mismatch, then route to `s32flashtool-upload-file-to-flash` if the user requests it.

## Shared references
- Apply shared rules from `s32flashtool-agent-rules-minimal/SKILL.md`.
- Use `s32flashtool-workflow-index/SKILL.md` to select the correct operation skill.
- For the CLI flow, see `references/CLI.md`.
- For the (intentional) absence of a GUI/RPC flow, see `references/GUI.md`.

## Quickstart

CLI-only (no documented GUI/RPC flow):

1. Select mode  see `## Execution mode`
2. Gather inputs  see `## Required inputs` (use discovery calls from `## Preconditions`)
3. Execute  `references/CLI.md`

## Execution mode

This skill is **CLI-only**.

Do not try to force this operation through undocumented GUI RPC actions.

## Operation mapping

**User intent:** verify / compare / CRC-check a file against a flash region

### CLI mapping
- Preferred tool: `cli_build_fcrc` + `cli_execute`
- Expert fallback: `cli_build_fcrc` + `cli_execute`

### Safety
- Destructive: **no**
- Confirmation required: **no**

## Preconditions

Before checking, ensure:

1. The S32FlashTool installation folder is available.
2. The target binary (`.bin`) exists and matches the processor family.
3. The appropriate flash algorithm file (e.g. `EMMC.bin`) is selected.
4. The target device is connected and powered.
5. The correct communication interface and port are known.
6. The board is placed in **serial boot mode**. Search `[S32FlashTool installation folder]/examples` for the board-specific documentation (usually PDF), and if needed the indexed documentation for board-specific configuration examples.
7. (Optional) Read the MCUID to identify the target processor, and extract the supported processors from the supported-devices files.

### Recommended preparation
- Check supported target/algorithm combinations using the supported-device documentation.
- If needed, read MCUID first to help identify the processor family.
- If the port is not known, discover it before checking.

## Required inputs

Collect or confirm the following:

- `s32flashtool_folder`
- `target`
- `algorithm`
- `interface`
- `port`
- `addr`
- `file_path`
- `size` -- in the file, the chunk starts at offset 0; on flash it starts at `addr`. If not given, the file size is used.

### Optional inputs
- `extra_args` (only if explicitly required, e.g. `-l c`)
- `preview_only`
- `timeout` -- DO NOT USE.

## Input rules

- Do not guess the target binary.
- Do not guess the flash algorithm.
- Do not guess the COM port.
- Use absolute file paths for the installation folder, target, algorithm, and file.
- `addr` and `size` may be decimal or hexadecimal.

## CLI flow

Selected by "Execution mode" above. This skill is CLI-only.

See [references/CLI.md](references/CLI.md) for the full CLI flow, parameters, and example MCP calls.

## GUI / RPC flow

There is no GUI / RPC flow for CRC comparison. See [references/GUI.md](references/GUI.md) for the explicit refusal and the correct response when the user asks for GUI/RPC operation.

## Validation loop

After a successful CRC compare, validation may include:

- confirming the tool returned two CRC values (file-side and flash-side)
- confirming the final verdict states either "match" or "mismatch"
- inspecting a smaller range if the user wants confirmation

### Practical validation examples
- report both CRC values side-by-side
- on mismatch, offer a targeted read-back of the differing region via `s32flashtool-read-flash`

## Error handling

If the operation fails:

1. Report the exact failure clearly.
2. Check:
   - target path
   - algorithm path
   - file path
   - interface
   - port
   - address
   - size
   - boot mode
3. If using UART, remind the user to confirm the board is in serial boot mode.
4. If a different flash algorithm was used before, suggest restarting the board in serial boot mode.
5. Do not switch to write/program operations to "fix" a mismatch without an explicit user request.

## Do not

- Do not modify flash. Do not attempt to "correct" a mismatch by writing; report and stop.
- Do not guess target/device compatibility.
- Do not guess COM ports.
- Do not use raw shell commands instead of MCP tools.
- Do not invent a GUI/RPC flow for this operation.
- Do not claim "match" without both CRC values printed by the tool.

## Quick decision summary

- **Need to verify a file against flash quickly?**  
  -> use this skill (`fcrc`)

- **Need GUI/RPC automation?**  
  -> not for this operation; this skill is CLI-only

- **Mismatch found?**  
  -> stop and report; only re-program on explicit user request via `s32flashtool-upload-file-to-flash`

- **Missing target, algorithm, or port?**  
  -> discover them first, do not guess

## Guardrails

**Scope**
- Only compute and compare CRC between a local binary file and a flash region using the documented
  `fcrc` CLI path (`cli_build_fcrc` + `cli_execute` or the `cli_build_<op>` + `cli_execute` actions).
  There is no documented GUI/RPC flow; do not invent one.
- Do not modify flash. Do not attempt to "correct" a mismatch by writing; report and stop.

**Destructive actions**
- This is a read-only comparison. If the user asks to reprogram after a mismatch, hand off to
  `s32flashtool-upload-file-to-flash`; do not chain destructive actions implicitly.

**Refuse-and-escalate**
- Missing file, wrong algorithm, unknown port, or unclear address/size: stop and ask.
  Recovery: request the specific value; never guess.
- If the target is not in serial boot mode or communication fails, stop and ask the user to place the
  board in serial boot mode and reconnect.

**Output contract**
- Report CRC values from file and from flash side-by-side, plus a clear pass/fail verdict.
  Do not claim "match" without both values printed by the tool.

## Out of scope

- GUI/RPC automation for CRC comparison (no documented RPC flow exists).
- see `## When not to use`

## Examples

- intentionally push examples into `references/*.md` 
