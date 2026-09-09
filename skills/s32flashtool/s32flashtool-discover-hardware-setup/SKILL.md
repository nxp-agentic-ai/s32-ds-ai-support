---
name: s32flashtool-discover-hardware-setup
description: Use this skill to discover the likely S32FlashTool hardware setup for a connected  target - interface, candidate port, target binary, flash algorithm, and the safest next identification step, without guessing missing hardware details.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32flashtool
  depends_on: '["s32flashtool-agent-rules-minimal", "s32flashtool-workflow-index"]'
  tags: '["s32flashtool", "discovery", "diagnostic", "hardware", "read-only"]'
---

# S32FlashTool Discover Hardware Setup

Determine, as far as possible from the installed S32FlashTool package, the user's clues, and the visible host environment:
- the likely communication interface (`uart`, `can`, or `ethernet`)
- candidate communication endpoints
- the most likely target binary
- the likely flash algorithm when the task requires one
- the single safest next command or tool call

## When to use

Use this skill for:
- identifying the likely communication interface for a connected target
- narrowing candidate ports/endpoints
- narrowing the likely target binary
- narrowing the likely flash algorithm when the task involves flash access
- choosing the safest next identification or validation step

## When not to use

Do not use this skill after the hardware setup is already known; go straight to the operation skill in that case.

## Shared references
- Apply shared rules from resource `s32flashtool-agent-rules-minimal/SKILL.md`.
- Use `s32flashtool-workflow-index/SKILL.md` to select the correct workflow.

## Quickstart

Read-only discovery pass to converge on interface/port/target/algorithm:

1. If the S32FlashTool installation folder is unknown, ask for the absolute
   path first.
2. Enumerate ports via `s32flashtool-list-available-serial-communication-interfaces`.
3. Inspect `<s32flashtool_folder>/flash/*.bin` and installed docs to list
   candidate targets and algorithms.
4. If the device is reachable, run `s32flashtool-read-mcuid` (safest read-only
   check) to narrow the target.
5. Emit ranked candidates with evidence labels and the single safest next
   step. Do not commit to one candidate when multiple remain plausible.

## Use these rules

1. Do **not** guess a COM port, target binary, device family, or flash algorithm when they are not known.
2. Prefer discovery using installed S32 Flash Tool capabilities and documentation over assumptions.
3. Use the S32 Flash Tool documentation and supported-device files to narrow candidates.
4. If the user mentions a board name, processor name, or family, use that to reduce the search space.
5. If the user does not mention the interface, consider all supported interfaces, but prefer:
   - `uart` when COM/serial devices are involved
   - `can` when the user mentions CAN adapters/bus
   - `ethernet` when the user mentions network-connected boards
6. If multiple valid candidates remain, present them clearly and ask the user for the smallest missing detail needed to continue.
7. Before proposing any programming or verification action, ensure the target binary and flash algorithm are explicitly identified.

## Recommended workflow

### Step 1: Gather user clues
Extract any of the following from the user request:
- board name
- MCU name or family
- connection type
- operating system
- visible COM/CAN/Ethernet endpoint
- task intent:
  - identify device
  - read MCU ID
  - upload a blob/binary
  - fast validation (using fcrc command)

### Step 2: Ask for the installation folder
Ask the user for the absolute `S32FlashTool installation folder` if it is not already known.
Use this value as `s32flashtool_folder` for all discovery operations.

### Step 3: Discover installed tool capabilities
Inspect the installed S32FlashTool environment for:
- available target binaries
- available flash memory algorithms
- supported-device details in the `doc` subfolder
- examples or board PDFs if needed

### Step 4: Consult documentation
Use installed documentation with `nxp_knowledge_kb_search` to determine:
- which device families are documented as supported
- which memory algorithms belong to which family
- whether board-specific notes exist
- whether UART, CAN, or Ethernet is appropriate

Known documentation facts:
- S32 Flash Tool supports families including S32R41, S32R45, S32G2xx, S32G3xx, SAF85xx, SAF86xx, S32R47, S32N5, S32Z2/E2 and other unreleased platforms.
- Supported communication interfaces include UART, CAN, and Ethernet.
- The user guide documents automatic port detection and MCU identification via `-mcuid`.

When the user asks whether a board is correctly configured for serial boot, boot mode, switch settings, or jumper settings:
1. identify the board
2. use `nxp_knowledge_kb_search` (as example: nxp_knowledge_kb_search query="<board_name> OR <processor_name> board features serial boot S32 Flash Tool UART boot memory" top_k=5):  
3. ask the user if the agent should search the installed S32FlashTool examples folder for the matching board PDF
4. extract the official settings from that PDF
5. only then compare with image-detected settings

### Step 5: Discover host endpoints
If the interface is unknown or likely UART/CAN, list available ports/endpoints using S32FlashTool discovery.
Do not invent endpoint names.

### Step 6: Narrow the target binary
Choose a target binary only when supported by evidence from:
- user-provided board/MCU/family name
- installed supported-device documentation
- installed target binary names

If several targets remain possible, list the best matches and explain why.

### Step 7: Narrow the flash algorithml
Only if needed for flashing, CRC, verify, or memory-read operations:
- inspect available algorithms
- match them to the family or memory technology mentioned in installed docs
- if still uncertain, ask the user what memory device or board they are using

### Step 8: Validate using MCU identification
When enough information is available, propose or run the safest identification command:
- prefer reading MCU ID before programming
- use explicit values for target, interface, and port
- do not proceed to flashing until setup is validated

## Output format
Respond in this structure:

### Hardware setup assessment
- **Likely interface:** ...
- **Candidate port(s):** ...
- **Likely target binary:** ...
- **Likely flash algorithm:** ...
- **Confidence:** high / medium / low

### Evidence
List the facts used:
- user-provided facts
- installed target names
- installed algorithm names
- supported-device documentation
- user-guide or release-note guidance

### Recommended next step
State the single safest next action.

### Command or tool suggestion
Provide the exact action to use next (via `execute_action`, e.g. a `cli_build_*` build then `cli_execute`, or the matching `gui_*` action), with explicit parameters where known.
If values are still unknown, show placeholders and say what is missing.

### If more information is required
Ask only the minimal follow-up question(s), such as:
- "What board or MCU family are you using?"
- "Which interface are you connected over: UART, CAN, or Ethernet?"
- "Which COM port or CAN adapter do you expect to use?"
- "Do you want to identify the device only, or also flash/verify memory?"

## Good behavior examples

### Example: user says "I connected an S32G board over USB and want to detect it"
Do:
- infer UART is likely, but not guaranteed
- inspect supported S32G devices and target binaries
- list available ports
- recommend reading MCU ID with an explicit S32G target candidate and selected port only after discovery
- mention that S32G documentation commonly uses UART COM-port workflows

### Example: user says "I need to program eMMC on an S32G2xx"
Do:
- inspect available algorithms
- identify `EMMC.bin` if present
- inspect target binaries for S32G2xx/S32G family
- recommend validating the port and MCU first before programming

### Example: user gives no hardware details
Do:
- not guess
- summarize supported interfaces and families
- ask for the smallest missing identifying detail

## Safety constraints
- Never fabricate hardware-specific defaults.
- Never assume a target binary just because one exists.
- Never choose a flash algorithm without evidence if the task is destructive.
- Prefer identification and discovery over programming.
---

## Guardrails

**Scope**
- Only discover and narrow: interface, candidate port, candidate target binary, candidate flash
  algorithm, safest next step. This is a read-only planning skill.
- Never fabricate hardware-specific defaults. Never assume a target binary just because one exists.

**Destructive actions**
- This skill must not run any destructive command. If discovery converges on a destructive next step,
  hand off to the matching operation skill and require explicit user confirmation there.

**Refuse-and-escalate**
- If the S32FlashTool installation folder is not provided, stop and ask for the absolute path.
- If multiple plausible targets/algorithms remain, present them as candidates with evidence; do not
  pick one silently. Recovery: ask the user to choose, or run `s32flashtool-read-mcuid` first.
- Prefer identification and discovery over programming. If in doubt, escalate to `read-mcuid`,
  `list-available-serial-communication-interfaces`, or `get-flash-id`.

## Validation loop

1. Every candidate returned (interface, port, target binary, flash algorithm)
   carries an evidence pointer: `installed-doc`, `installation-inventory`,
   `user-supplied`, or `inferred`. Fail if any candidate is unlabeled.
2. When multiple candidates remain plausible, all are presented; no silent
   single-pick was made. Fail if the transcript shows only one candidate where
   evidence supports several.
3. The proposed "safest next step" is a read-only skill
   (`read-mcuid`, `get-flash-id`, `list-available-serial-communication-interfaces`,
   `read-command-line-arguments`) unless the user explicitly asked for a
   destructive operation. Fail on unexplained escalation to a destructive skill.
4. No MCP tool that writes to a target was invoked from this skill. Fail on any
   destructive tool call.

## Out of scope

- Executing any operation on the target (read/program/erase/RCON/SRAM). This
  skill only narrows candidates and proposes the safest next step.
- Board identification by name/image. Use `s32flashtool-identify-user-board`.
- Answering support-matrix questions. Use
  `s32flashtool-supported-devices-per-platform`.
- Committing to a single target/algorithm when multiple candidates remain
  plausible. Present them and ask.
