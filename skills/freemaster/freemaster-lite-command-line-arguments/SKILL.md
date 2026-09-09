---
name: freemaster-lite-command-line-arguments
description: >
  Covers FreeMASTER Lite command-line options for fmlite.exe / fmlite.bin.
  Use whenever the user asks how to start FreeMASTER Lite from the command
  line, needs CLI flags such as --port, --host, --mock_api, --web_root, or
  --no-open_path, wants headless startup options, or needs to understand how
  named options interact with a .fmcfg configuration file.
license: LA_OPT_Online Code Hosting NXP_Software_License
metadata:
  author: NXP
  version: "1.0.0"
  product: freemaster
  tags: '[freemaster, cli, command-line, startup]'
---

# FreeMASTER Lite Command-Line Arguments

`fmlite.exe` (Windows) / `fmlite.bin` (Linux) is the FreeMASTER Lite
executable. It accepts optional flags for one-off overrides such as port,
host, and mock API. For persistent project settings, use a `.fmcfg` file.

## When to use

- Starting FreeMASTER Lite with one-off flags without a project file.
- Quick headless or local test setup using `--mock_api`.
- Understanding how CLI flags interact with a `.fmcfg` file.
- Disabling the automatic browser open (`--no-open_path`).

Do **not** use this skill for creating or editing a `.fmcfg` file
(`freemaster-lite-configuration-file`), calling JSON-RPC after the service is
running (`freemaster-lite-jsonrpc-api`), or building browser/Node.js clients
(`freemaster-lite-web-application`).

## Quick start

```text
# Default startup (opens browser at http://127.0.0.1:8090)
fmlite.exe

# Custom port, no browser
fmlite.exe --port 9000 --no-open_path

# Mock API — no hardware required
fmlite.exe --mock_api

# Load a project file (all named flags are ignored)
fmlite.exe C:\workspace\my_project\freemaster.fmcfg

# Fully headless
fmlite.exe --no-open_path --no-bonjour --no-web_root --port 8090
```

## Usage

```
fmlite.exe [options] [configuration file]
```

When a configuration file path is provided, **all named options are ignored** —
the file takes full control.

## Options Reference

| Short | Long | Arg | Description | Default |
|-------|------|-----|-------------|---------|
| `-V` | `--version` | — | Print version and exit | — |
| `-p` | `--port` | `<port>` | Server port | `8090` |
| `-h` | `--host` | `<host>` | Server host address | `0.0.0.0` |
| `-w` | `--web_root` | `<path>` | Static content folder | `./html/` |
| — | `--no-web_root` | — | Disable static content serving | — |
| `-o` | `--open_path` | `<path>` | Browser path on startup | `/` |
| — | `--no-open_path` | — | Disable automatic browser open | — |
| `-b` | `--bonjour` | `<name>` | Bonjour service name | `FreeMASTER Lite` |
| — | `--no-bonjour` | — | Disable Bonjour | — |
| `-r` | `--node_red` | `<path>` | Node-RED settings file | embedded config |
| — | `--no-node_red` | — | Disable Node-RED | — |
| `-q` | `--queue_limit` | `<size>` | JSON-RPC queue max size | — |
| `-s` | `--health` | `<route>` | Health check endpoint | `/health` |
| — | `--no-health` | — | Disable health endpoint | — |
| `-m` | `--mock_api` | `[file]` | Mock JSON-RPC API; optional custom JS | — |

Negated forms (`--no-<option>`) disable the feature; omitting the flag uses
the default.

## Guardrails

**Scope**
- This skill covers launch flags only; it does not modify any project file.

**Destructive actions**
- No file writes or process termination. Starting a second instance on the
  same port will fail — check if FreeMASTER Lite is already running first.

**Secrets**
- No credentials involved.

**Refuse-and-escalate**
- If the user needs persistent connection, variable, or SSL settings, stop
  and redirect to `freemaster-lite-configuration-file` — CLI flags cannot
  express those settings.

## Validation loop

1. Run `fmlite.exe --version` to confirm the executable is found and prints a
   version string.
2. Start with the intended flags; confirm the server prints
   `FreeMASTER Lite server is running at http://<host>:<port>`.
3. If `--no-open_path` is used, verify no browser window opens.
4. If `--mock_api` is used, confirm a WebSocket session connects and mock
   responses are returned from a `GetAppVersion` call.

## Out of scope

- Creating or editing `.fmcfg` project files — use `freemaster-lite-configuration-file`.
- Starting or stopping the service programmatically — use `freemaster-lite-start-server`
  or `freemaster-lite-stop-server`.
- JSON-RPC API calls once the service is running — use `freemaster-lite-jsonrpc-api`.

## See Also

- `freemaster-lite-configuration-file` — full project configuration with
  connections, variables, and SSL
- `freemaster-lite-start-server` — programmatic launch workflow
- `freemaster-lite-jsonrpc-api` — API interaction after the service is running
