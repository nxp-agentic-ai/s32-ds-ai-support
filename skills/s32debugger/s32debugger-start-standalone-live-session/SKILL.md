---
name: s32debugger-start-standalone-live-session
description: >
  Route standalone S32Debugger requests to the best matching workflow. Use this
  whenever the user mentions standalone S32Debugger, a live or interactive
  standalone debug session, keeping a standalone session open for follow-up
  commands, multicore standalone debug, flash programming, or flash-then-debug
  behavior, even if the user does not explicitly ask for routing.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: '[s32debugger-start-singlecore-standalone-live-debug-session, s32debugger-start-multicore-standalone-live-debug-session, s32debugger-flash-programming, s32debugger-resolve-gdb-variant, s32debugger-resolve-core-name-from-context]'
  tags: '[s32debugger, standalone, routing]'
---

# S32Debugger Start Standalone Live Session

Route standalone S32Debugger requests to the correct execution workflow. This
skill classifies session shape and programming intent first, preserves explicit
core identity, identifies when startup context already exists versus must be
established, and then hands off to the correct dedicated single-core,
multicore, or flash path.

## When to use

Use this skill when:
- The user asks for a standalone S32Debugger session but the exact execution
  path still needs to be chosen.
- The request may be single-core live debug, multicore live debug, flash-only,
  or flash-then-debug from flash.
- The user wants a standalone session kept open for follow-up control but has
  not named the dedicated downstream skill.

Do **not** use this skill for:
- Re-implementing the detailed single-core, multicore, or flash leaf workflow.
- Expanding a clearly classified request into a generic routing conversation.
- Probe sanity checks, target-identification requests, or core-state queries
  when no interactive debug session is already active.
- Starting, preparing, or inspecting a GDB live-debug flow for observational
  requests that can be answered by CCS.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Normalize shape and intent separately

```
Shapes: single-core live debug | multicore live debug |
        flash-programming session | other standalone fallback
Intent: live debug only | flash only | flash then debug from flash
```

### 3. Apply the CCS-first observational rule before live-session routing

Apply the **CCS-first observational rule**.
See `references/authoring-procedure.md`.

### 4. Keep the minimum routing sequence inline

Use this order for the minimum safe standalone routing path:
1. normalize shape separately from programming/debug intent
2. apply the **CCS-first observational rule**
3. preserve any explicit core instance identity
4. decide whether startup/debug context already exists
5. choose the downstream route from the shape + intent combination
6. if flash is involved and startup context is missing, establish the required startup path before flash routing

| Shape + intent | Route |
| --- | --- |
| observational request when the **CCS-first observational rule** applies | `s32debugger-ccs-execution-router` |
| single-core + live debug | `s32debugger-start-singlecore-standalone-live-debug-session` |
| multicore + live debug | `s32debugger-start-multicore-standalone-live-debug-session` |
| flash-only request | establish needed startup context if missing, then `s32debugger-flash-programming` |
| flash then debug from flash | establish matching startup context first, then `s32debugger-flash-programming` |

### 5. Preserve explicit identity and startup-context rules

```
Keep: explicit core instance such as M7_0 or A53_0_0
Use:  normalized core family only for GDB variant selection when needed
Rule: flash programming is not always a zero-startup path
Rule: apply the **CCS-first observational rule**
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Route standalone S32Debugger requests only.
- Classify request shape and programming/debug intent before choosing a path.
- Preserve explicit target identity such as `M7_0` when present.
- Keep fallback behavior minimal and temporary.
- Apply the **CCS-first observational rule** for observational requests.

**Destructive actions**
- Default to routing, not leaf execution.
- Do not embed detailed flash, single-core, or multicore execution logic here.
- Do not assume flash programming is a zero-startup path when connected context
  is still missing.

**Refuse-and-escalate**
- If shape or intent is still ambiguous, ask only the smallest missing routing
  question.
- If the **CCS-first observational rule** applies, stop live-session routing
  and hand off to `s32debugger-ccs-execution-router`.
- If flash programming is requested but no connected startup context exists,
  state that startup must be established first and then route accordingly.
- If authoritative family-context values are needed for downstream init or
  config correctness, defer to `s32debugger-resolve-core-name-from-context`
  rather than guessing.
- If the request is already clearly single-core, multicore, or flash-specific,
  stop routing and hand off immediately to the dedicated downstream skill.

**Routing rules**
- Preserve explicit core identity such as `M7_0` rather than collapsing it to a
  family-only token.
- Apply the **CCS-first observational rule** before any GDB routing.
- Use the normalized core family only for GDB-variant selection when routing or
  startup selection depends on it.
- Interactive/live/keep-open requests should prefer bridge-backed downstream
  startup.
- When routing to a bridge-backed downstream live-debug flow, treat the bridge
  port as a separate local control port that must not collide with the
  generated config's target GDB server port or CCS port.
- Flash execution remains delegated; do not embed the detailed `s32flash.py`
  procedure here.

**Do**
- Keep request shape and programming/debug intent separate.
- Preserve explicit core identity when available.
- Prefer bridge-backed downstream startup for interactive keep-open requests.
- Apply the **CCS-first observational rule** before choosing a live-session path.

**Do not**
- Choose the GDB variant from the SoC alone when the core family is known.
- Collapse `M7_0` to plain `M7` and lose instance identity.
- Route directly to flash execution as if startup context already exists when
  it does not.
- Start, prepare, or inspect a GDB live-session path when the
  **CCS-first observational rule** applies.

### Clarifying-question priority

Ask only what still blocks route selection:
1. does the **CCS-first observational rule** apply?
2. if yes, is an interactive session already active and explicitly to be
   reused?
3. otherwise: live debug only, flash only, or flash then debug from flash?
4. single-core or multicore?
5. does connected GDB/GTA context already exist, or must startup be established?
6. which exact core instance starts first, if topology matters?

### Result contract

A good routing result should contain:
- normalized shape
- normalized programming/debug intent
- chosen execution path
- whether startup context already exists or must be established
- preserved explicit core identity when present
- smallest missing blocker

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm the request shape is classified explicitly.
2. Confirm the programming/debug intent is classified explicitly.
3. Verify explicit core identity is preserved when present.
4. Verify the **CCS-first observational rule** was applied correctly.
5. Verify the chosen execution path matches both shape and intent.
6. Verify flash requests account for whether startup/debug context already
   exists or must be established first.
7. If a bridge-backed downstream live session is chosen, verify the downstream
   path preserves port separation between the bridge port and any generated
   target transport ports.
8. Return normalized shape, normalized intent, selected GDB variant when
   relevant, chosen execution path, short reason, fallback status, and any
   missing blocker.

## Out of scope

- Detailed execution of the single-core, multicore, or flash leaf workflow.
- Embedding the detailed `s32flash.py` procedure directly in the router.
- Using GDB `load` as a substitute for flash programming.
- Asking extra questions when the route is already obvious.
- Violating the **CCS-first observational rule**.

## See Also

- `references/authoring-procedure.md` - routing rules, flash-context handling,
  and fallback policy.
- `references/examples.md` - quick routing examples and anti-patterns.
- Related skills: `s32debugger-start-singlecore-standalone-live-debug-session`,
  `s32debugger-start-multicore-standalone-live-debug-session`,
  `s32debugger-flash-programming`, `s32debugger-resolve-gdb-variant`,
  `s32debugger-resolve-core-name-from-context`,
  `s32debugger-ccs-execution-router`
