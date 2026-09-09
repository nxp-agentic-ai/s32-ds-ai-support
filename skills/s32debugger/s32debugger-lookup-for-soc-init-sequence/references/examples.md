# Examples and Anti-Patterns

## Example families

### S32G2xx
Typical files:
- `<install>/S32Debugger/Debugger/scripts/s32g2xx/s32g2xx_generic_bareboard.py`
- `<install>/S32Debugger/Debugger/scripts/s32g2xx/s32g2xx_init_sequence.py`

Typical helpers may include:
- `_prologue()`
- `_sram()`
- `_partition_*()`
- `_m7_*()`
- `_a53_*()`
- `init_sequence_by_core_name(...)`

Always inspect the actual local files before citing helper names as
authoritative.

## Anti-patterns

- guessing the family when the SoC is ambiguous
- inventing init function names instead of reading the file
- assuming all families use the same reset/AP/register sequence
- forcing `init_sequence_by_core_name(...)` when the family uses another entry
  model
- presenting machine-specific install paths as generic guidance
