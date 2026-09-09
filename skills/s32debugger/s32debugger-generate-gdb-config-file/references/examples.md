# Examples and Anti-Patterns

## Typical triggers

- generate a GDB config file
- prepare the S32Debugger config for this target
- make the base config txt for live debug
- generate the config from the example template
- prepare the txt that I will later pass to `control.start_gdb`

## Good behavior cues

- call out `generate.gdb_config_file`
- describe the result as a generated GDB config `.txt` file with an embedded
  REST bridge
- preserve user-supplied paths and target parameters carefully
- prefer exact matching examples when available
- ask before using a fallback example
- surface generated transport ports that the chosen bridge port must not reuse

## Anti-patterns

- hand-writing a config by default
- confusing the source Python example with the final `.txt` artifact
- silently substituting a different template
- reusing the generated config's target GDB server port as the bridge port
- skipping required target/core/probe inputs when they matter for correctness
