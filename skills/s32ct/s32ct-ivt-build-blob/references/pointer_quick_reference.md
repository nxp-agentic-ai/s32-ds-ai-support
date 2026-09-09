# IVT pointer quick reference (per S32 family)

This is a sanity-check companion to Step 1 of `s32ct-ivt-build-blob`. It is
**not** authoritative - the live MCU data model at
`<mcu_data_root>\processors\<mcu>\<sdk_version>\ivt\<mcu>.xml` always wins.
Use this table only when you need a quick guess of "what should I expect to
see?" before opening the XML, or when you need to surface plausible
candidates to the user.

Naming conventions differ by family and occasionally even by individual MCU
within a family (see the lowercase 'a' on `CM7_2 application` for S32K374).
Always confirm against the XML for the specific MCU/SDK combination you are
building for.

---

## S32K1 family (Cortex-M4/M4F, single-core, no HSE)

| Pointer name | Offset | Notes |
|---|---|---|
| `Application` | varies | Single-core application entry |
| `App Bootloader` | varies | Optional bootloader |

No HSE peripheral on S32K1; no defaults to disable.

---

## S32K3 family (Cortex-M7, up to 3 cores, HSE_B variant)

Verified members: S32K312, S32K314, S32K322, S32K324, S32K328, S32K338,
S32K342, S32K344, S32K348, S32K358, S32K374, S32K388.

| Pointer name | Offset | Carrying core / role |
|---|---|---|
| `CM7_0 Application` | `0x0C` | Boot core entry point |
| `CM7_1 Application` | `0x14` | Optional second-core entry |
| `CM7_2 application` | `0x1C` | **Lowercase 'a'** - observed on S32K374 |
| `HSE_B Firmware Image` | `0x2C` | **Disable when no HSE** - `disable_pointers: ["HSE_B Firmware Image"]` |
| `AppBL` | `0x30` | Optional application bootloader |
| `Recovery Application` | `0x40` | Optional recovery image |

Companion `<setting>` bitfield enables (same-bitfield sibling rule - only the
first survives `-SetValue`, edit the rest directly):

```xml
<setting name="cm7_0" value="true"/>
<setting name="cm7_1" value="true"/>   <!-- direct edit, -SetValue would clobber -->
<setting name="cm7_2" value="true"/>   <!-- direct edit -->
```

---

## S32G2 / S32G3 family (Cortex-A53 + Cortex-M7, HSE_H variant)

Verified members: S32G233A, S32G253A, S32G254A, S32G274A, S32G358A, S32G378A,
S32G399A.

| Pointer name | Role |
|---|---|
| `Application Bootloader` | Primary boot image |
| `DCD` | DDR configuration descriptor - disable if running from SRAM only |
| `HSE_H Firmware` | **Disable when no HSE** |
| `Self-test microcode` | Optional BIST microcode |

---

## S32Z / S32E family (Cortex-R52, lockstep + split modes)

Verified members: S32Z270, S32Z370, S32E284, S32E288.

| Pointer name | Role |
|---|---|
| `Cluster 0 Application` | Boot cluster |
| `Cluster 1 Application` | Secondary cluster |
| `Cluster 2 Application` | (S32E only) |
| `M33 Application` | System Manager core |
| `HSE_H Firmware` | **Disable when no HSE** |
| `Self-test microcode` | Optional |

---

## S32R / S32S family (radar / safety)

Verified members: S32R45, S32R47, S32S247TV.

| Pointer name | Role |
|---|---|
| `Application Bootloader` | Primary boot |
| `Application` | Main application |
| `DCD` | DDR descriptor |
| `HSE_H Firmware` | **Disable when no HSE** |

---

## S32N family (wide-cluster)

| Pointer name | Role |
|---|---|
| `Cluster N App` | Per-cluster apps (N = 0..) |
| `HSE Firmware` | **Disable when no HSE** |
| `Application Bootloader` | Primary boot |

---

## How to confirm against the data model

```powershell
$mcu = 'S32K374'
$sdk = 'PlatformSDK_S32K3'
$xml = "$env:ProgramData\NXP\mcu_data_25.12\processors\$mcu\$sdk\ivt\$mcu.xml"
Select-String -Path $xml -Pattern '<ivt_pointer ' | ForEach-Object { $_.Line.Trim() }
```

That prints the authoritative list of `<ivt_pointer id="..." name="..."
offset="..." size="..." allow_raw_code="...">` rows for the exact
MCU/SDK/package combination you have installed. Use the `name` attribute
verbatim in `payloads[i].pointer_name`.
