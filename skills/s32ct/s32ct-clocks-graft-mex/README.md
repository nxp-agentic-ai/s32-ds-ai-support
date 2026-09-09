# `s32ct-clocks-graft-mex` skill  --  layout

Sibling of `s32ct-peripherals-graft-mex`. Handles the Clocks-tool side of
the `.mex` authoring puzzle.

```
s32ct-clocks-graft-mex/
+--- SKILL.md                              # Top-level skill, ~360 lines
+--- README.md                             # This file
+--- references/                           # Loaded on demand
|   +--- clock-anatomy.md                  # XML data model: TOP.xml, MUX/DIV/PLL, etc.
|   +--- performance-presets.md            # Per-MCU max-perf / mid / low-power presets
|   +--- error-decision-tree.md            # Clocks-specific validation errors -> fixes
|   \--- multi-config.md                   # Adding a second <clock_configuration>
\--- scripts/                              # Standalone workhorses (also usable from MCP recipes)
    +--- inspect_clocks.py                 # CLI version of the s32ct.inspect_* actions query=clock_*
    +--- apply_settings.py                 # Apply preset or explicit (id, value) edits to ClockConfig0
    +--- lift_clockconfig.py               # Workflow C: replace ClockConfig0 with one from an example .mex
    \--- add_clock_point.py                # Add McuClockReferencePoint_LPUART_CLK / CAN_PE_CLK / etc.
```

## When to use / when NOT to use

Every trigger must name the **Clocks tool**, a **`.mex` project**, or a
**concrete S32 clock identifier**. Domain-qualified examples:

- "configure the clock tree in my S32 Configuration Tools `.mex` project"
- "set `CAN_PE_CLK` to 80 MHz in the Clocks tool"
- "apply the max-performance clock preset to this `.mex`"
- "switch this `.mex` to a low-power clock configuration"
- "add a 32 kHz SXOSC clock source to the Clocks tool"
- "raise `CORE_CLK` on this part in the `.mex` clock tree"
- "lift the K344 example's `<clock_configuration>` into my `.mex`"

**Do NOT use this skill for** (negative examples - these are not
clock-tree work):

- "make this fast" / "make it faster" / "speed this up"
- "optimise this" / "reduce power" / "why is my code slow"
- "speed up my build" / "my app is laggy"
- Read-only clock questions - use `s32ct-clocks-info`.
- Pins or Peripherals changes - use `s32ct-pins-author-mex` /
  `s32ct-peripherals-graft-mex`.

## Three workflows

| `mode=` | When to use | Tool/script |
|---|---|---|
| `preset` | "apply the max-performance / low-power clock preset to this .mex" | `scripts/apply_settings.py --preset s32k312:max_performance` |
| `tweak`  | "bump CAN_PE_CLK to 80 MHz in the Clocks tool"                    | `scripts/apply_settings.py --set ID=VAL ...` |
| `lift`   | "use the K344 example's clock tree in my .mex"                    | `scripts/lift_clockconfig.py --example <ref.mex>` |

> **Warning - these workflows modify project files.**
> `apply_settings.py` and `lift_clockconfig.py` rewrite the target `.mex`
> clock configuration (replacing the existing tree), and `s32ct.sanitize`
> edits the `.mex` in place. No backup is written and the change is not
> reversible. Commit or back up the `.mex` project before running any of
> the three workflows above.

After **any** workflow:

```
s32ct.sanitize(project_path=out)          # rewrite dangling Mcu/Mcl refs
s32ct.validate(project_path=out, tool_name="Clocks")
s32ct.validate(project_path=out)              # full regression (Pins + Peripherals + Clocks)
```

## Companion: per-domain clock points

After tuning the tree, drivers still see `McuClockReferencePoint_0 -> CORE_CLK`
unless you add semantic points and re-point each driver's `*ClockRef`:

Windows (`cmd.exe`) - line continuation is `^`:

```bat
python scripts/add_clock_point.py project.mex ^
       --name LPUART_CLK --select AIPS_SLOW_CLK ^
       --name LPSPI_CLK  --select AIPS_PLAT_CLK ^
       --name CAN_PE_CLK --select AIPS_PLAT_CLK ^
       --name EMIOS_CLK  --select AIPS_PLAT_CLK ^
       --out  project_with_points.mex
```

Linux / macOS (`sh`/`bash`) - line continuation is `\`:

```sh
python3 scripts/add_clock_point.py project.mex \
       --name LPUART_CLK --select AIPS_SLOW_CLK \
       --name LPSPI_CLK  --select AIPS_PLAT_CLK \
       --name CAN_PE_CLK --select AIPS_PLAT_CLK \
       --name EMIOS_CLK  --select AIPS_PLAT_CLK \
       --out  project_with_points.mex
```

All four scripts in this skill are plain Python and run unchanged on
either platform; only the shell line-continuation character differs.

Then edit each driver's `*ClockRef` value to point at the matching new
entry (search/replace).

## Why this skill exists

The Clocks tool is structurally identical to the Peripherals tool (XML
`<clock_configuration>` is the analogue of `<instance>`) but uses
different XML element names and a different on-disk data store. The same
"lift validated XML from an authoritative source, surgically adapt, then
validate" workflow applies  --  this skill captures it for the clocks side
so you don't have to derive it from scratch each time.
