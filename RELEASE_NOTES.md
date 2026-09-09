## Overview

A suite of enablers (MCP Servers, Tools, Skills, Vectorized Knowledge Base) that give AI agents the capabilities to work efficiently with NXP development tools.

---

## v1.0.0 (28.09.2026)

Initial release.

### Key Features

- Gateway composition - all servers accessible through a single MCP connection
- Namespace-prefixed tool mounting (`nxp_<name>`) to avoid naming conflicts
- Dynamic server discovery via `mcp.servers` entry-points
- Opt-out mounting semantics (`disabled: true` per server)
- Shared YAML-based configuration model
- Skills system - markdown skill files served as MCP resources for agent guidance
- Vectorized knowledge base (LanceDB + local `bge-base-en-v1.5` embeddings) for offline semantic search over NXP documentation - no cloud calls, no data leaving the machine
- Self-installing `.pyz` installer with per-package selection and automatic agent registration
- Standalone mode - any single server can run on its own with its own config file

---

## Known Limitations

- Linux support is still work in progress for some MCP servers in this bundle.

## Licensing

This release is distributed under the **LA_OPT_Online Code Hosting NXP_Software_License - v1.4 May 2025**, together with the **AI Addendum**.
