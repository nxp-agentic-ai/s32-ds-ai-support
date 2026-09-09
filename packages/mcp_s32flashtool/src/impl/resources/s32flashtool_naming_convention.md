
# S32FlashTool Naming Convention

## Purpose

This document defines naming conventions and name equivalents to be followed when referring to
files, targets, algorithms, identifiers and other names in S32FlashTool operations and documentation.

You SHOULD follow these rules exactly.

## s32flashtool
Usually refers to the command line application `S32FlashTool CLI executable` which is found in the subfolder `bin` of the [S32FlashTool installation folder].
Colloquially refered as `flashtool`.
## S32 Flash Tool
Mainly in documentation, usually refers to the s32 flash tool as a tool (including GUI, command line application (S32FlashTool), documentation).
`S32 Flash Tool installation`, `S32FlashTool installation` mean the same.

## Targets
The term `target` might refer to:
- a processor (like S32N55)
- a binary file found in the [S32FlashTool installation folder]/targets folder (like S32N5x.bin) which is used (with the correct path) by the S32FlashTool command line application. Might be used as `target binary`.
Some users might use `agent` for the `target` binary.
If the user specifies `S32N5`, for example, take into account also `S32N5x`. Similar for other platforms.

## Algorithms
The term `algorithm` might refer to:
- a flash memory binary found in  `[S32FlashTool installation folder]/flash` folder (like S28HS01GT.bin) which is used (with the correct path) by the S32FlashTool command line application
- it is equivalent to `flash memory algorithm`

## Bootable image
The term "bootable image" might refer to:
- the `binary file` which gets uploaded into the flash memory
- the `blob` (also a binary file) that gets uploaded into the flash memory

## Program operation
The term `program` is equivalent to `upload`, `fprogram`. When the user request a `write`, tell that `write` requires `erase` and that `program` should be safer. 

## Mcuid
The term `mcuid` corresponds to `processor id`, `processor identifier`

