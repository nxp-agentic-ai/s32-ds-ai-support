# Authoring Procedure

## Core rule

Preserve structure first, change values second.

## Workflow

1. Identify the exact adaptation baseline.
   - Existing user script
   - Previously generated artifact
   - Known working startup flow
   - Config-generation pattern
   - Previously successful live-debug session flow
2. Separate structural logic from mutable values.
   - Preserve startup order, GTA-before-GDB lifecycle, bridge setup,
     config generation order, report layout, connect/load/break/run ordering,
     and known-good init ordering.
   - Change target family, SoC, core, lockstep, probe IP, ELF path,
     breakpoint symbol, hit count, report path, config filenames, and
     keep-session-open behavior when requested.
3. Classify the delta.
   - Local: probe IP, ELF path, breakpoint symbol, output filename,
     additional report metadata, hit count.
   - Architectural: background to bridge-backed interactive, adding reporting,
     collect-at-breakpoint flows, init reuse/import, one deliverable to many.
4. Reuse adjacent skills when needed.
   - `s32debugger-resolve-gdb-variant`
   - `s32debugger-start-standalone-live-session`
   - `s32debugger-lookup-for-soc-init-sequence`
   - `s32debugger-error-resolution`
   - `s32debugger-generate-automation-script`
   - `s32debugger-connect-gdb-to-s32-debug-probe`
5. Make the smallest correct change set.
6. Explain the delta explicitly.

## Preferred output pattern

1. Baseline used
2. Requested adaptation
3. Preservation summary
4. Change classification
5. Updated script or saved artifact path
6. Verification checklist

## Fallback

If adaptation is no longer enough, say which parts no longer fit and route to
more appropriate generation behavior while preserving any reusable baseline
knowledge.
