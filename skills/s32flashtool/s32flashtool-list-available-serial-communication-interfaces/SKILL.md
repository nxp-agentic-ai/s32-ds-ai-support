---
name: s32flashtool-list-available-serial-communication-interfaces
description: Enumerate available UART/CAN/Ethernet ports that S32FlashTool command-line application (CLI) can use for communication.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: s32flashtool
  depends_on: '["s32flashtool-agent-rules-minimal", "s32flashtool-workflow-index"]'
  tags: '["s32flashtool", "cli", "discovery", "serial", "uart", "can", "ethernet", "read-only"]'
---

# List available serial communication interfaces with S32FlashTool

Use the the `cli_build_<op>` + `cli_execute` actions MCP tool to ask S32FlashTool itself to enumerate the available serial communication ports.

## When to use
- When the user asks which UART/CAN/Ethernet interfaces are available to S32FlashTool.
- When the user asks to list the UART/CAN/Ethernet ports available.
- Before asking the user to guess a COM port.
- Before attempting mcuid, ping, flash read/write, or RCON operations.

## When not to use

Do not use this skill for full hardware setup discovery - use s32flashtool-discover-hardware-setup for that.

## Shared references
- Apply shared rules from resource `s32flashtool-agent-rules-minimal/SKILL.md`.
- Use `s32flashtool-workflow-index/SKILL.md` to select the correct workflow.

## Quickstart

Enumerate endpoints S32FlashTool can see:

```
Tool:   the `cli_build_<op>` + `cli_execute` actions
Args:   s32flashtool_folder=<abs path>
        interface=uart|can|ethernet
        port="?"
Output: list of endpoint labels (e.g. `COM15,ftdi`) as printed by the tool.
```

Present labels verbatim; do not reformat. If empty, report the empty
result and ask the user to check hardware/drivers.

## Tool
- the `cli_build_<op>` + `cli_execute` actions

## Parameters
- s32flashtool_folder: mandatory, absolute path to the S32FlashTool installation
- interface: mandatory, one of uart, can, ethernet
- port: mandatory, use `?`
- timeout: optional per-query timeout in seconds

## Behavior
The tool uses the S32FlashTool CLI enumeration form:
- -i uart -p ?
- -i can -p ?
- -i ethernet -p ?

The interface must always be specified - the CLI requires it for port enumeration.

## Guidance
- Prefer this tool before falling back to OS-level serial-port enumeration when the requirement is specifically use S32FlashTool.
- If S32FlashTool reports that listing is unsupported, say so clearly and then fall back to Windows enumeration as a secondary method.
- Do not guess ports or adapters.
---

## Guardrails

**Scope**
- Only enumerate UART/CAN/Ethernet endpoints available to S32FlashTool via
  the `cli_build_<op>` + `cli_execute` actions with `port = "?"`.
- Do not attempt communication, do not read MCUID, do not open an RPC session.

**Destructive actions**
- Read-only enumeration. Must never invoke a writing tool.

**Refuse-and-escalate**
- Missing installation folder or interface: stop and ask. Recovery: request the absolute path and
  one of `uart | can | ethernet`.
- If no ports are returned, do not invent one. Recovery: report the empty result and ask the user
  to plug the device or check drivers.

**Output contract**
- Present the raw port list from the tool. Preserve tool-formatted labels
  (e.g. `COM15,ftdi`); do not reformat them.

## Validation loop

1. Exactly one invocation of the `cli_build_<op>` + `cli_execute` actions with `port = "?"`
   is made per requested interface. Fail on more than one, or on any other tool
   call.
2. The tool's port list is presented verbatim (labels such as `COM15,ftdi` are
   preserved unmodified). Fail if the response reformats or invents labels.
3. If the returned list is empty, the response reports the empty result and
   asks the user to plug hardware / check drivers instead of guessing.
   Fail if any port name is invented.
4. No follow-up read/write/program operation is triggered from this skill.
   Fail on any destructive tool call.

## Out of scope

- Talking to a target device. This skill only enumerates endpoints.
- Reading MCUID, flash ID, or flash contents. Use the matching read skill.
- Programming, erasing, or writing anything. Use the matching operation skill.
- Inventing a port name when the tool returns an empty list.
