# Authoring an IVT blob - full step-by-step procedure

Companion reference for `s32ct-ivt-build-blob`. Covers the 5-step recipe
in narrative detail, family-specific notes, common failure modes, and
notes for reasoning. See `pointer_quick_reference.md` for the extended
per-family pointer table.

## Why the coordinated edits are required

`-ExportBlob` alone produces an IVT header with no payload because:

1. Each `<ivt_pointer>` ships with `size="4"` - the address-only width.
   Setting `file_path` to a multi-KB binary without bumping `size` yields
   the misleading error *"binary file (N bytes) is greater than the new
   IVT pointer size (4 bytes)"*. The message is about the payload area,
   not the 4-byte pointer slot inside the IVT header.
2. Default-active security pointers (`HSE_B Firmware Image` on S32K3 /
   S32Z/E, `HSE_H Firmware` on S32G) reserve regions of flash that
   almost always collide with user payload addresses. The validator
   refuses the export with a `segment overlaps with: ...` message that
   names both pointers exactly.

`-AutoAlign` is *conditionally* required - only when the exporter
reports overlap or alignment errors that cannot be resolved by disabling
the colliding pointer manually. Adding `-AutoAlign` unconditionally
masks layout problems the user may want to see surfaced.

## Step 1 - Discover the MCU's pointer set (read-only)

Read the IVT data model:

```
<mcu_data_root>/processors/<mcu>/<sdk_version>/ivt/<mcu>.xml
```

`mcu_data_root` is reported by `nxp_s32ct_execute_action(action_name="s32ct.env_status", params={})` (typical
value `C:/ProgramData/NXP/mcu_data_*`).

Extract every `<ivt_pointer id="..." name="..." offset="..." size="..."
allow_raw_code="...">`. The `name` attribute is the user-facing label
and is what `payloads[i].pointer_name` must match. Cross-check every
requested pointer name; if any doesn't match, stop and list the legal
names for this MCU - naming differs across families and is the single
most common user error.

**Example excerpt (S32K374):**

```text
<ivt_pointer id="cm7_0_application" name="CM7_0 Application" offset="0Ch" ...>
<ivt_pointer id="cm7_1_application" name="CM7_1 Application" offset="14h" ...>
<ivt_pointer id="cm7_2_application" name="CM7_2 application" offset="1Ch" ...>  <!-- lowercase 'a' -->
<ivt_pointer id="encr_hse_address"  name="HSE_B Firmware Image" offset="2Ch" ...>
```

Note the case-sensitivity gotcha on `CM7_2 application` (S32K374). The
data model is authoritative - never invent names from training data.

A per-family quick-reference table lives at `pointer_quick_reference.md`.
Use it as a sanity check only - the XML is the source of truth.

## Step 2 - Create the skeleton `.mex`

Minimum viable call:

```python
nxp_s32ct_execute_action(
    action_name="s32ct.configure_ivt",
    params={
        "empty_config": True,
        "mcu": "<mcu>",
        "sdk_version": "<sdk_version>",
        "config_name": "<config_name>",     # default "blob"
        "enable_tool": True,
        "set_values": ["cm7_0=true"],       # see clobber rule
        "export_kind": "ExportMEX",
        "output_dir": "<work_dir>",
        "data_dir": "<work_dir>/ws",        # isolated -data workspace
    },
)
```

**`-SetValue` clobber rule**: When an MCU exposes several enable bits in
the same bitfield (e.g. `cm7_0`, `cm7_1`, `cm7_2` on S32K3), `-SetValue`
only persists the first. Set only one here; the remaining siblings are
flipped in Step 3 directly in the XML.

## Step 3 - Patch the `.mex` (heart of the recipe)

Open `<work_dir>/<config_name>.mex` and apply three classes of edits.

### 3a. For each payload-bearing pointer in `payloads`

Locate the matching `<ivt_pointer ... name="<pointer_name>" ...>` row
and set:

- `size="<binary length in bytes>"` (was `"4"`)
- `start_address="<payloads[i].address>"`
- `file_path="<absolute path to binary>"` (was `"N/A"`)
- `reserved="false"` (was usually `"true"`)

The `size` attribute is the undocumented critical part. The validator
reads it as "how many bytes does this payload occupy in the blob".
Leaving it at `"4"` while setting `file_path` to a multi-KB binary
triggers the misleading *"binary file (N bytes) is greater than the new
IVT pointer size (4 bytes)"* error.

### 3b. Same-bitfield enables that `-SetValue` couldn't carry

For every co-resident enable the user wants on, edit the `<setting>`
node directly:

```xml
<setting name="cm7_1" value="true"/>
<setting name="cm7_2" value="true"/>
```

### 3c. Disable colliding defaults

For each name in `disable_pointers`, set `reserved="true"` on its
`<ivt_pointer>` row. The most common case is `HSE_B Firmware Image`
(S32K3, S32Z/E) or `HSE_H Firmware` (S32G): their default
`start_address` falls inside the payload region your binaries occupy,
and the IVT validator refuses to emit the blob with a `segment overlaps
with: ...` message that names both pointers exactly.

A parameter-driven helper is available at
`scripts/patch_mex_pointers.py` - use it to make Step 3 deterministic
across runs.

## Step 4 - Export the blob

**Attempt 1 - no `-AutoAlign`** (preferred):

```python
nxp_s32ct_execute_action(
    action_name="s32ct.configure_ivt",
    params={
        "project_path": "<work_dir>/<config_name>.mex",
        "enable_tool": True,
        "export_kind": "ExportBlob",
        "output_dir": "<output_dir>",
        "data_dir": "<work_dir>/ws",
    },
)
```

This is the right default. When Step 3 has been done correctly (all
payload-bearing pointers have their `size` and `start_address` set, and
any default-active pointer that collides with the payload region has
been disabled in Step 3c), the IVT exporter lays out the blob from the
explicit addresses and emits a payload-bearing blob in one shot.

**Inspect the result of Attempt 1 before deciding what to do next.**
Three outcomes:

| Outcome | Meaning | Action |
|---|---|---|
| Output file exists and is > ~5 KB | Success. Skip Attempt 2. | Go to Step 5. |
| stderr contains `segment overlaps with: <name>` | An undisclosed default-active pointer is still active and its layout collides with the payload region. | Prefer disabling that pointer in Step 3c (add it to `disable_pointers` and re-run from Step 3). Use `-AutoAlign` only if the colliding pointer is one the user actually wants in the blob (in which case the layout needs re-flowing). |
| stderr contains a different alignment/layout complaint | A user-supplied `address` value doesn't satisfy the family's IVT alignment rule. | Either fix the address in `payloads[i].address` (preferred), or fall back to Attempt 2 which lets the tool re-align. |

**Attempt 2 - with `-AutoAlign`** (conditional fallback):

```python
nxp_s32ct_execute_action(
    action_name="s32ct.configure_ivt",
    params={
        "project_path": "<work_dir>/<config_name>.mex",
        "enable_tool": True,
        "auto_align": "",                     # -AutoAlign with no address
        "export_kind": "ExportBlob",
        "output_dir": "<output_dir>",
        "data_dir": "<work_dir>/ws",
    },
)
```

`-AutoAlign` re-runs the IVT layout pass and resolves overlaps /
misaligned addresses by shifting payloads. Use it only when Attempt 1
surfaced an overlap or alignment error you cannot fix at the pointer
level, because it also masks layout problems the user may want to see.

## Step 5 - Verify

A clean blob must satisfy all of:

1. File exists at `<output_dir>/blobImage` (case matters on Linux).
2. File size > IVT header size (a header-only blob is typically <= ~5 KB
   regardless of `size` values - anything close to that is a red flag).
3. Magic at offset `0x00` = `A5 5A A5 5A`.
4. The 4-byte little-endian word at each pointer's documented `offset`
   (from Step 1) equals the requested `address`.
5. Disabled pointers read `0xFFFFFFFF` (or the family's documented
   "unused" sentinel - `0x00000000` on some older parts).
6. The first ~16 bytes at `(address - ivt_base)` inside the blob equal
   the first ~16 bytes of the corresponding source binary (sanity check
   that the payload was actually embedded, not just pointed at).

Two interchangeable verifiers ship with the skill - use whichever suits
the platform. Both run the same four checks and print PASS/FAIL per
check, exiting 0 on pass and 1 on any failure.

Windows PowerShell:

```powershell
powershell -File scripts/verify_blob.ps1 `
    -BlobPath C:\out\blobImage -IvtBase 0x00400000 `
    -Pointers @(
        @{ Name='CM7_0'; Offset=0x0C; Address=0x00400100; Binary='C:\work\cm7_0.bin' },
        @{ Name='CM7_1'; Offset=0x14; Address=0x00400B00; Binary='C:\work\cm7_1.bin' }
    )
```

Linux / macOS (or anywhere, since it is plain Python):

```sh
python3 scripts/verify_blob.py \
    --blob /out/blobImage --ivt-base 0x00400000 \
    --pointer "CM7_0:0x0C:0x00400100:/work/cm7_0.bin" \
    --pointer "CM7_1:0x14:0x00400B00:/work/cm7_1.bin"
```

Each `--pointer` takes `NAME:OFFSET:ADDRESS[:BINARY]`; `OFFSET` and
`ADDRESS` accept hex or decimal, and `BINARY` is optional (when given,
the payload head is compared).

**Exit code 0 does NOT mean a blob was produced.** Always parse stderr
for `BLOB Image Export failed.` before reporting success.

## Worked example - S32K374, three CM7 cores, no HSE

```yaml
mcu: S32K374
sdk_version: PlatformSDK_S32K3
payloads:
  - { pointer_name: "CM7_0 Application", binary_path: "C:/work/cm7_0.bin", address: "0x00400100" }
  - { pointer_name: "CM7_1 Application", binary_path: "C:/work/cm7_1.bin", address: "0x00400B00" }
  - { pointer_name: "CM7_2 application", binary_path: "C:/work/cm7_2.bin", address: "0x00401500" }
disable_pointers: ["HSE_B Firmware Image"]
output_dir: "C:/work/out"
ivt_base: "0x00400000"
```

Result (Attempt 1 succeeds without `-AutoAlign` because Step 3c disabled
the only default-active overlapper):

```text
C:/work/out/blobImage   (7872 bytes - IVT header + 3 embedded payloads)
  offset 0x00 = A5 5A A5 5A
  offset 0x0C = 00 01 40 00   (CM7_0 = 0x00400100)
  offset 0x14 = 00 0B 40 00   (CM7_1 = 0x00400B00)
  offset 0x1C = 00 15 40 00   (CM7_2 = 0x00401500)
  offset 0x2C = FF FF FF FF   (HSE_B disabled)
```

## Family-specific notes

Observations to set expectations - the data model is always
authoritative. See `pointer_quick_reference.md` for the fuller table.

| MCU family | Typical payload pointers | Default to disable when no HSE |
|---|---|---|
| S32K1 | `Application`, `App Bootloader` | usually none |
| S32K3 (S32K312/344/358/374) | `CM7_0 Application`, `CM7_1 Application`, `CM7_2 application` (lowercase 'a'), `AppBL`, `Recovery Application` | `HSE_B Firmware Image` |
| S32G2 / S32G3 | `Application Bootloader`, `DCD`, `HSE_H Firmware`, `Self-test microcode` | `HSE_H Firmware`, `DCD` (if no DDR init) |
| S32Z / S32E | `Cluster N Application`, `M33 Application`, `HSE_H Firmware` | `HSE_H Firmware`, `Self-test microcode` |
| S32R / S32S | `Application Bootloader`, `Application`, `DCD`, `HSE_H Firmware` | `HSE_H Firmware` |
| S32N | `Cluster N App`, `HSE Firmware`, `Application Bootloader` | `HSE Firmware` |

## Common failure modes and remedies

| Symptom | Cause | Remedy |
|---|---|---|
| Error: *"binary file (N bytes) is greater than the new IVT pointer size (4 bytes)"* | Step 3a's `size` attribute not bumped from `"4"`. | Set `size` on each payload-bearing pointer to the binary's actual byte length. |
| Error: *"segment overlaps with: {other pointer}"* | A default-active pointer's address collides with a payload region. | Preferred: add the named pointer to `disable_pointers` and re-run. Fallback: re-run Step 4 with `auto_align=""` to let the tool shift payloads. |
| Error: *"start address is not aligned to ..."* | A `payloads[i].address` value violates the family's IVT alignment rule. | Preferred: fix the address. Fallback: re-run Step 4 with `auto_align=""`. |
| Exit code 0 but no file in `output_dir` | Unresolved overlap or alignment violation; tool aborts silently after an unhandled layout failure. | Inspect stderr for the actual error and apply the relevant row above. |
| Exit code 0 but blob is only ~5 KB | Header-only emit. Almost always means `file_path` is still `"N/A"` or `size` is still `"4"` on the payload pointers. | Re-check Step 3a. |
| Error: *"pointer name not found"* | The `pointer_name` doesn't match this MCU's data model exactly. | Re-read Step 1's XML; case and spacing are significant (e.g. `CM7_2 application` on S32K374). |
| Stale outputs across consecutive runs | The S32CT `-data` workspace caches state from a crashed earlier run. | Wipe `<work_dir>/ws` between runs - see the caution below before deleting anything. |

> **Caution - only delete the workspace you created.** The wipe applies
> *solely* to the isolated `<work_dir>/ws` Eclipse workspace created in
> Step 2. Never delete a directory the user did not designate as scratch:
> confirm the resolved absolute path with the user first, and never
> recurse into a project, source or output directory. If `<work_dir>` was
> not created by this workflow, create a fresh one instead of wiping.

## Notes for reasoning

- The `.mex` schema is a one-to-one wrapper around the data-model XML;
  every attribute changed in Step 3 has a direct register-level effect
  at boot.
- Don't set pointer addresses via `-SetValue address=0x...` - that
  writes into bitfield `<setting>` nodes, not into `<ivt_pointer>` rows.
  Pointer addresses are only writable via direct XML edit (or the GUI).
- `file_path="N/A"` with `start_address` set and `reserved="false"`
  produces a valid "addresses-only" blob (~5 KB on K3). Useful when the
  user's binaries are programmed separately and only the IVT needs to
  point at them. Also a useful fallback when a `size` value is unknown.
- `-AutoAlign` is the conditional remedy for overlap and alignment
  errors, not a default. Try Step 4 Attempt 1 first; fall back to
  Attempt 2 (with `auto_align=""`) only when the exporter explicitly
  reports an overlap that cannot be cleared via `disable_pointers`, or
  an alignment violation the user won't fix at the pointer-address
  level.
- When grafting a Step 2 `.mex` into an existing project, run
  `s32ct.sanitize` before validation - it removes cross-references
  to drivers that aren't present.
- This skill is the write-side counterpart of `s32ct-clocks-info` and
  `s32ct-peripherals-info` (read-only data-model lookup skills).

## Hand-off

> **Warning - flashing an IVT blob is irreversible and can brick the
> device.** The IVT determines how the SoC boots; writing a malformed or
> mis-targeted blob can leave the device unbootable and unrecoverable
> without external hardware. Before handing off to the flash tool:
>
> - Confirm the exact target device / board with the user.
> - Confirm the blob passed verification (`verify_blob.ps1` or
>   `verify_blob.py`) and that the pointer addresses match the intended
>   memory map.
> - Confirm the user accepts the risk, and that a recovery path exists
>   (serial boot / debug probe) if the device fails to boot.
>
> Never flash automatically as a continuation of blob generation - always
> stop and get explicit confirmation.

After the blob is produced and verified:
- Use the `nxp_s32flashtool` extension to program it to the device.
- Re-run the workflow from Step 2 (with the skeleton already on disk)
  when only the payload contents change - the patched `.mex` can be
  re-loaded with `project_path` and re-exported in seconds.
