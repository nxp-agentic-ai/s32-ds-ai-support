# Authoring Procedure

## Workflow

1. Normalize the request.
2. Resolve the explicit core instance.
3. Select the GDB variant from the core family.
4. Discover the best matching single-core template.
5. Choose a bridge port that is distinct from the target GDB server port, the
   CCS port, and any active listener already in use.
6. Generate the startup config with `generate.gdb_config_file`, passing the
   chosen bridge port (the REST bridge is embedded in the generated config).
7. Reject or regenerate a mismatched all-cores/multicore shape unless it is
   explicitly justified.
8. Start GDB with the canonical explicit client identity using
   `control.start_gdb` (it launches GTA automatically).
9. Validate bridge responsiveness and breakpoint/session state.
10. Keep the session open unless the user asks to stop it.

## Template priority

1. exact SoC + exact core instance + single-core intent
2. exact SoC + exact core family + single-core intent
3. same SoC family + closest single-core-compatible template

## Failure handling

If anything fails:
1. identify the failing stage
2. preserve generated file paths and session details
3. consult `s32debugger-error-resolution`
4. retry with the smallest necessary correction
5. if the config shape is wrong, stop and regenerate from a better single-core
   base instead of blindly continuing
6. if the first attach fails early, check for bridge-port collision against the
   generated config's target GDB server port before retrying
