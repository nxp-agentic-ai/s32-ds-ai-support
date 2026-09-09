# Examples and Anti-Patterns

## Quick scenarios

- `M7_0` boot core plus `M7_1` secondary with separate ELF per core -> one
  config and one bridge per client; boot first, then secondary
- boot core plus two secondary M7 clients -> validate boot first, then attach
  secondaries one by one
- request mixes `A53` and `M7` without explicit support -> stop and clarify
- topology is multicore but boot core is missing -> ask only for that detail

## Anti-patterns

- using a single config for all GDB clients
- using one bridge port for multiple clients
- starting secondaries before boot-core readiness is proven
- starting multiple secondaries in parallel during fragile startup
- reporting success before each client has independent validation
- closing the session automatically after successful startup
