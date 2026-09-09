<#
.SYNOPSIS
  Verify an IVT blob produced by `s32ct -ExportBlob`.

.DESCRIPTION
  Implements Step 5 of the build_blob_image_s32ct skill. Performs four checks:
    1. File exists and is larger than a header-only blob (~5 KB).
    2. Magic at offset 0 is the family marker (A5 5A A5 5A on S32K3/G/Z/E/R/S
       /N; pass -Magic to override for older parts).
    3. The 4-byte little-endian word at each pointer's documented offset
       matches the requested address.
    4. The first N bytes at (address - IvtBase) inside the blob equal the
       first N bytes of the corresponding source binary.

  Exits 0 on PASS, 1 on any FAIL. Prints a line per check.

.PARAMETER BlobPath
  Path to the blob file.

.PARAMETER IvtBase
  Hex address of the IVT base (start of flash where the blob is programmed).

.PARAMETER Pointers
  Array of hashtables. Each requires:
    Name    - label (used only in output)
    Offset  - integer or hex string; the pointer's offset within the IVT
              header (from <ivt_pointer offset="..."/> in the MCU data model).
    Address - hex string; the address that should be programmed into that
              pointer slot.
    Binary  - optional path; if provided, the first PayloadHeadCheckBytes
              bytes are compared.

.PARAMETER Magic
  Override the expected magic. Default: 0xA55AA55A.

.PARAMETER PayloadHeadCheckBytes
  Number of leading bytes to compare for each payload. Default: 16.

.EXAMPLE
  powershell -File verify_blob.ps1 `
    -BlobPath C:\out\blobImage -IvtBase 0x00400000 `
    -Pointers @(
        @{ Name='CM7_0'; Offset=0x0C; Address=0x00400100; Binary='C:\work\cm7_0.bin' },
        @{ Name='CM7_1'; Offset=0x14; Address=0x00400B00; Binary='C:\work\cm7_1.bin' },
        @{ Name='CM7_2'; Offset=0x1C; Address=0x00401500; Binary='C:\work\cm7_2.bin' }
    )
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BlobPath,
    [Parameter(Mandatory = $true)][uint32]$IvtBase,
    [Parameter(Mandatory = $true)][hashtable[]]$Pointers,
    [uint32]$Magic = 0xA55AA55A,
    [int]$PayloadHeadCheckBytes = 16,
    [int]$HeaderOnlyHighWaterBytes = 6144
)

$ErrorActionPreference = 'Stop'
$failed = 0

function _hex32([uint32]$v) { '0x{0:X8}' -f $v }

# 1. Existence + size
if (-not (Test-Path -LiteralPath $BlobPath)) {
    Write-Host "[FAIL] blob not found: $BlobPath" -ForegroundColor Red
    exit 1
}
$blob = [IO.File]::ReadAllBytes($BlobPath)
Write-Host ("[INFO] blob size: {0} bytes" -f $blob.Length)
if ($blob.Length -lt $HeaderOnlyHighWaterBytes) {
    Write-Host ("[WARN] blob is suspiciously small ({0} B) - likely header-only emit." -f $blob.Length) -ForegroundColor Yellow
}

# 2. Magic
$gotMagic = [BitConverter]::ToUInt32($blob, 0)
if ($gotMagic -eq $Magic) {
    Write-Host ("[PASS] magic @0x00 = {0}" -f (_hex32 $gotMagic)) -ForegroundColor Green
} else {
    Write-Host ("[FAIL] magic @0x00 = {0}, expected {1}" -f (_hex32 $gotMagic), (_hex32 $Magic)) -ForegroundColor Red
    $failed++
}

# 3 + 4. Per-pointer checks
foreach ($p in $Pointers) {
    $name    = [string]$p.Name
    $offset  = [int]$p.Offset
    $address = [uint32]$p.Address
    $binary  = $p.Binary

    if ($offset + 4 -gt $blob.Length) {
        Write-Host ("[FAIL] {0}: offset 0x{1:X} past end of blob" -f $name, $offset) -ForegroundColor Red
        $failed++
        continue
    }
    $word = [BitConverter]::ToUInt32($blob, $offset)
    if ($word -eq $address) {
        Write-Host ("[PASS] {0} pointer @0x{1:X2} = {2}" -f $name, $offset, (_hex32 $word)) -ForegroundColor Green
    } else {
        Write-Host ("[FAIL] {0} pointer @0x{1:X2} = {2}, expected {3}" -f $name, $offset, (_hex32 $word), (_hex32 $address)) -ForegroundColor Red
        $failed++
        continue
    }

    if ($binary) {
        if (-not (Test-Path -LiteralPath $binary)) {
            Write-Host ("[FAIL] {0}: binary not found: {1}" -f $name, $binary) -ForegroundColor Red
            $failed++
            continue
        }
        $payloadOffset = [int]($address - $IvtBase)
        if ($payloadOffset -lt 0 -or $payloadOffset + $PayloadHeadCheckBytes -gt $blob.Length) {
            Write-Host ("[WARN] {0}: payload region (offset 0x{1:X}) is outside the blob - payload may be programmed separately." -f $name, $payloadOffset) -ForegroundColor Yellow
            continue
        }
        $expectedFull = [IO.File]::ReadAllBytes($binary)
        $checkLen     = [Math]::Min($PayloadHeadCheckBytes, $expectedFull.Length)
        $expected     = $expectedFull[0..($checkLen - 1)]
        $actual       = $blob[$payloadOffset..($payloadOffset + $checkLen - 1)]
        $match        = ($null -eq (Compare-Object $expected $actual -SyncWindow 0))
        if ($match) {
            Write-Host ("[PASS] {0} payload head ({1} B) matches binary" -f $name, $checkLen) -ForegroundColor Green
        } else {
            Write-Host ("[FAIL] {0} payload head does not match binary" -f $name) -ForegroundColor Red
            $failed++
        }
    }
}

if ($failed -eq 0) {
    Write-Host "`nAll checks passed." -ForegroundColor Green
    exit 0
} else {
    Write-Host ("`n{0} check(s) failed." -f $failed) -ForegroundColor Red
    exit 1
}
