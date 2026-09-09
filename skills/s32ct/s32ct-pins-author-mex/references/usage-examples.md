# Typical Usage Examples  -  s32ct-pins-author-mex

This file is referenced from `SKILL.md`. It captures concrete invocation
examples for the skill (schematic-parsing path, explicit-routings path,
different MCU/package, and incremental peripheral additions). Read it
when you need a template input payload for a real call.

## Typical Usage Examples

### 1. Board + peripheral wish-list (schematic parsing path)
```jsonc
{
  "board_name":         "S32K312MINI-EVB",
  "schematic_path":     "...\\S32K312MINI-EVB_Schematic_HardwarePackage_Rev1.pdf",
  "peripheral_request": { "SPI": 2, "UART": 2, "CAN": 2, "LIN": 2, "ADC": 2, "PWM": 1 },
  "mcu":                "S32K312",
  "package":            "S32K312_172HDQFP",
  "platform_sdk":       "PlatformSDK_S32K3",
  "output_path":        "C:\\tmp\\S32K312MINI_EVB.mex",
  "validate":           true,
  "generate_sources":   true
}
```

### 2. Explicit routings (deterministic / regression)
```jsonc
{
  "board_name":   "S32K312MINI-EVB",
  "mcu":          "S32K312",
  "package":      "S32K312_172HDQFP",
  "platform_sdk": "PlatformSDK_S32K3",
  "output_path":  "C:\\tmp\\fixed.mex",
  "overwrite":    true,
  "validate":     true,
  "routings": [
    { "function": "SPI #1 (FS26)", "peripheral": "LPSPI0", "signal": "lpspi0_sout", "pin": "PTB1" },
    { "function": "SPI #1 (FS26)", "peripheral": "LPSPI0", "signal": "lpspi0_sin",  "pin": "PTC9" },
    { "function": "SPI #1 (FS26)", "peripheral": "LPSPI0", "signal": "lpspi0_sck",  "pin": "PTC8" },
    { "function": "SPI #1 (FS26)", "peripheral": "LPSPI0", "signal": "lpspi0_pcs0", "pin": "PTB0" }
  ]
}
```

### 3. Different MCU/package (once template registered)
```jsonc
{
  "board_name":         "<custom-board>",
  "schematic_path":     "...\\<board>_schematic.pdf",
  "peripheral_request": { "SPI": 1, "UART": 2, "CAN": 1 },
  "mcu":                "<MCU>",
  "package":            "<MCU>_<PKG>",
  "platform_sdk":       "PlatformSDK_<family>",
  "output_path":        "C:\\tmp\\<board>.mex",
  "validate":           true
}
```

The skill resolves the matching reference `.mex` automatically; only the
triple changes from example 1.

### 4. Add a peripheral on top of an existing routing set
> *"Add a second PWM channel on PTB5 to the file I just generated."*

Re-run this skill with the full routings list (existing + new) and
`overwrite=true`. The skill is deterministic, so the result differs only
by the added `<pin>` entry.

---

## Caution - `overwrite: true` causes data loss

Every example above that sets `"overwrite": true` will permanently
replace any existing file at `output_path`, with no prompt and no
backup. Hand-authored edits in that `.mex` are lost and cannot be
recovered.

Before enabling it:

- Confirm the resolved `output_path` with the user.
- Back up or commit the existing `.mex` project.
- Prefer `"overwrite": false` (the default) so the run fails safely when
  the destination already exists.
