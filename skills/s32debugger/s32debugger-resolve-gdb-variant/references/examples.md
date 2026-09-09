# Examples and Anti-Patterns

## Quick examples

- `M7_0` -> family `M7`, instance `M7_0`, variant `arm32`
- `M7_0_LS` -> family `M7`, instance `M7_0_LS`, variant `arm32`
- `A53_0_0` -> family `A53`, instance `A53_0_0`, variant `arm64`
- `R52_0` -> family `R52`, instance `R52_0`, variant `arm32`
- only SoC given, no target core -> ask for the exact core instead of guessing

## Anti-patterns

- inferring `arm64` from any `A*` core without checking the supported mapping
- selecting the GDB variant from the SoC family instead of the target core
  family
- throwing away an explicit instance name too early
- using this skill as if it also chooses init scripts, configs, or flash logic
- guessing a variant when only a vague SoC reference is available
