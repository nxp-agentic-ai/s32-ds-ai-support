---
name: freemaster-lite-configuration-file
description: >
  Creates, edits, validates, and explains FreeMASTER Lite .fmcfg configuration
  files. Use whenever the user wants to define target connections, load ELF
  symbols, declare variables, configure file-system access rules, set up SSL,
  or enable mock API in a reusable project file. Triggers on "create .fmcfg",
  "edit fmcfg", "fmcfg format", "FreeMASTER connection string", "RS232 port
  speed", "add ELF to FreeMASTER", "FreeMASTER variables", "mock_api config".
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: freemaster
  tags: '[freemaster, configuration, fmcfg, setup]'
---

# FreeMASTER Lite Configuration File

A `.fmcfg` file is a JSON file that tells `fmlite.exe` how to start: port,
web content location, physical connections, ELF symbols, and variables. Create
it before launching with `freemaster-lite-start-server`.

> **Tip:** Fastest approach — use the FreeMASTER Desktop Application
> (File -> Export -> FreeMASTER Service Configuration) to export a ready-to-use
> template from an existing project.

> **Key rule:** JSON keys are case-sensitive. Missing properties **disable**
> the corresponding feature (unlike CLI flags, which use defaults).

## When to use

- Creating, inspecting, fixing, or validating a `.fmcfg` file.
- Defining target connections, variables, file-system rules, SSL, or mock API.
- Building a reusable project configuration instead of one-off CLI flags.

Do **not** use this skill for one-off launch flags (`freemaster-lite-command-line-arguments`),
starting/stopping the service (`freemaster-lite-start-server` /
`freemaster-lite-stop-server`), or JSON-RPC calls (`freemaster-lite-jsonrpc-api`).

## Quick start

Minimal valid `.fmcfg` for a serial connection:

```json
{
  "port": 8090,
  "connections": [
    {
      "connection_string": "RS232;port=COM3;speed=115200",
      "name": "UART on COM3",
      "elf": "C:/path/to/application.elf"
    }
  ]
}
```

Save as `my-project.fmcfg` at an absolute path and pass it to `fmlite.exe`.

## Root Properties

| Property | Type | Description |
|----------|------|-------------|
| `port` | number | Server port (default if omitted: `8090`) |
| `host` | string | Server host address |
| `web_root` | string | Path to static content folder |
| `open_path` | string | Browser path opened on startup |
| `bonjour` | string | Bonjour service name |
| `node_red` | string \| boolean | Node-RED settings file or `true` for defaults |
| `queue_limit` | number | JSON-RPC queue max size |
| `health` | string | Health check endpoint |
| `mock_api` | string \| boolean | JS mock file path or `true` for embedded mock |
| `connections` | array | Named physical connections to the target |
| `variables` | array | Project variables |
| `dirs` | array | File-system access rules |
| `ssl` | object | SSL key/cert paths |

## Connections

Each connection object requires:

| Field | Required | Description |
|-------|----------|-------------|
| `connection_string` | yes | Transport string (see formats below) |
| `name` | yes | Friendly name |
| `description` | no | Optional description |
| `elf` | no | ELF file for symbol resolution |

**RS232 format:** `RS232;port=<port>;speed=<baud>[;key=value...]`

Mandatory: `port` and `speed`. All others (timeout values, parity, stop bits,
RTS, DTR) fall back to defaults. See `references/examples.md` for timeout
customization.

**Other supported transports:** `CAN`, `NET`, `DAP`, `JLINK`, `HCS`, `EONCE`,
`PDBDM`, `LIN`, `TCPCOM`. Linux is limited to `RS232`, `NET`, `TCPCOM`.

## Variables

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Variable name |
| `addr` | number \| string | yes | Address or ELF symbol name |
| `type` | string | yes | `int`, `uint`, `float`, `double`, `fract`, `ufract` |
| `size` | number | yes | `1`, `2`, `4`, or `8` bytes |
| `shift` | number | no | Right-shift for integer variables |
| `mask` | number | no | AND mask applied after shifting |
| `q_m` | number | fract/ufract | Integer bits |
| `q_n` | number | fract/ufract | Fractional bits |

For `fract`/`ufract`: `q_m + q_n` must equal `8*size - 1` (fract) or `8*size` (ufract).

## Mock API

Use `mock_api: true` for development without hardware:

```json
{ "port": 8090, "mock_api": true }
```

## Guardrails

**Scope**
- This skill only reads and writes `.fmcfg` files in the user's project
  directory. It does not launch processes or modify embedded firmware.

**Destructive actions**
- Writing a new `.fmcfg` will overwrite an existing file at that path.
  Confirm the path with the user before writing.

**Secrets**
- SSL key and cert paths appear in the config. Do not log or display the
  contents of referenced key files.

**Refuse-and-escalate**
- If the connection string format is ambiguous (e.g. non-RS232 plugin the
  user has not used before), ask for confirmation or refer to the Desktop
  Application export flow for the authoritative string format.

## Validation loop

1. Confirm the file parses as valid JSON (`json.loads` or equivalent).
2. Confirm `connections[].name` is present on every connection object —
   missing `name` causes a startup error.
3. Confirm `connection_string` uses semicolon-separated `key=value` format
   (not colon-separated).
4. After launching with `freemaster-lite-start-server`, call the
   `IsCommPortOpen` method to confirm the connection resolves.

## Out of scope

- One-off launch flags — use `freemaster-lite-command-line-arguments`.
- Starting or stopping the service — use `freemaster-lite-start-server` /
  `freemaster-lite-stop-server`.
- JSON-RPC API usage — use `freemaster-lite-jsonrpc-api`.

## See Also

- `references/examples.md` — full config, TCP/IP, CAN, timeout, fractional
  variable, and dirs examples
- `freemaster-lite-start-server` — launch FreeMASTER Lite with this file
- `freemaster-lite-jsonrpc-api` — interact with the running service
