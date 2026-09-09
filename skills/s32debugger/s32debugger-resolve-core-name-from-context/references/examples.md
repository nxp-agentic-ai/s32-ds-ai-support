# Examples and Anti-Patterns

## Quick examples

- `S32G274A` -> identify `s32g2xx`, inspect `s32g2xx_context.py`, extract
  `_CORE_NAME` and `_SOC_NAME`, then validate against
  `s32g2xx_init_sequence.py`
- family already known as `s32k3xx` -> skip family inference, inspect
  `s32k3xx_context.py`, return authoritative values directly
- `_CORE_NAME` assigned via imported constant -> trace the import before
  reporting the resolved value
- `_context.py` incomplete but `_cores.py` exists -> use fallback and state
  clearly that authoritative context resolution was incomplete

## Anti-patterns

- guessing `_CORE_NAME` from the SoC part number
- guessing `_SOC_NAME` instead of reading it
- constructing either string from architecture name or derivative suffix
- copying context values from a different family
- assuming `core_name` alone is enough without checking derivative-specific
  `soc_name` logic
