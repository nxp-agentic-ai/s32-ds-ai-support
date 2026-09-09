# `s32ct-peripherals-graft-mex` skill  --  layout

```
s32ct-peripherals-graft-mex/
+--- SKILL.md                                # Top-level skill (~400 lines)
+--- README.md                               # This file
+--- references/                             # Loaded on demand
|   +--- per-driver-gotchas.md               # Per-driver adaptation rules
|   +--- error-decision-tree.md              # SEVERE: [TOOL] message -> fix
|   +--- iteration-playbook.md               # What to expect per round
|   \--- cross-reference-map.md              # /Mcl/, /Mcu/.*_CLK, BOARD_BootClockRUN
\--- scripts/                                # Executable workhorses
    +--- balanced_array.py                   # find_balanced_named_array() helper
    +--- inventory.py                        # List existing <instance> + clock points
    +--- discover.py                         # Pick best RTD example .mex per driver
    +--- extract_examples.py                 # Lift <instance> XML from example .mex
    +--- splice.py                           # Splice into target .mex (re-uuid'd)
    +--- sanitize.py                         # 3-sweep cross-reference cleaner
    +--- check_problems.bat                  # Canonical validation invocation (Windows)
    +--- check_problems.sh                   # Canonical validation invocation (Linux/macOS)
    \--- filter_problems.py                  # The only honest validation gate
```

All Python scripts are platform-neutral. Only the validation wrapper is
shell-specific: use `check_problems.bat` on Windows and
`check_problems.sh` on Linux/macOS. The two accept the same arguments and
produce the same capture files.

## Quick start (Windows - `cmd.exe`)

```bat
REM 1. Inventory the existing .mex
python scripts/inventory.py C:\path\to\Project_Pins.mex

REM 2. Find the cleanest RTD example for the driver
python scripts/discover.py --driver Spi --mcu S32K312

REM 3. Lift the example's <instance> block
python scripts/extract_examples.py --driver Spi ^
       --example <path-from-step-2> ^
       --out work/Spi.xml

REM 4. Splice into the user's .mex (regenerates instance UUID)
python scripts/splice.py --project C:\path\to\Project_Pins.mex ^
       --out C:\path\to\Project_Full.mex ^
       --instances work/Spi.xml

REM 5. Sanitize cross-references (idempotent)
python scripts/sanitize.py --mex C:\path\to\Project_Full.mex

REM 6. Validate (no-space path required)
copy /Y C:\path\to\Project_Full.mex C:\tmp_mex\probe.mex
scripts\check_problems.bat probe Peripherals
python scripts/filter_problems.py --stderr C:\tmp_mex\probe_Peripherals_stderr.txt
```

## Quick start (Linux / macOS - `sh`/`bash`)

```sh
# Staging dir for the validation probe; check_problems.sh defaults to
# ${TMPDIR:-/tmp}/s32ct_probe when S32CT_PROBE_DIR is unset.
export S32CT_PROBE_DIR="${TMPDIR:-/tmp}/s32ct_probe"
export S32CT_INSTALL=/opt/nxp/S32ConfigTools.<release>
mkdir -p "$S32CT_PROBE_DIR"

# 1. Inventory the existing .mex
python3 scripts/inventory.py ~/projects/Project_Pins.mex

# 2. Find the cleanest RTD example for the driver
python3 scripts/discover.py --driver Spi --mcu S32K312

# 3. Lift the example's <instance> block
python3 scripts/extract_examples.py --driver Spi \
       --example <path-from-step-2> \
       --out work/Spi.xml

# 4. Splice into the user's .mex (regenerates instance UUID)
python3 scripts/splice.py --project ~/projects/Project_Pins.mex \
       --out ~/projects/Project_Full.mex \
       --instances work/Spi.xml

# 5. Sanitize cross-references (idempotent)
python3 scripts/sanitize.py --mex ~/projects/Project_Full.mex

# 6. Validate
cp -f ~/projects/Project_Full.mex "$S32CT_PROBE_DIR/probe.mex"
sh scripts/check_problems.sh probe Peripherals
python3 scripts/filter_problems.py \
       --stderr "$S32CT_PROBE_DIR/probe_Peripherals_stderr.txt"
```

> **Warning - steps 4-6 write and overwrite files.** `splice.py` writes
> `--out` (overwriting it if present), `sanitize.py` modifies the `.mex`
> it is given **in place**, and `copy /Y` (Windows) / `cp -f` (POSIX)
> replaces the destination without prompting. None of these create a
> backup. Before running the quick start, back up or commit the original
> project `.mex`, and keep `--project` and `--out` as distinct paths so
> the input stays intact.

If `filter_problems.py` reports `FAIL N`, consult
`references/error-decision-tree.md` to map the error to a fix. Re-run
`sanitize.py` and validate again - typically 3-6 iterations resolve to 0.

## Why this skill exists

Authoring driver `<instance>` blocks from scratch (via the
`.component` schema + resource tables) reliably takes 25+ validator
iterations because the cross-reference shape only the RTD example knows.

Lifting from the RTD example takes 3-6 iterations because the cross-reference
shape is already correct  --  only the package-specific hw-channel selectors and
a small set of clock/DMA cross-refs need adaptation, and the
adaptations are systematic.

The skill packages the systematic part (sanitize + filter), the per-driver
part (gotchas reference), and the iteration discipline (playbook + decision
tree). The intent is for any future agent that needs to add a driver
instance to a `.mex` to reach a validating result *fast*.
