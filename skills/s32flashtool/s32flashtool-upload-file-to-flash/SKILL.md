---
name: s32flashtool-upload-file-to-flash
description: Program a binary file into supported flash memory on an NXP S32 device using either S32FlashTool CLI or S32FlashTool GUI via RPC.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32flashtool
  depends_on: '["s32flashtool-agent-rules-minimal", "s32flashtool-workflow-index", "s32flashtool-rpc-api"]'
  tags: '["s32flashtool", "cli", "gui", "rpc", "flash", "program", "write", "destructive"]'
---

# S32FlashTool Program Flash Memory

Program a binary file into supported flash memory on an NXP S32 target.

This skill supports **two execution modes**:

- **CLI mode** using:
  - `cli_build_fprogram` + `cli_execute`
  - or the `cli_build_<op>` + `cli_execute` actions as preview / fallback path
- **GUI mode** using S32FlashTool  GUI over RPC:
  - the matching `gui_*` action

This skill is **operation-focused**:
- it explains what the flash programming operation needs
- how to choose GUI vs CLI
- how to execute the program/upload in each mode
- how to validate the outcome
- how to handle destructive-operation confirmation safely

> Names shown in tool-call snippets below are routing hints. Confirm current parameter names and enum values via `search_actions(query="<action_name>", detailed=true, limit=1)`. See `s32flashtool-agent-rules-minimal`.

## When to use

Use this skill when the user wants to:
- program a file into external flash or other supported flash memory
- upload a bootable image/blob into flash
- write a binary file at a specified flash address
- program and verify a flash image
- trigger the S32FlashTool GUI upload/program workflow through RPC

## When not to use

Do **not** use this skill for:
- reading flash contents -> use `s32flashtool-read-flash`
- reading RCON/EEPROM -> use `s32flashtool-read-rcon`
- erasing only (without programming) -> use `s32flashtool-erase-flash`
- writing hex bytes into RCON/EEPROM -> use `s32flashtool-write-rcon`
- executing a binary from SRAM -> use `s32flashtool-sram`
- identifying the processor -> use `s32flashtool-read-mcuid`

## Shared references
- Apply shared rules from `s32flashtool-agent-rules-minimal/SKILL.md`.
- Use `s32flashtool-workflow-index/SKILL.md` to select the correct operation skill.

## Quickstart

1. Select mode  see `## Mode selection policy`
2. Gather inputs  see `## Required inputs` (use discovery calls from `## Preconditions`)
3. Preview the operation  CLI: `preview_only=true`; GUI: show payload
4. Obtain confirmation phrase "yes, program"  see `## Guardrails` (Destructive actions)
5. Execute  `references/CLI.md` or `references/GUI.md`
6. Validate  see `## Validation loop`

## Mode selection policy

Choose execution mode as follows:

1. If the user explicitly asks for **GUI**, **window**, **RPC**, or **S32FlashTool GUI**, use the **GUI/RPC flow**.
2. If the user explicitly asks for **CLI**, **command line**, **shell**, or requests a command, use the **CLI flow**.
3. If the user does not specify GUI or CLI:
   - prefer a preview-first CLI flow using `cli_build_fprogram` + `cli_execute`
4. If the user previously established a working GUI RPC session and continues issuing GUI-style requests, continue with RPC.
5. Do not silently switch from GUI to CLI or from CLI to GUI.
6. If the requested behavior is only possible through the other mode, explain the fallback before doing it.

## Preconditions

Before programming, ensure:

1. The S32FlashTool installation folder is known.
2. The target binary exists and matches the processor family.
3. The flash algorithm exists and matches the flash device.
4. The file to be programmed exists and is accessible.
5. The communication interface is known:
   - `uart`
   - `can`
   - `ethernet`
6. The communication endpoint is known.
7. The board is connected and powered.
8. The board is in **serial boot mode** for S32FlashTool communication.
9. If a different target/algorithm was used previously, a board reset / restart into serial boot may be necessary.
10. The user has explicitly confirmed the destructive programming action.

### Recommended preparation
Use concrete discovery tool calls instead of guessing. The following hints map each precondition to a tool call:

- List candidate target binaries:
  - `list_platform_files` action (bin_type="target").
- List candidate flash algorithms:
  - `list_platform_files` action (bin_type="flash").
- Confirm device / algorithm / interface support before any hardware-specific action:
  - `list_platform_files` action (bin_type="supported") and read the matching `supported_<platform>_devices.txt`.
- Inspect board-specific examples and PDFs if useful:
  - `list_platform_files` action (bin_type="blob")
  - `list_platform_files` action (bin_type="example_pdf").
- Discover available communication ports if the port is unknown:
  - the `cli_build_<op>` + `cli_execute` actions with `list_ports=true`.
- Identify the processor on the connected board when family is uncertain:
  - apply skill `s32flashtool-read-mcuid` (uses `cli_build_mcuid` + `cli_execute`).
- Capture current flash content before programming if it may be needed later:
  - `cli_build_fread` + `cli_execute` over the same `addr`/`size` range.

Do not invent values for `target`, `algorithm`, `port`, `addr`, or `file_path`. Use the discovery calls above or ask the user.

## Required inputs

Collect or confirm the following:

- `s32flashtool_folder`
- `target`
- `algorithm`
- `interface`
- `port`
- `addr`
- `file_path`

### Optional inputs

- `size`
- `verify`
- `extra_args`

## Input rules

- Do not guess the target binary.
- Do not guess the flash algorithm.
- Do not guess the COM port.
- Use absolute file paths when a file path is provided.
- `addr` and `size` may be decimal or hexadecimal.
- If the user asked for verify, preserve that request; do not silently claim verification occurred.
- Never claim "verified" unless verify was actually requested/configured and the tool reported it.
- Do not claim only the exact requested range will change; sector-based flash may erase/program a larger block.
- For GUI workflows, numeric strings may be normalized by the GUI. Treat that as normal unless the semantic value changed incorrectly.

## GUI / RPC flow

See [references/GUI.md](references/GUI.md) for the full GUI / RPC flow, payloads, and example sequences.

## CLI flow

See [references/CLI.md](references/CLI.md) for the full CLI flow, parameters, and example MCP calls.

## Validation loop

After programming, validation may include:

- checking that the programming action completed successfully
- checking that verify was enabled if requested
- reading back a region from flash
- comparing CRC against the programmed file
- checking expected boot behavior on the board

### Practical validation examples
- run a read-back of the first bytes
- use `cli_build_fcrc` + `cli_execute`
- save a read-back file and compare contents
- boot the board from flash and check expected UART output

## Failure modes

Recognize these failures from tool output and respond accordingly. Never auto-retry a destructive operation. On any failure, report the exact tool output before proposing next steps.

| # | Failure | Symptom | Interpretation | Response |
|---|---|---|---|---|
| 1 | User-aborted program (GUI) | `flash.clickUploadFileToDevice` returns OK but GUI dialog cancelled or reports aborted | RPC click dispatched; operation did not complete | Report as user-cancelled; ask whether to retry. Do not claim success. |
| 2 | Target / algorithm mismatch | Algorithm does not match device; flash not detected; JEDEC/device ID mismatch; identification-related error at start | Wrong `target` and/or `algorithm` for the board or flash device | Stop. Re-run `list_platform_files` action (bin_type="supported") and consult `supported_<platform>_devices.txt`. If family uncertain, apply `s32flashtool-read-mcuid` first. Do not guess a new algorithm. |
| 3 | File larger than flash / range exceeds device | Tool reports `addr + file_size` exceeds flash size, or destination range is unmapped | File too large for the device, or base `addr` set incorrectly | Do not silently truncate the file. Confirm geometry from `supported_<platform>_devices.txt`. Ask the user to confirm `addr` or the file. |
| 4 | Verify-after-program mismatch | Programming completes but built-in verify, `fverify`, or a follow-up CRC compare reports a mismatch | Write appeared to succeed but flash content differs (not erased first, protected/locked region, algo without erase-before-write, or brownout/reset during programming) | Do not report success. Ask whether to erase the range first via `s32flashtool-erase-flash`, then re-program. Read the mismatched region with `cli_build_fread` + `cli_execute` to inspect. Do not auto-retry without an intermediate erase. |
| 5 | Missing initialization (GUI/RPC) | `flash.clickUploadFileToDevice` fails; destination reported as not initialized | `init.clickLaunchInitialization` was skipped or failed for `FLASH` | Call `init.clickLaunchInitialization` before retrying. If init itself fails, treat as row 2 or row 6. |
| 6 | Communication / boot-mode / path errors | Port not open; no response; file-not-found on `target`/`algorithm`/`file_path` paths | Wrong `port`, board not in serial boot, previous session used a different target/algo, or bad paths | Verify `target`/`algorithm`/`file_path` paths, `interface`, `port`, `addr`, boot mode. Confirm serial boot mode. If a different algorithm ran previously, ask the user to reset the board into serial boot. |
| 7 | GUI/RPC unavailable | `hello` fails or RPC endpoint unreachable | GUI not running or RPC disabled | Do not launch a second GUI blindly; follow the launch procedure in `s32flashtool-rpc-api`. Explain unavailability and ask whether CLI fallback is acceptable. |

## Guardrails

**Scope**
- Only program a binary file into supported flash memory on a supported NXP S32 target using `cli_build_fprogram` + `cli_execute`, the `cli_build_<op>` + `cli_execute` actions` as a preview/fallback, or the documented GUI/RPC upload flow.
- Do not read, erase-only, run SRAM images, or write RCON hex from this skill.
  Recovery: hand off to the correct sibling skill.

**Destructive actions (confirmation contract)**
- Programming is destructive and may affect a larger sector/block than the requested byte range on sector-based flash. Always **preview** first: print file path, target, algorithm, interface, port, flash address, and (if applicable) whether verify is enabled.
- Before the actual program step, summarize the intended operation and warn that programming may affect a larger flash block or sector than the requested range depending on flash geometry.
- Require an **explicit user confirmation phrase** (e.g. "yes, program") before invoking the program action. This applies to **both** CLI and GUI/RPC flows. Recovery: if the user hesitates, stop;  do not program.
- Never claim "verified" unless verify was actually requested/configured and the tool reported it.
- Never mix GUI and CLI in the same program invocation. Recovery: pick one mode up front.

**Refuse-and-escalate**
- Missing/ambiguous file, target, algorithm, interface, port, or address: stop and ask.
- Board not in serial boot mode, or a previous session used a different target/algorithm: ask the user to reset the board into serial boot before retrying.
- RPC GUI: if `hello` fails, do not launch a second GUI blindly; follow the launch procedure in `s32flashtool-rpc-api`. Never use `communicationDevice = UART`; use `COM` with values like `COM15,ftdi` in `comPort`.

**Output contract**
- Report the tool's exit status, the address range programmed, and (only when actually run) the verify result. Do not claim success without a positive response from the tool. Do not fabricate a verify verdict.

## Out of scope

- Claiming a verify pass when verify was not actually configured/executed.
- Byte-granular programming on sector-based flash. This skill respects the device's native erase/program granularity.
- also see `## When not to use`

## Examples

- intentionally push examples into `references/*.md`
