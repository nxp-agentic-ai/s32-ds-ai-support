---
name: s32debugger-connect-gdb-to-s32-debug-probe
description: >
  Execute the low-level GDB CLI procedure to connect to an S32 Debug Probe.
  Use this whenever the user wants raw GDB probe-connection steps, needs to
  know which Python globals must be set, needs the correct init script for
  bareboard versus attach scenarios, wants the exact `board_init()` /
  `core_init()` ordering, or asks about `load` versus `symbol-file` behavior
  outside the higher-level standalone session workflows.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: '[s32debugger-resolve-core-name-from-context, s32debugger-resolve-gdb-variant]'
  tags: '[s32debugger, gdb, connection]'
---

# S32Debugger Connect GDB to S32 Debug Probe

Provide the low-level GDB CLI procedure for connecting directly to an S32 Debug
Probe. This skill covers scenario selection, mandatory Python globals, init
script choice, `board_init()` / `core_init()` ordering, and the distinction
between memory-loading, symbols-only attach, and flash-programming flows.

## When to use

Use this skill when:
- The user wants raw GDB CLI steps instead of a higher-level standalone
  session workflow.
- The user asks which init script to source for bareboard, attach-first,
  attach-running, or multicore follow-on scenarios.
- The user wants the exact rules for mandatory globals, init ordering,
  `load`, and `symbol-file`.

Do **not** use this skill for:
- High-level standalone startup orchestration; use the standalone live-session
  skills.
- Physical flash programming through GDB `load`; use
  `s32debugger-flash-programming`.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.

### 2. Resolve the low-level scenario first

```
Choose: bareboard load/debug | attach from first instruction |
        attach to running target | multicore follow-on | flash programming
Need:   authoritative _SOC_NAME, _CORE_NAME, and probe IP
```

### 3. Set mandatory globals before sourcing any init script

Set these before any `source` step, in this order:
1. `_PROBE_IP`
2. `_SOC_NAME`
3. `_CORE_NAME`

```gdb
py _PROBE_IP = "s32dbg:192.168.1.100"
py _SOC_NAME = "S32G274A"
py _CORE_NAME = "M7_0"
```

### 4. Source the matching script and initialize in order

For full bareboard bring-up, preserve this sequence:
1. `source "<install>/S32Debugger/Debugger/scripts/<family>/<family>_generic_bareboard.py"`
2. `py board_init()`
3. `py core_init()`

```gdb
source "<install>/S32Debugger/Debugger/scripts/<family>/<family>_generic_bareboard.py"
py board_init()
py core_init()
```

Then:
- use `load` plus `symbol-file` for memory-loading scenarios
- use `symbol-file` only for attach scenarios
- hand physical flash writes off to `s32debugger-flash-programming`

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Cover the low-level GDB CLI probe-connection procedure only.
- Require authoritative `_SOC_NAME` and `_CORE_NAME`; do not approximate them.
- Keep bareboard, attach, symbols-only, and flash-programming behavior clearly
  separated.
- Preserve the multicore rule: first core does `board_init()` plus
  `core_init()`, subsequent cores do `core_init()` only.

**Destructive actions**
- Default to explaining the exact CLI procedure and script choice.
- Do not use GDB `load` as a substitute for physical flash programming.
- Do not call `board_init()` more than once in a multicore session.

**Refuse-and-escalate**
- If `_SOC_NAME` or `_CORE_NAME` is uncertain, resolve them first instead of
  guessing, typically through `s32debugger-resolve-core-name-from-context`.
- If the user asks for flash writes or debug-from-flash behavior, route to the
  flash-programming skills rather than improvising with `load`.
- If the request is really for a full standalone startup flow, redirect to the
  higher-level session skills.
- If the scenario intent is ambiguous, ask whether the goal is bareboard
  load/debug, attach from first instruction, attach to a running target,
  flash programming, or multicore follow-on.

**Do**
- Set `_PROBE_IP`, `_SOC_NAME`, and `_CORE_NAME` before sourcing any init
  script.
- Use `s32dbg:<probe-ip>` for `_PROBE_IP`.
- Use `symbol-file` explicitly when symbols are needed.

**Do not**
- Source an init script before the mandatory globals are set.
- Use attach scripts for memory-loading scenarios.
- Treat this low-level flow as a replacement for the higher-level startup
  skills.

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm the scenario is classified correctly: bareboard load/debug,
   attach-first-instruction, attach-running, multicore follow-on, or flash.
2. Verify `_PROBE_IP`, `_SOC_NAME`, and `_CORE_NAME` are set before sourcing the
   init script.
3. Verify `_SOC_NAME` and `_CORE_NAME` come from authoritative family context.
4. Verify the chosen init script matches the scenario and that
   `board_init()` / `core_init()` ordering is correct.
5. Verify `load` is used only for memory-loading flows and `symbol-file` is
   used correctly for attach or debug symbolization.
6. Return the chosen script, required globals, init ordering, load-vs-symbols
   decision, and any flash-programming handoff.

## Out of scope

- High-level standalone debug-session orchestration.
- S32DS GUI launch configuration flows.
- Treating GDB `load` as a flash-programming primitive.
- Guessing `_SOC_NAME` or `_CORE_NAME`.

## See Also

- `references/authoring-procedure.md` - mode selection, init-script mapping,
  and multicore rules.
- `references/examples.md` - CLI examples, anti-patterns, and quick checks.
- Related skills: `s32debugger-resolve-core-name-from-context`,
  `s32debugger-start-singlecore-standalone-live-debug-session`,
  `s32debugger-start-multicore-standalone-live-debug-session`,
  `s32debugger-flash-programming`
