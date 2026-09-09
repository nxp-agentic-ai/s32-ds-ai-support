---
name: s32debugger-start-multicore-standalone-live-debug-session
description: >
  Execute the dedicated standalone S32Debugger multicore live-debug workflow.
  Use this whenever the user wants a multicore standalone session, names
  multiple cores or GDB clients, needs boot-core-first startup, wants separate
  bridge/control per core, or wants a multicore session kept open for
  follow-up commands after startup and per-client validation.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: '[s32debugger-generate-gdb-config-file, s32debugger-resolve-core-name-from-context, s32debugger-resolve-gdb-variant]'
  tags: '[s32debugger, multicore, execution]'
---

# S32Debugger Start Multicore Standalone Live Debug Session

Execute the dedicated multicore standalone live-debug workflow. This skill is
for already-classified multicore requests: preserve explicit per-core identity,
start the boot core first (which launches GTA automatically), validate it
before any secondary startup, and keep the multicore session open for
follow-up control.

## When to use

Use this skill when:
- The request is clearly for one multicore standalone S32Debugger session.
- The user names multiple cores or GDB clients and needs boot-core-first
  startup.
- The user wants separate config, bridge, and later control per core, with the
  session left open after validation.

Do **not** use this skill for:
- Requests that are really single-core or still ambiguous about topology; use
  the standalone router or ask the smallest missing multicore question.
- Improvising mixed-family multicore handling when one supported variant policy
  is not clearly justified.

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Confirm topology and explicit client identities

```
Need: boot_core, secondary_cores, per-core client names, per-core ELF intent
Rule: preserve explicit client identity from the first start_gdb call onward
```

### 3. Build one startup path per client

```
Per client: one generated base config (bridge embedded), one unique bridge port
Note:       the first control.start_gdb launches GTA automatically; later
            clients reuse the same GTA
```

### 4. Keep the minimum multicore startup sequence inline

Use this order for the minimum safe multicore startup path:
1. start the boot-core GDB client first with `control.start_gdb` (it launches GTA automatically)
2. validate boot-core bridge/session readiness
3. start one secondary client with `control.start_gdb`
4. validate that secondary client
5. repeat secondary start/validate serially for each remaining client
6. keep the session open unless the user asks to stop it

```
Order: boot-core start -> boot-core validation -> secondary start/validate ->
       next secondary
Result: keep the session open unless the user asks to stop it
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Execute only the dedicated multicore live-debug workflow.
- Preserve explicit per-core identity, one generated config per client, and one
  bridge port per client.
- Use one shared GDB variant policy only when all participating clients clearly
  map to the same supported variant.
- Validate each client independently before reporting success.

**Destructive actions**
- Default to keeping the multicore session open after successful startup.
- Do not reuse one config across multiple GDB clients.
- Do not reuse one bridge port across multiple GDB clients.
- Do not start secondary clients before boot-core readiness is confirmed.

**Refuse-and-escalate**
- If the request no longer looks multicore, route back to the standalone router
  instead of forcing it through this workflow.
- If topology is incomplete, ask only for the smallest missing detail, usually
  boot core or secondary-core identity.
- If requested cores do not clearly share one supported variant policy, stop
  and clarify rather than improvising mixed-family behavior.
- For authoritative family strings or low-level first-core vs subsequent-core
  init rules, defer to the family-context and probe-connection skills rather
  than reconstructing them here.

**Do**
- Start the boot-core GDB first (this launches GTA automatically) and validate
  bridge responsiveness before any secondary startup.
- Start secondary clients serially and validate each one.

**Do not**
- Report success before per-client validation completes.
- Drift into generic router behavior after execution is already clear.
- Close the session automatically after startup succeeds.

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm topology is complete and the boot core is explicitly identified.
2. Verify one generated base config, one unique bridge port, and one explicit
   client identity exist per GDB client.
3. Verify the chosen GDB variant policy is justified across all participating
   cores.
4. Verify the boot core is started first (GTA launches automatically with it)
   and its readiness is validated before any secondary startup.
5. Verify secondary clients are started and validated serially.
6. Return the selected templates, GDB variant policy, per-client config and
   bridge details, boot-core result, secondary results, per-client validation,
   and confirmation that the session remains open.

## Out of scope

- Using a single config or single bridge endpoint for multiple clients.
- Starting secondaries before the boot core is proven ready.
- Improvising unsupported mixed-family multicore handling.
- Reclassifying a clearly multicore execution request into a generic router
  conversation.

## See Also

- `references/authoring-procedure.md` - topology rules, startup ordering, and
  failure handling.
- `references/examples.md` - quick multicore scenarios and anti-patterns.
- Related skills: `s32debugger-start-standalone-live-session`,
  `s32debugger-resolve-gdb-variant`,
  `s32debugger-resolve-core-name-from-context`,
  `s32debugger-connect-gdb-to-s32-debug-probe`,
  `s32debugger-error-resolution`
