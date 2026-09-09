# Authoring Procedure

## Family mapping

### ARM32
Use `arm32` for:
- `M7`
- `M33`
- `M0`
- `M4`
- `R52`

Executable (`.exe` suffix on Windows only; no suffix on Linux):
- `gdb/gdb-arm/arm32-eabi/bin/arm-none-eabi-gdb-py.exe` (Windows)
- `gdb/gdb-arm/arm32-eabi/bin/arm-none-eabi-gdb-py` (Linux)

### ARM64
Use `arm64` for:
- `A53`
- `A78`

Executable (`.exe` suffix on Windows only; no suffix on Linux):
- `gdb/gdb-arm/arm64-eabi/bin/aarch64-none-elf-gdb-py.exe` (Windows)
- `gdb/gdb-arm/arm64-eabi/bin/aarch64-none-elf-gdb-py` (Linux)

## Normalization rules

1. normalize the input core string to uppercase when matching
2. strip common instance suffixes only for family matching:
   - `_0`
   - `_1`
   - `_0_0`
   - `_LS`
3. preserve the original explicit instance separately when it is useful
   downstream

## Workflow

1. read the requested core string
2. normalize it to a supported core family
3. preserve explicit instance information
4. select the GDB variant from the normalized family
5. return the mapping with short justification
