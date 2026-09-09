# Worked example  -  s32ct-pins-author-mex

This file is referenced from `SKILL.md`. It contains the verified
end-to-end run that produced a Pins `.mex` for the S32K312MINI-EVB.
The example is illustrative of every supported target  -  only the
`(mcu, package, platform_sdk)` triple and the schematic change for
other boards.

---

## Worked example (verified end-to-end on `S32K312MINI-EVB`)

This example is illustrative of *every* supported target  -  only the
`(mcu, package, platform_sdk)` triple and the schematic change for other
boards.

Inputs:

```jsonc
{
  "board_name":         "S32K312MINI-EVB",
  "schematic_path":     "C:\\Users\\...\\S32K312MINI-EVB_Schematic_HardwarePackage_Rev1.pdf",
  "peripheral_request": { "SPI": 2, "UART": 2, "CAN": 2, "LIN": 2, "ADC": 2, "PWM": 1 },
  "mcu":                "S32K312",
  "package":            "S32K312_172HDQFP",
  "platform_sdk":       "PlatformSDK_S32K3",
  "output_path":        "<your-workspace>\\S32K312MINI_EVB.mex",
  "overwrite":          true,
  "validate":           true,
  "generate_sources":   true
}
```

> **Caution - `"overwrite": true` destroys data.** Any existing file at
> `output_path` (and any copied sidecar such as
> `ClockConfigurationMappings.txt`) is permanently replaced with no
> prompt and no backup. Before enabling it, confirm the target path with
> the user, and back up or commit the existing `.mex` project. Use
> `"overwrite": false` to fail safely when the file already exists.

Produced final routing table (23 pins, 11 peripheral instances, zero
conflicts):

| Function | Peripheral | Signal | Pin | pin_num |
|---|---|---|---|---|
| SPI #1 (FS26 on-board) | LPSPI0 | lpspi0_sout | PTB1 | 94 |
| SPI #1 (FS26 on-board) | LPSPI0 | lpspi0_sin  | PTC9 | 97 |
| SPI #1 (FS26 on-board) | LPSPI0 | lpspi0_sck  | PTC8 | 98 |
| SPI #1 (FS26 on-board) | LPSPI0 | lpspi0_pcs0 | PTB0 | 95 |
| SPI #2 (Arduino)       | LPSPI1 | lpspi1_sout | PTB16 | 112 |
| SPI #2 (Arduino)       | LPSPI1 | lpspi1_sin  | PTA20 | 3 |
| SPI #2 (Arduino)       | LPSPI1 | lpspi1_sck  | PTA28 | 30 |
| SPI #2 (Arduino)       | LPSPI1 | lpspi1_pcs0 | PTA21 | 6 |
| UART #1 (OpenSDA)      | LPUART6 | lpuart6_tx | PTA16 | 143 |
| UART #1 (OpenSDA)      | LPUART6 | lpuart6_rx | PTA15 | 145 |
| UART #2 (Arduino)      | LPUART3 | lpuart3_tx | PTD2 | 121 |
| UART #2 (Arduino)      | LPUART3 | lpuart3_rx | PTD3 | 120 |
| CAN #1 (Arduino)       | CAN1 | can1_tx | PTB22 | 67 |
| CAN #1 (Arduino)       | CAN1 | can1_rx | PTB23 | 69 |
| CAN #2 (Arduino)       | CAN4 | can4_tx | PTB3 | 74 |
| CAN #2 (Arduino)       | CAN4 | can4_rx | PTB2 | 79 |
| LIN #1 (TJA1022 on-board) | LPUART5 | lpuart5_tx | PTB27 | 75 |
| LIN #1 (TJA1022 on-board) | LPUART5 | lpuart5_rx | PTB28 | 76 |
| LIN #2 (Arduino LIN-B)    | LPUART2 | lpuart2_tx | PTC15 | 68 |
| LIN #2 (Arduino LIN-B)    | LPUART2 | lpuart2_rx | PTC16 | 66 |
| ADC #1 (Arduino A0)    | ADC0 | adc0_p1 | PTD0 | 8 |
| ADC #2 (Arduino A2)    | ADC1 | adc1_p1 | PTA13 | 155 |
| PWM (Arduino)          | eMIOS_0 | emios_0_ch_4_g | PTB4 | 48 |

Validation: `toolsc.exe -Load ... -HeadlessTool Pins -ShowProblems` -> exit 0,
no problem lines after the four-step stderr filter. Sources:
`Siul2_Port_Ip_Cfg.[ch]` + `Tspc_Port_Ip_Cfg.[ch]` emitted to
`generated_pins\board\`.

### Caveats from that run (record them in the *Conflict report*)

- **CAN0 (on-board TJA1043) was deliberately not selected**  -  its only
  legal pins on this package (`PTB0`/`PTB1`) overlap the on-board SBC
  SPI. The skill picked `CAN1` + `CAN4` on free Arduino pins instead.
  When the user needs the TJA1043 specifically, they must drop LPSPI0
  from the request (or accept that the SBC link will be unconfigured).
- **LIN1 on PTB9/PTB10** as drawn on the schematic is **FlexIO-based**
  (those pins have no LPUART alt function on this package). The skill
  chose `LPUART5` on PTB27/PTB28  -  the *other* TJA1022 channel  -  to
  deliver a real, hardware-LIN-capable routing for LIN #1. Software LIN
  over FlexIO is not modelled by this skill.

These two caveats illustrate the general lesson: prefer-onboard is a
*hint*; if it conflicts with conflict-freeness, the skill always wins on
conflict-freeness and records the rejection.

---


