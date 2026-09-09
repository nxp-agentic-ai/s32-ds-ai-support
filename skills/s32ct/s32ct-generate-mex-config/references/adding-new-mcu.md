# Adding support for a new MCU

The skill is MCU-agnostic. To enable a new `(mcu, package, mcu_data)`
combination, drop a reference template next to the skill - no code
changes needed.

## Procedure

1. Open S32 Configuration Tools (GUI).
2. Create a new project; select the target MCU, package and SDK / RTD.
3. (Recommended) Enable the **Pins**, **Clocks** and **Peripherals**
   tools so downstream skills have non-empty sections to patch. Leave
   the tools in their default state otherwise.
4. Save the project as `<MCU>_default.mex` (for example
   `S32K344_default.mex`) directly into this skill's folder, next to
   `SKILL.md`.
5. If S32CT writes a sidecar `ClockConfigurationMappings.txt`, copy it
   too so it can be propagated to generated projects.
6. (Optional) Close S32CT, reopen the saved `.mex` to confirm it loads
   cleanly, then save again to normalise whitespace and ordering.

From that point on, calling the skill with `mcu="<MCU>"` (and matching
`package` / `mcu_data` if specified) picks up the new template
automatically.

## Verification

After dropping the template, run a plain-clone smoke test:

```jsonc
{
  "output_path": "C:\\tmp\\<MCU>_starter.mex",
  "mcu": "<MCU>"
}
```

Then open the generated file in S32CT (or run
`toolsc.exe -Load <path> -HeadlessTool Peripherals -ShowProblems`) to
confirm zero problems.

## Treat templates as read-only

The bundled `<MCU>_default.mex` files are inputs, not outputs. Patch a
copy; never the original. Any drift in an original poisons every
subsequent invocation for that MCU.

## Cross-family tips

- Prefer S32CT-saved files over hand-authored XML - the tool applies
  ordering and namespace conventions the parser is picky about.
- Different MCU families use different schema versions (`_17`, `_18`,
  `_19`, `_20`, ...). The skill preserves whichever namespace the
  loaded template carries; see `references/mex-schema.md`.
- Note the pre-wired peripheral set inside the new template - it
  becomes the baseline for `peripherals.patch` / `.remove` requests
  against that MCU.
