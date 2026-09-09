---
name: s32flashtool-supported-devices-per-platform
description: Answer which processors, flash memories, communication interfaces, and platform limitations are supported by S32FlashTool for a given board, platform, or family, using installed support files as the authoritative source.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32flashtool
  depends_on: '["s32flashtool-agent-rules-minimal", "s32flashtool-workflow-index"]'
  tags: '["s32flashtool", "reference", "support-matrix", "platform", "read-only"]'
---

# S32FlashTool Supported Devices Per Platform

Reference skill for support-matrix questions. Produces a labeled summary of
supported processors, flash memories, communication interfaces, and
limitations for a given S32 platform or board, drawing from installed
support files, release notes, package inventory, and - as fallback -
`nxp_knowledge_kb_search`. Every claim in the output carries an evidence
label so documentation, package availability, and hardware-verified facts
are never merged.

## When to use

Use this skill when the user is asking a **support-matrix question** about
a specific platform, family, or board.

Typical triggers:
- *"Which processors are supported (on this board / by S32FlashTool)?"*
- *"Which flash memories are supported for S32N5 / S32G3 / ...?"*
- *"What interfaces are supported for this platform?"*
- *"What are the limitations for platform X?"*
- *"What is supported on this board?"* (after board identity is known or
  provided as a clue)
- Sibling skills (typically operation skills) need to check whether a
  target processor/flash/interface is documented as supported before
  proceeding.

## When not to use

Do **not** use this skill for:
- identifying which board the user has - use `s32flashtool-identify-user-board`
  first, then return here for the support-matrix answer
- hardware setup / connection details (interface choice, port discovery,
  boot mode) - use `s32flashtool-discover-hardware-setup`
- live processor identification from the connected target -
  use `s32flashtool-read-mcuid`
- routing an ambiguous request - use `s32flashtool-workflow-index`
- any operation on the target (read, program, erase, verify) - use the
  matching operation skill
- questions about a specific board's connectors, jumpers, or boot-mode
  switches - refer to the board's own documentation

This skill is **reference-only**. It never invokes tools that touch the
target and never claims hardware verification.

## Shared references
- Apply shared rules from `s32flashtool-agent-rules-minimal/SKILL.md`.
- Use `s32flashtool-workflow-index/SKILL.md` to select the correct workflow.
- Defer board identification to `s32flashtool-identify-user-board`.
- Apply `s32flashtool-evidence-disciplined-technical-validation` when the
  answer will be used for a factual claim.

## Quickstart

Follow this sequence. Skip forward when the user's clues already answer an
earlier step.

### Step 1 - Gather user clues

Extract any of: board name, processor name, processor family / platform,
flash memory name. If the user refers to *"this board"* and a board was
identified earlier in the session, reuse that identity.

If nothing usable is provided, ask the smallest missing question. Do not
guess a platform.

### Step 2 - Locate the authoritative source

Two branches, chosen by whether the installation folder is available:

**With `s32flashtool_folder`:**
1. list `s32flashtool_folder/doc/supported*_devices.txt` files
2. pick the file whose name matches the platform/family
3. read that file directly - it is the primary source
4. if no matching support file exists, fall back to Release Notes in
   `doc/`, then to `nxp_knowledge_kb_search` as a secondary aid

**Without `s32flashtool_folder`:**
1. call `nxp_knowledge_kb_search` with the best available clue
   (board / platform / processor family / flash memory)
2. produce a **provisional** answer, clearly labeled
3. ask for `s32flashtool_folder` only if the user wants authoritative
   verification against installed support files
4. never claim installed-package availability without the folder

Ask permission before reading arbitrary local files other than
`supported*_devices.txt`. Inform the user of any supplementary cost.

### Step 3 - Extract support facts from the matched file

From the matched `supported*_devices.txt`, extract as many of the following
as are documented:
- supported processors
- supported flash memories
- supported communication interfaces
- limitations and restrictions
- notes and family-specific remarks

If the user asks *"supported / available"*, split the answer into
**Documented support** (from the support file) and **Available package
artifacts** (from the installation tree). Never merge them into one list.

### Step 4 - Cross-check installation availability (secondary)

If the user asked about availability in the local installation, use
`list_platform_files` action to list:
- available target binaries (filter by documented processors/platform)
- available flash algorithms (filter by documented flash memories)

Report these under **available in installation** - never as evidence of
documented board support. Presence of `flash/X.bin` does not by itself
prove that `X` is supported for the current board.

### Step 5 - Add interfaces, limitations, and notes

From the support file, extract additional information (interfaces,
limitations, known issues). If missing there, consult Release Notes and
label the source explicitly. Use `nxp_knowledge_kb_search` only when no
direct installed documentation is available.

## Evidence sources

Use these in decreasing order of authority. Every claim in the response
labels which source it came from.

| Source | Label | Justifies | Does NOT justify |
|---|---|---|---|
| `s32flashtool_folder/doc/supported_<platform>_devices.txt` | `installed-doc:<file>` | *"Documented as supported"*, *"listed in the support file"* | hardware verification, board population |
| Release Notes / User Guide / board PDFs under `s32flashtool_folder/doc` | `installed-doc:<file>` | *"Documented as supported (release notes / user guide)"* | that a support file also confirms it |
| Files under `s32flashtool_folder/flash`, `targets`, `examples` | `installation-inventory:<path>` | *"Available in the installation"*, *"algorithm present in the package"* | *"supported on this board"*, *"available on the physical board"* |
| `nxp_knowledge_kb_search` result | `kb-search:<query>` | *"Consistent with knowledge-base entry"*, *"provisional"* | authoritative installed-package answers when the folder is available |
| User statement | `user-supplied` | *"Per user statement"* | anything the user hasn't actually stated |
| Live tool output from a connected target | `hardware-verified` | *"Verified by <tool> output"* | any support fact the tool did not return |

Prefer higher-authority sources when they are available. When installed
documentation and installation inventory disagree, report both sides and
name the discrepancy - do not silently pick one.

## Known documentation facts

- S32FlashTool supports families including S32R41, S32R45, S32G2xx, S32G3xx,
  SAF85xx, SAF86xx, S32R47, S32N5, S32Z2/E2, and other unreleased
  platforms. Confirm against the matching support file before quoting.
- Supported communication interfaces include UART, CAN, and Ethernet.
- The User Guide documents automatic port detection and MCU identification
  via `-mcuid`.

Treat this list as a rough index for locating the right support file - not
as an authoritative support statement in itself.

## Preferred wording

Prefer *"documented as supported"*, *"listed in `supported_<platform>_devices.txt`"*,
*"available in the installation"*, *"present in the `flash` folder"*,
*"expected to be supported based on knowledge-base evidence"*, *"not yet
hardware-verified"*, *"provisional answer, installed-file verification
pending"*.

Avoid *"is supported on this physical board"* (unless identity and
applicability are both verified), *"available on the board"* (when only
the algorithm is present in the installation), *"confirmed"* (without live
verification), or *"this will work"* (without a successful live run).

## Output format

Respond in this structure. Omit sub-sections that have no content rather
than leaving them empty.

### Support summary
- **Board / platform:** ...
- **Evidence mode:** installed documentation / provisional knowledge base / mixed
- **Matched support file:** `supported_<platform>_devices.txt` / not available
- **Supported processors:** ...
- **Supported flash memories:** ...
- **Supported communication interfaces:** ...
- **Limitations / notes:** ...
- **Verification status:** documented / provisional / hardware-verified

### Installed package availability
- **Available target binaries:** ... / not checked / not available without `s32flashtool_folder`
- **Available flash algorithms:** ... / not checked / not available without `s32flashtool_folder`

### Evidence
List each source used, one line per item, labeled per the Evidence sources
table (`installed-doc:<file>`, `installation-inventory:<path>`,
`kb-search:<query>`, `user-supplied`, `hardware-verified`).

### Recommended next step
State the single safest next action. Typical patterns:
- Provisional answer, `s32flashtool_folder` missing -> ask for the folder
  to verify against installed `supported_*_devices.txt`.
- Documented but not hardware-verified -> suggest `s32flashtool-read-mcuid`.
- User asked about installation availability -> list target binaries and
  flash algorithms filtered by the documented processors/flashes.

### If more information is required
Ask only the minimal follow-up question(s). Examples:
- *"What board or MCU family are you using?"*
- *"What is your S32FlashTool installation folder?"*
- *"Do you want documented support only, installed-package availability
  too, or hardware confirmation?"*

## Worked examples

**User asks *"Which processors and flash memories are supported/available
on this board?"*.** Identify the board/platform first (delegate to
`s32flashtool-identify-user-board` if unknown). Then list
`supported*_devices.txt` files in `doc/`, pick the matching one, read it
directly, and extract supported processors, flash memories, interfaces,
and limitations. Optionally cross-check installation availability. Report
documented support and installation availability as separate blocks.

**User asks *"What flash memories are supported for S32N5?"*.** Locate
`supported_s32n5_devices.txt`, read it directly, extract the documented
flash memories. Optionally cross-check with the `flash` folder inventory,
labeled as installation-availability, not as support evidence.

**User provides a board picture only.** Board identity is unknown - hand
off to `s32flashtool-identify-user-board` first. Return here once the
platform/family is established.

**`s32flashtool_folder` is not provided.** Use `nxp_knowledge_kb_search`
with the best available clue, return a clearly labeled provisional
answer, and ask for the folder only if the user wants authoritative
installed-file verification.

## Guardrails

**Scope**
- Only produce support-matrix answers (processors / flash memories /
  interfaces / limitations) for a given platform or family, using
  installed support files as primary evidence and installation inventory
  as secondary. Recovery on scope mismatch: name the correct sibling
  skill and stop.
- Keep support-matrix conclusions separate from board-identification
  conclusions (see `s32flashtool-identify-user-board`).

**Destructive actions**
- Reference-only. Never invoke a hardware operation.

**Refuse-and-escalate**
- Do not fabricate hardware-specific defaults. Recovery: ask for the
  missing detail.
- When a `supported_<platform>_devices.txt` exists, do not answer from
  `flash/*.bin` or `targets/*.bin` inventory alone. Recovery: read the
  support file first, then optionally cross-check inventory.
- If documentation and installation inventory disagree, report both sides
  and state the discrepancy. Recovery: ask the user which to trust.
- If `s32flashtool_folder` is not provided, refuse claims that require
  installed evidence. Recovery: label the answer as provisional, name what
  the folder would verify, and ask for it if the user wants stronger
  evidence.

**Output contract**
- Every claim carries an evidence label from the Evidence sources table.
  Recovery: if no source applies, drop the claim.
- Documented support and installation availability are reported in
  separate sub-sections of the output.
- The verification status is exactly one of `documented | provisional | hardware-verified`.

## Validation loop

1. Every claim about supported processors, flash memories, interfaces, or
   limitations carries an evidence label (`installed-doc:<file>`,
   `installation-inventory:<path>`, `kb-search:<query>`, `user-supplied`,
   or `hardware-verified`). Fail on any unlabeled claim.
2. When a `supported_<platform>_devices.txt` exists in the installation,
   it is used as the primary source. Fail if the response uses
   inventory-only evidence while a support file was available.
3. When installed documentation and installation inventory disagree, both
   are reported and the discrepancy is stated. Fail if only one side is
   presented as authoritative without noting the conflict.
4. Board-identification questions are deferred to
   `s32flashtool-identify-user-board`. Fail if this skill answers them
   directly.
5. Verification status is exactly one of `documented | provisional | hardware-verified`.
   Fail on any invented or missing value.
6. No MCP tool that writes to a target is invoked. Fail on any destructive
   tool call.

## Out of scope

- Board identification. Use `s32flashtool-identify-user-board`.
- Live verification of hardware. Use the connectivity/operation skills
  (`s32flashtool-read-mcuid`, `s32flashtool-get-flash-id`, etc.).
- Concluding platform support from `flash/*.bin` presence when a
  documented support file exists.
- Merging installed-doc and installation-inventory claims without labeling
  the source of each.
- Answering questions about a specific board's connectors, jumpers, or
  boot-mode switches. Refer to the board's own documentation.
