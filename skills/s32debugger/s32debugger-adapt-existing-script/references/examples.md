# Examples and Verification

## Typical triggers

- adapt this script for another probe IP
- same script, but for a different ELF
- keep the working flow and add breakpoint reporting
- modify the existing Python launcher to use bridge-backed mode
- reuse this script but switch target/core
- take the working setup and make it save a report
- keep the existing automation, just retarget it

## Typical inputs

- Baseline script or working flow
- Requested delta
- Target family / SoC / core changes
- Probe / ELF / breakpoint / output-path changes
- Generation-only, save-only, or adapt-and-run intent
- Single-file vs multi-deliverable expectation

## Verification checklist items

- Target family / SoC still matches the flow
- GDB variant still matches the core
- Probe connection parameters are correct
- ELF path exists
- Breakpoint symbol exists in the image
- Report path is writable
- Bridge behavior still matches interactive requirements
- Init logic is still valid for the target

## Do

- Preserve the working baseline whenever possible
- Classify changes as local vs architectural
- Make minimal necessary modifications
- Explain the delta explicitly
- Route to adjacent skills when needed

## Do not

- Regenerate from scratch when adaptation is sufficient
- Change startup sequencing without strong reason
- Drop known-good init, bridge, or report behavior silently
- Hide major structural changes inside a supposed small adaptation
