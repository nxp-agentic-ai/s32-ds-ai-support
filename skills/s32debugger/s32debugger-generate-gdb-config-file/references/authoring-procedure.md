# Authoring Procedure

## Workflow

1. Select the right Python example template.
   - prefer exact match by `soc_family`, `script_type`, `core_name`, and
     lockstep when relevant
   - if the user already knows `template_name`, use that directly
2. Collect the required overrides.
   - target/SoC name
   - probe IP
   - core name, core ID, cluster ID
   - lockstep mode
   - ELF path (`file_debug`)
   - init script path
   - ports and logging options
   - secure/reset/lifecycle options when needed
3. Resolve authoritative family-context values first when `core_name`,
   `soc_name`, or init-sensitive inputs are uncertain.
4. Call `generate.gdb_config_file`.
5. Inspect or report the generated target transport ports when they are known,
   especially the target GDB server port and CCS port.
6. Return the generated `.txt` path and describe it as a GDB config artifact
   for later startup.

## Fallback policy

If no exact example exists:
1. find the closest matching example in the same family and script type
2. explain clearly which example was found
3. say explicitly that it is a fallback base
4. ask before proceeding with that fallback

## Typical handoff

Common next steps after generation:
1. choose a bridge port distinct from the generated config's target GDB server
   port and CCS port (the bridge is already embedded in the generated config)
2. start the GDB client with `control.start_gdb` (it launches GTA automatically
   and starts GDB with the generated config)
3. inspect session state
