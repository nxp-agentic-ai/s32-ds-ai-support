# Examples and Anti-Patterns

## Quick scenarios

- `M7_0` plus one ELF and keep-open live debug -> execute the single-core live
  flow directly
- `A53_0_0` plus one ELF and interactive startup -> use explicit `A53_0_0`
  client identity and bridge-backed startup
- `M7` with missing `core_id` -> ask only for that missing detail
- generated config points to `*_all_cores.py` for a clearly single-core request
  -> stop and regenerate from a better single-core source
- generated config keeps `_GDB_SERVER_PORT=45000` -> choose a different bridge
  port such as `45100` instead of reusing `45000`

## Anti-patterns

- relying on client inference in interactive single-core sessions
- using non-bridge interactive startup when follow-up MCP control is expected
- choosing the GDB variant from the SoC alone when the core family is known
- collapsing `M7_0` to plain `M7` and losing instance identity
- accepting an all-cores bring-up shape without challenge for a clearly
  single-core request
- using the same numeric port for both the bridge listener and the generated
  config's target GDB server port
- closing the session automatically after startup when the user asked for a
  live/open session
