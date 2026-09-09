---
name: s32flashtool-evidence-disciplined-technical-validation
description: Use for technical investigations where documentation, static analysis, inferred context, package contents, or example assets must not be confused with live verification.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32flashtool
  depends_on: '["s32flashtool-agent-rules-minimal", "s32flashtool-workflow-index"]'
  tags: '["s32flashtool", "validation", "methodology", "diagnostic"]'
---
# Evidence-Disciplined Technical Validation

A methodology layer for S32FlashTool answers. It forces every technical
claim to carry an evidence tag so that documentation, package inventory,
inference, and live hardware readings are never mixed into a single
"confirmed" statement.

## When to use

Use this skill when a response would otherwise blur the line between what is
documented, what is available in the installation, what is inferred, and what
is verified on the connected hardware. Apply it as a **methodology layer** on
top of any S32FlashTool workflow that produces technical claims - before
answering questions of the form "is it supported?", "is this the board?",
"will this work?", or "can I use this flash?".

Typical triggers:
- the user asks whether a processor, flash memory, interface, or board is
  **supported**, and only documentation or installation inventory has been
  consulted
- the user asks to **confirm** a board identity, MCU identity, or flash
  identity, and no live tool call has produced that evidence yet
- the answer is about to combine documentation, package contents, and
  hardware behavior into a single statement (e.g. "this board has S32N55
  and the flash is EMMC")
- a support-matrix question was answered by scanning `flash/`, `targets/`,
  or `examples/` rather than by reading `doc/supported_*_devices.txt`
- board-image analysis produced an "expected configuration" and the agent
  is tempted to report it as the actual configuration
- the user asks "will this work?" or "is this compatible?" before any
  live `fread`, `fprogram`, `fverify`, `fcrc`, or `mcuid` has succeeded
- a previous step returned only `inferred` evidence and the user now asks
  for a factual answer

Also apply this skill when reviewing another skill's output before
presenting it to the user, to ensure each claim carries an evidence tag
(`live`, `installed-doc`, `user-supplied`, `inferred`).

## When not to use

Do **not** use this skill as the primary skill for:
- identifying which S32 board the user has - use `s32flashtool-identify-user-board`
- answering "which processors / flashes / interfaces are supported on
  platform X" - use `s32flashtool-supported-devices-per-platform`
- performing any operation on the target (read, program, erase, verify,
  CRC, RCON, SRAM, MCU ID) - use the matching operation skill
- routing a user request to the correct workflow - use `s32flashtool-workflow-index`

This skill is **methodology-only**. It never invokes MCP tools. It sits
alongside the operation and identification skills to keep their outputs
epistemically honest, but it never replaces them.

## Shared references
- Apply shared rules from `s32flashtool-agent-rules-minimal/SKILL.md`.
- Use `s32flashtool-workflow-index/SKILL.md` to select the correct workflow.

## Quickstart

For every technical claim in a response, do this pass:

1. Assign the claim an evidence tag:
   `live` (from a real MCP tool call in this session),
   `installed-doc` (inspected file under `s32flashtool_folder`),
   `user-supplied` (stated by the user), or
   `inferred` (deduced from static context).
2. If the user asked for verified facts and only `inferred` evidence is
   available, refuse and describe what would satisfy verification.
3. Never merge tags in one sentence. Split the claim if needed.

## Core Principle

Always distinguish between:

1. **Documented** - stated in manuals, support files, examples, PDFs, release notes, or package metadata.
2. **Available in installation** - present as files, binaries, examples, templates, or package artifacts.
3. **Inferred** - reasoned from naming, context, patterns, prior steps, or partial evidence.
4. **Verified** - directly confirmed by live tool output, hardware interrogation, successful execution, or observed runtime results.

Do not present documented, available, or inferred conclusions as verified facts.

## Required behavior

| # | Rule | Canonical phrasing |
|---|---|---|
| 1 | Label the epistemic status of every meaningful technical claim (`Documented` / `Available in installation` / `Inferred` / `Verified` / `Unknown`). | *"The MCU identity is **verified** by live `read_mcuid` output."* |
| 2 | Never upgrade evidence: documentation is not a hardware fact; package contents are not a populated board; example availability is not compatibility; algorithm presence is not board support; image resemblance is not identification. | *"The algorithm is **available in the installation**; it does not by itself prove eMMC is populated on this board."* |
| 3 | Keep five concepts separate: **documented support**, **package availability**, **board/platform expectation**, **connected hardware identity**, **operational validation**. Never merge them in one sentence. | *"The support file documents S32N55; the connected board is not yet verified."* |
| 4 | For support-matrix questions (supported processors / flashes / interfaces / limitations), read `doc/supported_*_devices.txt` first. Use `flash/`, `targets/`, examples, release notes, or semantic search only for cross-checking. | *"Per `supported_s32n5_devices.txt`, S32N55 is documented as supported."* |
| 5 | Presence of a file in the install tree means only "available in the installed package". It does not imply documented support, board population, current-setup validity, or hardware verification. | *"`EMMC.bin` is available in the installation; the support file must confirm eMMC for the board."* |
| 6 | If a live tool exists that would materially raise certainty, name it before making a strong claim. | *"Documented support only; live confirmation would require `s32flashtool-read-mcuid`."* |
| 7 | Cite the evidence source by file or tool name when giving important conclusions. | *"Based on `supported_s32n5_devices.txt` and the `X-S32NZ55-EVB.pdf` example."* |
| 8 | Prefer precise wording over convenient wording. Split "it is supported" into what layer of evidence supports it. | *"**Documented as supported** by the installed package, but **not yet verified on the connected hardware**."* |
| 9 | When user intent is ambiguous ("Is it supported?", "Will this work?"), clarify or answer at every evidence layer explicitly. | *"Documentation-level: listed. Hardware-level: not yet."* |
| 10 | For hardware and flashing workflows, use the 5-level reporting model: Documented / Available / Expected / Verified / Validated. | See `## Default answer template`. |
| 11 | Board-image analysis is a vision tool for observed physical state only. Ignore any "expected/reference/template" configuration it returns; official setup comes from S32FlashTool PDFs and support files. | *"Image shows a USB connector; official boot-mode setup must come from the board PDF."* |

### Preferred vs. avoided wording

**Prefer:** *"documented as supported"*, *"available in the installation"*, *"expected to be"*, *"appears consistent with"*, *"suggests"*, *"not yet confirmed"*, *"would need live verification"*, *"cannot be concluded from documentation alone"*.

**Avoid:** *"is supported"* (when only docs consulted), *"confirmed"* (without direct evidence), *"the board is X"* (when only inferred), *"this flash is on the board"* (when only the algorithm exists in the package), *"this will work"* (without validation).

## Evidence-source cheat sheet

Use this to decide what a source can and cannot justify.

| Source | Justifies | Does NOT justify |
|---|---|---|
| `doc/supported_*_devices.txt`, board PDFs, examples, release notes, semantic-search results, image-analysis template expectations | *"documented as supported"*, *"expected to be available"*, *"example exists for this board"* | *"confirmed on this physical board"*, *"proven to work in the current setup"* |
| Files in `flash/`, `targets/`, `examples/`, package-contained PDFs and templates | *"available in the installation"*, *"present in the package"*, *"candidate artifact exists"* | *"available on the board"*, *"supported for this board"* (unless docs also say so) |
| Successful `s32flashtool-read-mcuid`, successful `fread`/`fprogram`/`fverify`/`fcrc`, explicit board-image match with confidence, port discovery, runtime identification output | *"verified"*, *"confirmed by tool output"*, *"operationally validated"* | anything beyond what the tool actually returned |

## Default answer template

When a user asks for confirmation, use this structure:

```
Here is the precise status:

- Documented:              ...
- Available in installation: ...
- Expected / inferred:     ...
- Verified:                ...
- Not yet verified:        ...

Conclusion: ...
```

## Guardrails

**Scope**
- Apply only to technical claims where documentation, static analysis, package inventory, or
  inferred context could be mistaken for live verification (board support, supported
  processors/flash, flashing workflows, board identification).
- Never merge documentation-based conclusions with live-hardware conclusions in the same statement.
  Recovery: split the claim into two labeled statements.

**Destructive actions**
- This skill is a methodology, not an operation. It never triggers writes. If verification demands
  live interaction, hand off to the matching operation skill and require explicit confirmation.

**Refuse-and-escalate**
- If a claim cannot be sourced to (a) live tool output, (b) inspected installed documentation, or
  (c) explicit user statement: refuse to assert it as verified. Recovery: label it "unverified",
  cite what would be needed to verify, and ask the user how to proceed.
- If installation folder is not provided, refuse "installed-example evidence" claims.

**Output contract**
- Every assertion carries an evidence tag: `live`, `installed-doc`, `user-supplied`, or
  `inferred`. Recovery: if you cannot tag a statement, drop it.

## Validation loop

1. Every technical assertion emitted during the workflow carries one of the
   evidence tags `live`, `installed-doc`, `user-supplied`, or `inferred`.
   Fail on any unlabeled assertion.
2. No `inferred` claim is presented as if it were `live` or `installed-doc`.
   Fail if the transcript merges categories.
3. When the user asks a support/verification question that requires live data
   and no live data exists, the response is a refusal plus a description of
   what would satisfy verification. Fail if the response fabricates a live-style
   answer from static sources.
4. No MCP tool that writes to a target was invoked. This skill is
   methodology-only. Fail on any destructive tool call.

## Out of scope

- Executing any MCP tool. This skill is a methodology, not an operation.
- Board identification. Use `s32flashtool-identify-user-board`.
- Support-matrix answers. Use `s32flashtool-supported-devices-per-platform`.
- Producing conclusions from `inferred` evidence when the user asked for
  verified facts. Refuse and describe what would satisfy verification.
