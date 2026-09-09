---
name: s32debugger-generate-gdb-config-file
description: >
  Generate a real S32Debugger GDB config `.txt` artifact from an S32Debugger
  Python example template by using the dedicated MCP tool. Use this whenever
  the user wants a base config file before later startup, asks to generate a
  config from a `SingleCore`, `MultiCore`, or `FlashProgrammer` example,
  provides `soc_family` / `script_type` / `template_name` plus probe/core/ELF
  overrides, or needs a config artifact that will later be passed into
  `control.start_gdb` or a standalone live-debug flow.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32debugger
  depends_on: '[s32debugger-discover-installation, s32debugger-navigate-installation, s32debugger-resolve-core-name-from-context, s32debugger-resolve-gdb-variant]'
  tags: '[s32debugger, config, generation]'
---

# S32Debugger Generate GDB Config File

Generate a real S32Debugger GDB config `.txt` artifact from a Python example
template using the dedicated MCP tool. This skill is for producing the config
file that later startup flows consume, not for hand-writing arbitrary configs
or launching the debug session itself.

## When to use

Use this skill when:
- The user wants a base S32Debugger GDB config `.txt` file.
- The request references `soc_family`, `script_type`, `template_name`, probe
  IP, core identity, ELF path, or other config overrides.
- The generated artifact will later be used with `control.start_gdb` or a
  standalone live-debug workflow.

Do **not** use this skill for:
- Hand-writing a manual GDB config by default.
- Starting the GDB client or creating the live session after generation.

## Available Capabilities

| Type | Name | Invocation |
| --- | --- | --- |
| Action | `generate.gdb_config_file` | `execute_action(action_name="generate.gdb_config_file", params={...})` |

## Quickstart

### 1. Mandatory reference read

Before using this skill, read:
- `references/authoring-procedure.md`
- `references/examples.md`

Do not continue until those files have been reviewed.
### 2. Select the source example template

```
Input:   soc_family + script_type + optional template_name
Prefer:  exact Python example match by family, script type, core, and lockstep
Fallback: closest grounded example only with explicit explanation and approval
```

### 3. Resolve important overrides before generation

```
Need: probe_ip, soc_name, core_name, core_id, cluster_id, lockstep,
      file_debug, init_script, ports, reset/security/lifecycle options
```

### 4. Generate the `.txt` artifact with the dedicated action

```
Action: generate.gdb_config_file
Output: generated GDB config file path (with REST bridge embedded) for later debugger startup
```

## Guardrails

**Mandatory reference rule**
- Read the listed reference files before selecting a branch, generating output,
  or producing the final answer.
- Treat the references as part of the skill, not as optional supplemental
  notes.
**Scope**
- Generate the GDB config artifact only.
- Prefer the dedicated action over manual reconstruction.
- Treat the Python example template as the source and the generated `.txt` as
  the output artifact.
- Resolve authoritative family-context values first when `core_name`,
  `soc_name`, or init-sensitive inputs are uncertain.
- Preserve any target transport ports emitted by the generated config so the
  chosen bridge port stays distinct from them.

**Destructive actions**
- Default to generation only; do not expand into startup execution here.
- Do not silently substitute a different example template.
- Do not assume a downstream startup may safely reuse any port already present
  in the generated config for the bridge.

**Refuse-and-escalate**
- If no exact template exists, explain the closest grounded example and ask
  before using it as a fallback base.
- If required target/core/probe inputs are missing, ask only for the fields
  that block correct generation.
- If authoritative family-context values are uncertain, resolve them before
  finalizing init-sensitive overrides.
- If the user wants to start the session after generation, hand off to the
  downstream startup skills instead of collapsing both steps.

**Do**
- Use `generate.gdb_config_file` as the primary path.
- Describe the result as a generated GDB config `.txt` file with an embedded
  REST bridge on the requested port.
- Preserve user-supplied target and path overrides carefully.
- Call out the generated target transport ports when they are known and matter
  to bridge-port selection.

**Do not**
- Treat the tool as plain text substitution.
- Confuse the source Python example with the final config artifact.
- Silently invent a config when the action path is available.

## Validation loop
0. Confirm the required reference files were reviewed before executing the
   workflow or finalizing the answer.
1. Confirm the source template identity is exact or explicitly approved as a
   fallback.
2. Verify required overrides are collected and authoritative family-context
   values are resolved when needed.
3. Verify the generation path uses `generate.gdb_config_file`.
4. Verify the returned path is described as the generated GDB config artifact.
5. Verify the response preserves any generated target transport ports that the
   bridge port must not reuse.
6. Verify the response explains the intended next-step handoff to the
   downstream `control.start_gdb` flow without performing it here.
7. Return the selected template, exact-vs-fallback status, key overrides,
   generated `.txt` path, any known generated transport ports, and intended
   next use.

## Out of scope

- Hand-writing a GDB config by default.
- Starting the GDB client or executing a live-debug flow here.
- Silently swapping templates without explanation.

## See Also

- `references/authoring-procedure.md` - template selection, override
  collection, and downstream handoff.
- `references/examples.md` - common requests, fallback behavior, and
  anti-patterns.
- Related skills: `s32debugger-discover-installation`,
  `s32debugger-navigate-installation`,
  `s32debugger-resolve-core-name-from-context`,
  `s32debugger-resolve-gdb-variant`,
  `s32debugger-start-standalone-live-session`
