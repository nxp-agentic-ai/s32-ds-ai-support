# S32 Design Studio AI Support

![python-badge](https://img.shields.io/badge/Python-3.11+-green)
![fastmcp-badge](https://img.shields.io/badge/FastMCP-3.3.1-orange?logo=fastmcp)

A suite of enablers (MCP Servers, Tools, Skills, Vectorized Knowledge Base) that give AI agents the capabilities to work efficiently with NXP development tools.

The toolkit extends the S32 ecosystem tools - S32 Design Studio, S32 Configuration Tools, S32 Debugger, S32 Flash Tool, S32Trace, S32SDAF, FreeMASTER Lite and the bundled compilers - with AI-ready integrations that can be consumed by MCP-compatible agents. When connected to assistants such as Claude, GitHub Copilot, VS Code Copilot, Cursor, Goose, or Codex, developers can interact with S32 tools using natural language to build a project, regenerate driver code, configure pins and clocks, flash a board, start a debug session, analyze a trace or search NXP documentation.

## Features

- Gateway composition - all servers accessible through a single MCP connection
- Namespace-prefixed tool mounting (`nxp_<name>`) to avoid naming conflicts
- Dynamic server discovery via `mcp.servers` entry-points
- Opt-out mounting semantics (`disabled: true` per server)
- Shared YAML-based configuration model
- Skills system - markdown skill files served as MCP resources for agent guidance
- Vectorized knowledge base (LanceDB + local `bge-base-en-v1.5` embeddings) for offline semantic search over NXP documentation - no cloud calls, no data leaving the machine
- Self-installing `.pyz` installer with per-package selection and automatic agent registration
- Standalone mode - any single server can run on its own with its own config file

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [How to Install](#how-to-install)
- [Repository Layout](#repository-layout)
- [Registering the MCP servers into AI Agents](#registering-the-mcp-servers-into-ai-agents)
- [Skills](#skills)
- [Configuration](#configuration)
- [Knowledge Base](#knowledge-base)
- [Building from Source](#building-from-source)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Community](#community)

---

## Prerequisites

| Prerequisite | Version | Link |
|--------------|---------| ---- |
| Python | 3.11+ | [Download](https://www.python.org/downloads/) |
| S32 Design Studio | 3.6.11+ | [Download](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide:S32-DESIGN-STUDIO-IDE)<br>Includes: S32 Debugger, S32 Configuration Tools, S32 Trace, S32 SDAF |
| S32 Design Studio MCP Integration plugin | 1.0.1+ | Bundled with S32 Design Studio 3.6.11+ or available for installation via Extensions and Updates in older versions starting with 3.6.5 |
| FreeMASTER Lite | 1.5.0+ | [Download](https://www.nxp.com/design/design-center/software/development-software/freemaster-run-time-debugging-tool:FREEMASTER) |
| S32 Flash Tool | 2.4.3+ | [Download](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide/s32-flash-tool-for-s32-platform:S32FT-S32PLATFORM) |
| AI Agent (MCP compatible) | latest |  Any MCP-compatible agent that can launch a standalone MCP server - such as [Claude Desktop](https://claude.ai/download), [VS Code](https://code.visualstudio.com/) or [Cursor](https://www.cursor.com/), among others |

> **Note** After installing S32 Design Studio, you must install the S32 Design Studio MCP Integration plugin from S32DS Extensions and Updates if not already installed. This plugin provides a JSON-RPC-based integration service that connects AI agents to S32 Design Studio tooling via MCP servers, enabling AI-assisted interaction. It is recommended to install this plugin on S32 Design Studio version 3.6.5 or newer.

> **Note** Please consult S32 Flash Tool User Guide found in the product installation for more information on how to configure the JSON RPC API server in S32 Flash Tool.

> **Note** NXP products above provide an API (REST/JSON RPC) for the MCP server(s) to connect to. Please consider changing the default port(s) of these APIs if they are not available on your system.

| Product | Default MCP API Port |
|--------------|---------|
| S32 Design Studio | 8088 TCP |
| FreeMASTER Lite | 8090 TCP |
| S32 Flash Tool | 51236 TCP |

---

## How to Install

### Step 1 - Install the NXP tools you plan to drive

Each MCP server is a bridge to an NXP product. Install the products relevant to your workflow (see [Prerequisites](#prerequisites) and the links in the [package table](#22---available-package-short-names)). For S32 Design Studio, also install the **S32 Design Studio MCP Integration plugin** from *Extensions and Updates*, and enable the REST/RPC API of S32 Flash Tool and FreeMASTER Lite if you plan to use them.

### Step 2 - Run the self-installing package

Open a terminal and run the self-installing package to install the NXP MCP servers on your system:

```shell
# Interactive mode: package selection, agent registration and skills copy
python s32ds-agentic-ai-installer-{version}.pyz
```

Non-interactive example - install everything into a fixed directory:

```shell
python s32ds-agentic-ai-installer-{version}.pyz --yes --dest C:/NXP/s32ds-agentic-ai
```

#### 2.1 - Installer options

| Option | Short | Description |
|--------|-------|-------------|
| `--yes` | `-y` | Non-interactive: install all packages without prompting |
| `--packages PKG,...` | `-p` | Comma-separated list of packages to install |
| `--dest DIR` | `-d` | Directory where assets (skills, models, configs) are extracted (default: `.`) |
| `--register AGENT,...` | | Register the gateway into the listed AI agents after install (`claude-desktop`, `vscode`, `cursor`). Use `none` to skip; omit to show an interactive menu |
| `--copy-skills [DIR]` | | Copy bundled skills after registration. When DIR is given, copies all skills there. Otherwise shows an interactive menu to choose which agents to copy skills to. Skills are always copied for each agent selected for registration unless `--skip-copy-skills` is given. |
| `--skip-copy-skills` | | Do not copy the skills in any directory. |
| `--no-venv` | | Install the wheels into the system Python instead of an isolated virtual environment. By default the installer creates a `.venv` inside the destination and installs into it; use this flag only when you explicitly want a system-wide install (not recommended on externally-managed distributions). |

#### 2.2 - Available package short names

| Short Name | Full Package | Description |
|------------|--------------|-------------|
| `gateway` | `nxp_mcp_gateway` | Gateway aggregator - combines all servers into one MCP endpoint |
| `knowledge` | `nxp_mcp_knowledge` | Knowledge base server with semantic search |
| `compiler` | `nxp_mcp_compiler` | LLVM/Clang and GCC compiler tools integration; Product installer - [S32 Design Studio](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide:S32-DESIGN-STUDIO-IDE) |
| `freemaster` | `nxp_mcp_freemaster` | FreeMASTER Lite integration; Product installer [FreeMASTER Lite](https://www.nxp.com/design/design-center/software/development-software/freemaster-run-time-debugging-tool:FREEMASTER) |
| `s32ct` | `nxp_mcp_s32ct` | S32 Configuration Tools integration; Product installer - [S32 Design Studio](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide:S32-DESIGN-STUDIO-IDE) |
| `s32debugger` | `nxp_mcp_s32debugger` | S32 Debugger integration; Product installers - [S32 Design Studio](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide:S32-DESIGN-STUDIO-IDE) or [S32 Debugger Standalone](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide/s32-debugger-for-s32-platform:S32DBG-S32PLATFORM) |
| `s32ds` | `nxp_mcp_s32ds` | S32 Design Studio integration; Product installer - [S32 Design Studio](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide:S32-DESIGN-STUDIO-IDE) |
| `s32flashtool` | `nxp_mcp_s32flashtool` | S32 Flash Tool integration; Product installers - [S32 Design Studio](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide:S32-DESIGN-STUDIO-IDE) or [S32 Flash Tool](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide/s32-flash-tool-for-s32-platform:S32FT-S32PLATFORM) |
| `s32sdaf` | `nxp_mcp_s32sdaf` | S32 Secure Debug Authorization Framework integration; Product installers - [S32 Design Studio](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide:S32-DESIGN-STUDIO-IDE) |
| `s32trace` | `nxp_mcp_s32trace` | S32Trace configurator integration; Product installer - [S32 Design Studio](https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide:S32-DESIGN-STUDIO-IDE) |

> **Note** Depending on the installed packages, you also need to install the corresponding tools in the S32 ecosystem that these MCP servers expose to the agents. See the links in the description column on the table above for latest versions of these products.

### Step 3 - Register the MCP servers with your AI coding agent

During installation you can register the gateway directly into Claude Desktop, VS Code, Cursor:

```shell
# Register specific agents, no menu
python s32ds-agentic-ai-installer-{version}.pyz --register claude-desktop

# Skip registration entirely
python s32ds-agentic-ai-installer-{version}.pyz --register none
```

If you skipped this step, or want to register later, use `register_agents.py` from the installation root. See [Registering the MCP servers into AI Agents](#registering-the-mcp-servers-into-ai-agents) for all variants, including manual JSON registration.

### Step 4 - Register the skills with your AI coding agent

Skills are always served as MCP resources, but agents with native skill support work best when the skill files are also on disk. Registration copies them automatically unless `--skip-copy-skills` is given:

```shell
# Copy the bundled skills into a specific folder
python register_agents.py --copy-skills ~/.claude/skills
```

See [Skills](#skills) for per-agent skill folders and manual copy instructions.

### Step 5 - Verify the installation (Optional)

Start the gateway once from the installation directory and confirm it comes up without errors:

```shell
run-mcp.bat nxp.mcp.gateway configs/gateway.stdio.yaml
```

Then restart your AI agent and ask it to list the available tools - the NXP tools appear with an `nxp_` prefix. If something is missing, see [Troubleshooting](#troubleshooting).

---

## Repository Layout

| Path | Description |
|---|---|
| `packages/` | One Python sub-package per MCP server (`mcp_gateway`, `mcp_knowledge`, `mcp_compiler`, `mcp_freemaster`, `mcp_s32ct`, `mcp_s32debugger`, `mcp_s32ds`, `mcp_s32flashtool`, `mcp_s32sdaf`, `mcp_s32trace`) plus `mcp_shared` with common infrastructure |
| `configs/` | Ready-to-use YAML configs - `gateway.stdio.yaml`, `gateway.http.yaml` and one `*.standalone.yaml` per server |
| `skills/` | Bundled agent skills, grouped per tool domain (`compiler/`, `freemaster/`, `s32ct/`, `s32debugger/`, `s32ds/`, `s32flashtool/`, `s32sdaf/`, `s32trace/`) |
| `scripts/` | Build and packaging utilities, installer sources, CI pipeline definition |
| `run-mcp.bat` / `run-mcp.sh` | Cross-platform launcher used by agent registrations |
| `SBOM-S32-DS-Agentic-AI.spdx.json` | SPDX software bill of materials for the release |
| `LICENSE`, `LICENSE_ADDENDUM` | NXP Online Code Hosting Software License and the AI Addendum |
| `RELEASE_NOTES.md` | Version history and known limitations |

## Scripts

Utility scripts live in the `scripts/` directory. See [`scripts/README.md`](scripts/README.md) for full details.

| Script | Description |
|---|---|
| `scripts/build_modules.py` | Build `.whl` wheels for all sub-packages and the root meta-package |
| `scripts/create_deploy_package.py` | Bundle wheels + assets into a single self-installing `.pyz`; version and asset list come from `scripts/installer/_manifest.py` |

---

## Registering the MCP servers into AI Agents

The gateway server (or any standalone server provided by this package) can be registered in any of the following AI agents so they can launch it automatically.

 * [Claude Desktop](https://claude.com/download) (claude-desktop)

 * [VS Code](https://code.visualstudio.com/) (vscode)
 * [Cursor](https://cursor.com/download) (cursor)

### Using the --register option of the installer

The `--register` option of the installer registers the installed gateway with your AI agents so
they can launch it automatically:

- **Config-based agents** (Claude Desktop): the installer merges an
  MCP server entry into the agent's config file (creating it if missing).
- **CLI-based agents** (VS Code): the installer invokes `code --add-mcp` so
  VS Code performs the merge itself.
- **Deeplink agents** (Cursor): the installer opens the agent's own install
  dialog with the gateway pre-filled.

The launch command is derived from the install destination at runtime
(`run-mcp.bat` / `run-mcp.sh` + `configs/gateway.stdio.yaml`), so it always
points at the correct location.

```bash
# Interactive menu (default when --register is omitted and not using --yes)
python s32ds-agentic-ai-installer-{version}.pyz

# Register specific agents, no menu
python s32ds-agentic-ai-installer-{version}.pyz --register claude-desktop

# Skip registration entirely
python s32ds-agentic-ai-installer-{version}.pyz --register none
```

### Registering after installation

There is a dedicated script that can be used for post install registration with any supported agent.
It can be found in the installation root and it is named `register_agents.py`

```shell
usage: python register_agents.py [-h] [--dest DEST] [--name NAME] [--register A,B,...] [--yes] [--list] [--dry-run]

Register the NXP MCP gateway into your AI agents (Claude Desktop, VS Code, Cursor).

options:
  -h, --help           show this help message and exit
  --dest DEST          MCP install directory containing run-mcp.bat/.sh, configs/, and skills/ (default: current directory)
  --name NAME          Server name to register in the agent configs (default: NXP-tools)
  --register A,B,...   Comma-separated agent keys to target (claude-desktop, vscode, cursor); use 'none' to skip. Omit to
                       show the interactive menu.
  --skip-register      Skip agent registration entirely (useful when only copying skills).
  --yes, -y            Do not show menus; register into all agents and/or copy skills.
  --copy-skills [DIR]  Copy bundled skills after registration. When DIR is given, copies all skills there. Otherwise shows an
                       interactive menu to choose which agents to copy skills to. Skills are always copied unless --skip-copy-skills is given.
  --skip-copy-skills   Skip the skills copy step entirely.
  --list               List all supported agents and their registration target, then exit.
  --dry-run            Show the gateway command and the per-agent target/action without writing anything.
```

Examples:
```shell
# Interactive (numbered menu):
python register_agents.py

# List all supported agents and what WOULD be written (no changes):
python register_agents.py --list
python register_agents.py --dry-run

# Register into every supported agent, no menu:
python register_agents.py --yes

# Register into specific agents only:
python register_agents.py --register vscode
```

> **Note:** Both options above will always assume that the gateway package is installed and will place the following command in the agent's config upon successful registration - `run-mcp.<bat\sh> nxp.mcp.gateway <MCP_Install_DIR>/configs/gateway.stdio.yaml`. If the gateway package is not installed, please manually edit the launch command for the installed MCP server(s).

### Manual registration

For manual registration with an AI agent, add an MCP server entry pointing to the gateway command.

```json
{
  "mcpServers": {
    "nxp-tools": {
      "command": "C:/NXP/s32ds-agentic-ai/run-mcp.bat",
      "args": ["nxp.mcp.gateway", "configs/gateway.stdio.yaml"],
      "disabled": false
    }
  }
}
```
> **Note:** Some agents may need to be restarted after registration.

## Skills

Skills are markdown documents bundled with the MCP servers that describe how to interact with each server - its tools, resources, and prompts - in a structured format agents can reason about.

### How skills are served

All skills are **automatically loaded as MCP resources** by each server at startup. Every skill file is exposed as a resource URI (e.g. `skill://nxp_freemaster/freemaster_lite_start_server`) and is accessible to any MCP-compatible agent without any additional setup.

### Better experience with agents that natively support skills

Some agents have native support for skill/prompt directories and will pick up skills automatically when placed in a specific directory. For the best experience with those agents, copy the skills from the `skills/` directory in this installation to the appropriate location for your agent.

| Agent | Skills folder | Notes |
|---|---|---|
| **Claude Code** | `~/.claude/skills/` | Place skill folders directly inside; Claude Code loads `.md` files from this directory |
| **Codex (OpenAI)** | `~/.codex/skills/` | Copy the skill subdirectories; Codex reads skills from the user profile skills dir |
| **Cursor** | `.cursorrules` / `.cursor/skills/` | Add skill content to `.cursorrules` in the project root, or place skill folders under `.cursor/skills/` |

### Copying Skills to the Agent Skills Directory automatically

When opting for any agent registration during installation or explicitly using the `register_agents.py` script to register with agents, the bundled skills will always be copied for each selected agent in it's respective skills directory unless the `--skip-copy-skills` option is used.

Examples:
```bash
# Register with Claude Code and copy the bundled skills into ~/.claude/skills/
python register_agents.py --register claude

# Copy into a custom destination regardless of the agent selected during installation
python register_agents.py --copy-skills ~/.claude/skills
```

**Copying skills manually**

> **Note:** The skills directory for your installation is located at `skills/` in the MCP install folder. Each server has its own subdirectory (e.g. `skills/freemaster/`, `skills/s32ct/`, `skills/s32debugger/`). Copy only the skill folders relevant to the servers you are using.

```shell
# Windows
xcopy /E /I skills\freemaster %USERPROFILE%\.agents\skills\freemaster

# Linux / macOS
cp -r skills/freemaster ~/.agents/skills/freemaster
```

## Configuration

This section walks you through configuring the MCP servers via their respective configuration files, starting from the most common use cases.

### Shared Configuration Options

These options are available in both standalone and gateway configs.

#### Logging

```yaml
logging:
  level: INFO                         # DEBUG | INFO | WARNING | ERROR
  timestamp_format: "%Y-%m-%d %H:%M:%S"
  format: "%(asctime)s [%(name)s] %(levelname)s %(message)s"
  file: ./.tmp/logs/myserver.log      # optional - omit to log to stderr only
```

| Field | Default | Description |
|-------|---------|-------------|
| `level` | `INFO` | Log verbosity |
| `timestamp_format` | `%Y-%m-%d %H:%M:%S` | Date/time format in log lines |
| `format` | `%(asctime)s [%(name)s] %(levelname)s %(message)s` | Full Python logging format string |
| `file` | _(none)_ | Path to log file; omit to write to stderr only |


> **Note:** In the gateway, `logging` settings are inherited from the top-level `logging` block unless a per-server `logging` override is provided.

---
### Running the Gateway

The gateway loads multiple servers and exposes them all through one MCP connection. Each tool is prefixed with the server name (e.g. `nxp_freemaster_start`, `nxp_knowledge_kb_search`) to avoid naming conflicts.

**Start the gateway (stdio transport - default):**

The agent launches the gateway as a subprocess. Use this for most agents (Claude Desktop, VS Code with stdio).

```shell
# Run from the installation directory
python -m nxp.mcp.gateway configs/gateway.stdio.yaml
```
or
```shell
run-mcp.bat nxp.mcp.gateway configs/gateway.stdio.yaml
```

**Start the gateway (HTTP transport - shared instance):**

The gateway runs as a persistent shared process. Start it once; agents can connect to it via `http://127.0.0.1:8080/mcp`.
```shell
# Run from the installation directory
python -m nxp.mcp.gateway configs/gateway.http.yaml
```
or
```shell
run-mcp.bat nxp.mcp.gateway configs/gateway.http.yaml
```

> **Note:** The HTTP endpoint host and port are configurable via `http.host` and `http.port` in `configs/gateway.http.yaml` (default: `http://127.0.0.1:8080/mcp`).

#### Gateway-only config structure

A gateway config adds two sections on top of the shared `logging` block:

- `logging` - shared logging settings (inherited by all sub-servers unless overridden)
- `gateway` - gateway-level behaviour flags
- `servers` - one entry per server, with its settings and optional overrides

#### Minimal gateway config example (FreeMASTER + Knowledge Base)

This is the most common starting point - two servers, one gateway connection:

```yaml
logging:
  level: INFO
  file: ./.tmp/logs/gateway.log       # optional - omit for stderr only

gateway:
  strict_startup: true                # fail to start if any enabled server fails to load

servers:
  knowledge:
    settings:
      db_path: "knowledge_db/bge-base-en-v1.5"
      collection: "freemaster"
      dirs:
        - "knowledge/freemaster"
      chunk_size: 1200
      chunk_overlap: 200
      embedder:
        provider: "sentence_transformers"
        model: "models/bge-base-en-v1.5"
        dimension: 768
        device: "cpu"
      mutable: false

  freemaster:
    settings:
      ws_host: "localhost"
      ws_port: 8090
    skills: skills/freemaster
```

> **How opt-out works:** Servers installed but not listed here are still discovered automatically. To explicitly prevent a server from loading, add `disabled: true` to its entry.

#### Full gateway config

This example shows all available servers with their settings, using `disabled: true` to exclude servers you do not need:

```yaml
logging:
  level: INFO
  file: ./.tmp/logs/gateway.log

gateway:
  strict_startup: true
  skills: []                          # optional: list of extra skill directories to expose

servers:
  knowledge:
    settings:
      db_path: "knowledge_db/bge-base-en-v1.5"
      corpora:
        - name: "compiler"
          dirs:
            - "knowledge/compiler"
        - name: "freemaster"
          dirs:
            - "knowledge/freemaster"
        - name: "s32ct"
          dirs:
            - "knowledge/s32ct"
        - name: "s32debugger"
          dirs:
            - "knowledge/s32debugger"
        - name: "s32ds"
          dirs:
            - "knowledge/s32ds"
        - name: "s32flashtool"
          dirs:
            - "knowledge/s32flashtool"
        - name: "s32sdaf"
          dirs:
            - "knowledge/s32sdaf"
        - name: "s32trace"
          dirs:
            - "knowledge/s32trace"
      chunk_size: 1200
      chunk_overlap: 200
      embedder:
        provider: "sentence_transformers"
        model: "BAAI/bge-base-en-v1.5"
        dimension: 768
        device: "cpu"
        cache: "../models"
        offline: true
      mutable: false

  freemaster:
    settings:
      ws_host: "localhost"
      ws_port: 8090
    skills: skills/freemaster

  s32debugger:
    settings:
      installation_path: ""           # S32Debugger install root (for example C:/NXP/S32DBG.3.6.8)
      default_gdb_variant: "arm32"
    skills: skills/s32debugger

  s32ct:
    settings:
      installation_path: ""           # leave empty for auto-discovery
      mcu_data_root: ""
      documentation_path: ""
      timeout_s: 600
    skills: skills/s32ct

  compiler:
    settings:
      toolchain_path: ""              # Toolchain folder (ex: C:/NXP/S32DS/S32DS/build_tools), leave empty for auto-discovery
    skills: skills/compiler

  s32flashtool:
    settings:
      project_path: ""
    skills: skills/s32flashtool

  s32trace:
    settings:
      installation_path: ""
    skills: skills/s32trace

  s32ds:
    disabled: true                    # opt-out: Eclipse-based S32DS not in use
    settings:
      s32ds_rest_port: 8088

  s32sdaf:
    settings:
      installation_path: ""  # set to the volkano install root (for example C:/NXP/S32DS.3.6.8/S32DS/tools/S32Debugger/Debugger/Server/CCS/bin or C:/NXP/SDAF)
    skills: skills/s32sdaf
  template:
    disabled: true                    # opt-out: reference server, not needed in production
```
---
### Running a Standalone Server

A standalone config (a config file specific to one of the bundled mcp servers) has three sections:

- `logging` - logging settings
- `settings` - server-specific settings
- `skills` - path to the skills directory for this server (optional)

#### Example: FreeMASTER standalone

Use this when you only need to connect to a running FreeMASTER Lite instance.

**Start the server:**
```shell
# Run from the installation directory
python -m nxp.mcp.freemaster configs/freemaster.standalone.yaml
```
or
```shell
run-mcp.bat nxp.mcp.freemaster configs/freemaster.standalone.yaml
```

**Config file (`configs/freemaster.standalone.yaml`):**
```yaml
logging:
  level: INFO
  file: ./.tmp/logs/freemaster.log    # optional - omit for stderr only

settings:
  ws_host: "localhost"                # host where FreeMASTER Lite WebSocket is running
  ws_port: 8090                       # WebSocket port (default: 8090)

skills: skills/freemaster
```

#### Example: Knowledge Base standalone

Use this when you want semantic search over NXP documentation and skill files.

**Start the server:**
```shell
# Run from the installation directory
python -m nxp.mcp.knowledge configs/knowledge.standalone.yaml
```
or
```shell
run-mcp.bat nxp.mcp.knowledge configs/knowledge.standalone.yaml
```

**Config file (`configs/knowledge.standalone.yaml`):**
```yaml
logging:
  level: INFO
  file: ./.tmp/logs/knowledge.log               # optional - omit for stderr only

settings:
  db_path: "knowledge_db/bge-base-en-v1.5"      # directory where LanceDB stores vector data
                                                # (one folder, one table per corpus)
  corpora:                                      # one named corpus per LanceDB table
    - name: "freemaster"                        # corpora name used as collection name by LanceDB
      dirs:                                     # directories scanned for this corpus at startup
        - "knowledge/freemaster"
  chunk_size: 1200                              # max words per document chunk
  chunk_overlap: 200                            # word overlap between consecutive chunks
  embedder:
    provider: "sentence_transformers"
    model: "BAAI/bge-base-en-v1.5"              # path to a pre-downloaded model
    dimension: 768                              # must match the model (768 for bge-base-en-v1.5)
    device: "cpu"                               # "cpu", "cuda", or "mps"
    cache: "../models"                          # directory (config-relative) where models are cached / downloaded
    offline: true                               # true = load only from local cache (no HuggingFace Hub calls); false = allow download
  mutable: false                                # true = allow adding/removing documents via tools
```
---

## Knowledge Base

The `mcp_knowledge` server provides a fully local, vectorized documentation index:

- **Storage** - LanceDB tables under `knowledge_db/bge-base-en-v1.5/`, one table per corpus.
- **Embeddings** - `models/bge-base-en-v1.5` (768 dimensions), executed locally on CPU (or CUDA / MPS if configured).
- **Reranking** - `models/bge-reranker-base` is bundled for higher-precision result ordering.
- **Corpora** - one per tool domain (`compiler`, `freemaster`, `s32ct`, `s32debugger`, `s32ds`, `s32flashtool`, `s32sdaf`, `s32trace`). Corpora can be grouped so a single query fans out across multiple tables.
- **Tools** - `nxp_knowledge_kb_search` (semantic search) and `nxp_knowledge_kb_list_corpora` (discover groups and tables). With `mutable: true`, `kb_ingest` / `kb_remove` become available for adding your own documents.

Everything runs offline - no documentation, source code or query text is sent to any external service by the knowledge base.

## Building from Source

The repository is a multi-package Python workspace. Each server under `packages/mcp_<name>/` owns its own `pyproject.toml` and declares an `nxp.mcp.servers` entry-point, so it can be installed and used independently. The root `pyproject.toml` is a convenience meta-package that pulls all of them in.

```shell
# 1. Create and activate a virtual environment (Python 3.11+)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Build wheels for all sub-packages plus the root meta-package
python scripts/build_modules.py

# 4. Bundle wheels and assets into a single self-installing .pyz
python scripts/create_deploy_package.py
```

The resulting installer (`s32ds-agentic-ai-installer-{version}.pyz`) and wheels are written to the `dist/` directory. The packaged version and the list of bundled assets (skills, models, configs, launchers) are defined in `scripts/installer/_manifest.py`. See [`scripts/README.md`](scripts/README.md) for the full script reference and [`scripts/Jenkinsfile`](scripts/Jenkinsfile) for the CI pipeline.

To run a server directly from a source checkout, install the workspace in editable mode and point the module at a config file:

```shell
pip install -e .
python -m nxp.mcp.gateway configs/gateway.stdio.yaml
```

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Agent shows no `nxp_*` tools | The MCP server entry was not picked up. Re-run `python register_agents.py --dry-run` to confirm the command, then restart the agent. |
| Gateway exits immediately at startup | With `gateway.strict_startup: true`, one failing server aborts the whole gateway. Check the log file configured under `logging.file`, then either fix the server's `settings` or mark it `disabled: true`. |
| A tool reports "installation not found" | The corresponding NXP product is not installed, or auto-discovery failed. Set the explicit `installation_path` (or `toolchain_path`) for that server in the config. |
| S32DS tools time out or refuse to connect | S32 Design Studio is not running, the MCP Integration plugin is missing, or the JSON-RPC port differs. Verify the plugin is installed and align `s32ds_rest_port` with the IDE setting (default 8088). |
| FreeMASTER tools cannot connect | FreeMASTER Lite is not running or listens on another port. Align `ws_host` / `ws_port` with the `.fmcfg` configuration (default 8090). |
| S32 Flash Tool tools fail | The REST/RPC server is not enabled in S32 Flash Tool, or the port differs from 51236. See the S32 Flash Tool User Guide in the product installation. |
| Knowledge search returns nothing | The corpus is empty or `db_path` points to the wrong folder. Confirm `knowledge_db/` was extracted by the installer and that the corpus name matches `kb_list_corpora` output. |
| Skills are not offered by the agent | Skills are always exposed as MCP resources, but agents with native skill support need the files on disk. Copy `skills/` into the agent's skills folder, or re-run `register_agents.py --copy-skills`. |

Enable `logging.level: DEBUG` and set `logging.file` in the relevant config to capture a full trace before reporting an issue.

## License

This software is licensed under the **LA_OPT_Online Code Hosting NXP_Software_License - v1.4 May 2025**, together with an **AI Addendum** that governs the agentic / AI-assisted functionality of this toolkit.

- Full license text: [`LICENSE`](LICENSE)
- AI Addendum: [`LICENSE_ADDENDUM`](LICENSE_ADDENDUM)
- Third-party components and their licenses: [`SBOM-S32-DS-Agentic-AI.spdx.json`](SBOM-NXP_Agentic_AI_Toolkit.spdx.json)

By downloading, installing or using this software you accept the terms of the license agreement and the addendum. If a separate license agreement for this software has been signed by you and NXP, that agreement governs your use and supersedes the terms above.

## Community

Questions, feedback, feature requests and discussions about this toolkit are welcome on the NXP Community:

[Agentic AI Development - NXP Community](https://community.nxp.com/t5/Agentic-AI-Development/tkb-p/agentic-ai-development)

When reporting a problem, please include the toolkit version (see [`RELEASE_NOTES.md`](RELEASE_NOTES.md)), your operating system and Python version, the NXP tool versions involved, the agent you are using, and the relevant portion of the server log captured with `logging.level: DEBUG`.
