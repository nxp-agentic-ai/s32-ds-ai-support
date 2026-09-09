---
name: s32flashtool-read-command-line-arguments
description: Retrieve the command line arguments exposed by an installed S32FlashTool command-line application (CLI) and use them as the version-specific source of truth.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32flashtool
  depends_on: '["s32flashtool-agent-rules-minimal", "s32flashtool-workflow-index"]'
  tags: '["s32flashtool", "cli", "diagnostic", "introspection", "read-only", "arguments"]'
---

# S32FlashTool Read Command Line Arguments

Retrieve the command line arguments supported by the installed S32FlashTool instance and use them as the version-specific source of truth. Semantic search with `nxp_knowledge_kb_search` and corpus `s32flashtool` should be prefered.

This skill supports **one execution mode**:

- **CLI mode** using:
  - the `cli_build_<op>` + `cli_execute` actions
  - run with only `s32flashtool_folder` (no board communication, no flash operation arguments)

There is **no GUI / RPC mode** for reading command line arguments; the S32FlashTool GUI RPC API exposes no documented action that returns the CLI help/argument text. See `references/GUI.md` for the explicit refusal.

This skill is **operation-focused**:
- it explains what the argument-introspection operation needs
- why this operation is CLI-only
- how to execute the read
- how to validate the outcome

## Shared references
- Apply shared rules from `s32flashtool-agent-rules-minimal/SKILL.md`.
- Use `s32flashtool-workflow-index/SKILL.md` to select the correct operation skill.
- For the CLI flow, see `references/CLI.md`.
- For the (intentional) absence of a GUI/RPC flow, see `references/GUI.md`.

## Quickstart

1. Confirm mode  see `## Mode selection policy` (CLI-only; refuse GUI/RPC requests)
2. Gather inputs  see `## Required inputs`
   - Argument-introspection-specific: pass only `s32flashtool_folder`; do **not** pass target, algorithm, interface, port, address, file, or flash-operation arguments
3. Execute  `references/CLI.md`
4. Validate  see `## Validation loop`

Do not escalate to board communication or programming operations from this skill.

## Mode selection policy

This skill is **CLI-only**.

1. Regardless of what the user requests, reading command line arguments uses the **CLI flow**.
2. If the user explicitly asks for **GUI**, **window**, or **RPC**, explain that argument introspection is not exposed by the S32FlashTool GUI RPC API (see `references/GUI.md`) and offer the CLI path.
3. Do not invent an undocumented GUI/RPC action for reading CLI help.
4. An active GUI/RPC session does not create a GUI help-text path; dispatch the CLI call directly.

## When to use this skill

Use this skill when the user wants to:

- know which command line arguments S32FlashTool supports
- verify whether a specific option exists in the installed version
- confirm an argument that is not listed in the local S32FlashTool command line documentation
- verify version-specific behavior before attempting an operation
- reconcile a discrepancy between documentation and observed tool behavior

## When not to use this skill

Do **not** use this skill when:

- the user wants to **identify the connected device / read MCU ID**
  -> use `s32flashtool-read-mcuid`
- the user wants to **read flash contents**
  -> use `s32flashtool-read-flash`
- the user wants to read **RCON/EEPROM**
  -> use `s32flashtool-read-rcon`
- the user wants to **program/write/upload** a file
  -> use `s32flashtool-upload-file-to-flash`
- the user wants **GUI automation through RPC**
  -> not available for argument introspection; this skill is CLI-only

## Preconditions

Before reading command line arguments, ensure:

1. The S32FlashTool installation folder is known.
2. The installation contains `bin/S32FlashTool.exe` on Windows, `bin/S32FlashTool` on Linux.
3. The caller can provide the absolute installation path.

No board connection, target binary, algorithm, port, or serial boot mode is required.

### Recommended preparation
- Confirm the installation is reachable if unsure:
  - `cli_execute` (version query).

## Required inputs

Collect or confirm the following:

- `s32flashtool_folder` - absolute path to the S32FlashTool installation directory,
  e.g. `C:/NXP/S32FlashTool_2.4.2`.

### Optional inputs
- none

## Input rules

- Use an absolute path for the installation folder.
- Do not pass target, algorithm, interface, port, address, file, or flash-operation arguments when
  the goal is only to inspect supported arguments.
- Do not use raw shell commands instead of MCP tools.
- Do not invent undocumented flags.
- If a flag is missing from both the static documentation and live tool output, treat it as unsupported unless the user provides authoritative evidence.
- Do not silently switch to a GUI/RPC flow; none exists for this operation.

## GUI / RPC flow

There is no GUI / RPC flow for reading command line arguments. See [references/GUI.md](references/GUI.md) for the explicit refusal and the correct response when the user asks for GUI/RPC operation.

## CLI flow

See [references/CLI.md](references/CLI.md) for the full CLI flow, parameters, fallback behavior, and example MCP calls.

## Validation loop

After a successful read, validation may include:

- checking that the command produced help/version text rather than an error
- confirming the returned text includes product name, version/build, and supported options
- labeling the source clearly as `installed CLI, version <X>`
- comparing the live output against the static command-line documentation and calling out any mismatch

### Practical validation examples
- confirm the output begins with a product/version banner, e.g. `S32 Flash Tool 2.4.2. Build 260424.`
- confirm the specific flag the user asked about is present (or clearly report it as absent)
- if the output is empty or an error, treat it as a failed read; do not infer supported arguments

## Failure modes

Recognize these failures from tool output and respond accordingly. This is a read-only introspection step, so a bounded retry after correcting inputs is acceptable. On any failure, report the exact tool output before proposing next steps.

| # | Failure | Symptom | Interpretation | Response |
|---|---|---|---|---|
| 1 | Missing installation folder | `s32flashtool_folder` not provided | Cannot locate the executable | Stop and ask for the absolute installation path. Do not guess. |
| 2 | Missing executable | file-not-found on `{s32flashtool_folder}/bin/S32FlashTool.exe` on Windows, `{s32flashtool_folder}/bin/S32FlashTool` on Linux | Installation path wrong or install incomplete | Report the missing binary and stop. Do not fall back to static documentation without labeling the fallback. |
| 3 | Empty / limited output | Command returns little or no help text | Executable ran but produced weak output | Fall back to `cli_execute` (version query) (weaker: version only). Do not infer unsupported arguments from missing output. |
| 4 | GUI/RPC requested | User asks for GUI/window/RPC argument reading | No documented RPC action returns CLI help text | Explain that argument introspection is not exposed by the GUI RPC API (see `references/GUI.md`). Offer the CLI path and ask before switching modes. |
| 5 | Doc / live mismatch | Static docs and live output disagree about a flag | Version-specific behavior differs from curated docs | Prefer the installed executable output and call out the discrepancy explicitly. |

## Guardrails

**Scope**
- Only query the installed S32FlashTool CLI binary under `{s32flashtool_folder}/bin/` (`S32FlashTool.exe` on Windows, `S32FlashTool` on Linux) for its documented
  help/version text via the `cli_build_<op>` + `cli_execute` actions (CLI). There is no documented GUI/RPC flow; do not invent one.
- Use this skill as the version-specific source of truth when documentation and observed behavior differ.
- Do not read MCUID, flash, or RCON, and do not program from this skill.
  Recovery: hand off to the correct sibling skill.

**Destructive actions**
- Read-only. Must never invoke a writing tool or touch a connected target.

**Refuse-and-escalate**
- If the installation folder is not provided, stop and ask for the absolute path.
- If the CLI binary in `{s32flashtool_folder}/bin` is missing, stop and report the missing binary; do not fall back to static documentation without labeling the fallback.
- GUI/RPC: argument introspection is not exposed by the S32FlashTool GUI RPC API. Do not invent an RPC action; offer the CLI path and ask before switching modes.

**Output contract**
- Report the tool's help output verbatim (or a faithful summary) plus a clear source label (`installed CLI, version X`). Never mix installed-CLI output with generic doc text without a
  label.

## Out of scope

- Communicating with a target or opening a port.
- Reading MCUID, flash, RCON, or flash ID. Use the matching read skill.
- Programming a file into flash. Use `s32flashtool-upload-file-to-flash`.
- GUI/RPC automation for argument introspection (no documented RPC flow exists).
- Replacing static CLI documentation for planning; use this skill specifically when documentation and observed behavior disagree.
- Falling back to generic documentation without labeling it as such if the installed executable is missing.
- also see `## When not to use this skill`

## Examples

- intentionally push examples into `references/*.md`
