# Authoring Procedure

## Workflow

1. Normalize the multicore request.
2. Confirm topology completeness.
3. Resolve per-core identities and the shared GDB variant policy.
4. Discover the correct boot and secondary MultiCore templates.
5. Generate one config per client with `generate.gdb_config_file`, each with a
   unique bridge port embedded.
6. Start the boot core first with `control.start_gdb` (launches GTA
   automatically).
7. Validate boot-core readiness.
8. Start secondary clients serially with `control.start_gdb`.
9. Validate each client independently.
10. Keep the session open unless the user asks to stop it.

## Core rules

- one generated config per GDB client
- one unique bridge port per GDB client
- one explicit client identity per client
- boot core starts first
- secondaries wait until boot-core readiness is proven
- secondaries start serially, not in fragile parallel startup

## Failure handling

If anything fails:
1. identify the failing stage
2. preserve generated config paths, bridge ports, and client identities
3. use `s32debugger-error-resolution`
4. retry with the smallest necessary correction
