# Copyright 2026 NXP
#
# NXP Proprietary. This software is owned or controlled by NXP and may
# only be used strictly in accordance with the applicable license terms.
# By expressly accepting such terms or by downloading, installing,
# activating and/or otherwise using the software, you are agreeing that
# you have read, and that you agree to comply with and are bound by,
# such license terms.  If you do not agree to be bound by the applicable
# license terms, then you may not retain, install, activate or otherwise
# use the software.

"""Verify an IVT blob produced by the S32CT -ExportBlob export.

Cross-platform equivalent of verify_blob.ps1 (Windows PowerShell). Use
this variant on Linux / macOS, or anywhere a single implementation is
preferred. Both scripts perform the same four checks:

  1. File exists and is larger than a header-only blob (~5 KB).
  2. Magic at offset 0 is the family marker (A5 5A A5 5A on
     S32K3/G/Z/E/R/S/N; pass --magic to override for older parts).
  3. The 4-byte little-endian word at each pointer's documented offset
     matches the requested address.
  4. The first N bytes at (address - ivt_base) inside the blob equal the
     first N bytes of the corresponding source binary.

This script only reads files; it never writes or modifies anything.

Usage:
    python verify_blob.py --blob <path> --ivt-base 0x00400000 \\
        --pointer "CM7_0:0x0C:0x00400100:/work/cm7_0.bin" \\
        --pointer "CM7_1:0x14:0x00400B00:/work/cm7_1.bin" \\
        --pointer "CM7_2:0x1C:0x00401500"

Each --pointer takes NAME:OFFSET:ADDRESS[:BINARY] where OFFSET and
ADDRESS accept hex (0x..) or decimal. BINARY is optional; when given,
the payload head is compared.

Exit codes:
    0 all checks passed
    1 at least one check failed
    2 usage / input error
"""

import argparse
import struct
import sys
from pathlib import Path

DEFAULT_MAGIC = 0xA55AA55A
DEFAULT_PAYLOAD_HEAD_BYTES = 16
DEFAULT_HEADER_ONLY_HIGH_WATER = 6144


def parse_int(text, label):
    """Parse a hex (0x..) or decimal integer."""
    try:
        return int(text, 16) if text.lower().startswith("0x") else int(text, 10)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{label}: expected a hex (0x..) or decimal integer, got {text!r}"
        )


def parse_pointer(spec):
    """Parse NAME:OFFSET:ADDRESS[:BINARY] into a dict."""
    parts = spec.split(":")
    # A Windows binary path can contain a drive-letter colon, so rejoin
    # everything past the third field.
    if len(parts) < 3:
        raise argparse.ArgumentTypeError(
            f"--pointer needs NAME:OFFSET:ADDRESS[:BINARY], got {spec!r}"
        )
    name, offset_s, address_s = parts[0], parts[1], parts[2]
    binary = ":".join(parts[3:]) if len(parts) > 3 else ""
    return {
        "name": name,
        "offset": parse_int(offset_s, f"pointer {name} offset"),
        "address": parse_int(address_s, f"pointer {name} address"),
        "binary": binary,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify an IVT blob. Read-only; nothing is modified.",
    )
    parser.add_argument("--blob", required=True, type=Path, help="Path to the blob file.")
    parser.add_argument(
        "--ivt-base",
        required=True,
        help="Hex or decimal address of the IVT base (start of flash).",
    )
    parser.add_argument(
        "--pointer",
        action="append",
        default=[],
        metavar="NAME:OFFSET:ADDRESS[:BINARY]",
        help="Pointer to verify. Repeatable.",
    )
    parser.add_argument(
        "--magic",
        default=hex(DEFAULT_MAGIC),
        help=f"Expected magic at offset 0 (default: {hex(DEFAULT_MAGIC)}).",
    )
    parser.add_argument(
        "--payload-head-bytes",
        type=int,
        default=DEFAULT_PAYLOAD_HEAD_BYTES,
        help="Leading bytes compared per payload (default: %(default)s).",
    )
    parser.add_argument(
        "--header-only-high-water",
        type=int,
        default=DEFAULT_HEADER_ONLY_HIGH_WATER,
        help=(
            "Warn when the blob is smaller than this, which indicates a "
            "header-only emit (default: %(default)s)."
        ),
    )
    return parser.parse_args(argv)


def hex32(value):
    return f"0x{value & 0xFFFFFFFF:08X}"


def read_u32_le(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def main(argv=None):
    args = parse_args(argv)

    ivt_base = parse_int(args.ivt_base, "--ivt-base")
    magic = parse_int(args.magic, "--magic")
    pointers = [parse_pointer(spec) for spec in args.pointer]

    failed = 0

    # 1. Existence + size.
    if not args.blob.is_file():
        print(f"[FAIL] blob not found: {args.blob}")
        return 1
    blob = args.blob.read_bytes()
    print(f"[INFO] blob size: {len(blob)} bytes")
    if len(blob) < args.header_only_high_water:
        print(
            f"[WARN] blob is suspiciously small ({len(blob)} B) - "
            f"likely header-only emit."
        )

    # 2. Magic.
    if len(blob) < 4:
        print("[FAIL] blob is shorter than 4 bytes; no magic to read")
        return 1
    got_magic = read_u32_le(blob, 0)
    if got_magic == magic:
        print(f"[PASS] magic @0x00 = {hex32(got_magic)}")
    else:
        print(f"[FAIL] magic @0x00 = {hex32(got_magic)}, expected {hex32(magic)}")
        failed += 1

    # 3 + 4. Per-pointer checks.
    for ptr in pointers:
        name = ptr["name"]
        offset = ptr["offset"]
        address = ptr["address"]
        binary = ptr["binary"]

        if offset + 4 > len(blob):
            print(f"[FAIL] {name}: offset {hex(offset)} past end of blob")
            failed += 1
            continue

        word = read_u32_le(blob, offset)
        if word == address:
            print(f"[PASS] {name} pointer @{hex(offset)} = {hex32(word)}")
        else:
            print(
                f"[FAIL] {name} pointer @{hex(offset)} = {hex32(word)}, "
                f"expected {hex32(address)}"
            )
            failed += 1
            continue

        if not binary:
            continue

        binary_path = Path(binary)
        if not binary_path.is_file():
            print(f"[FAIL] {name}: binary not found: {binary_path}")
            failed += 1
            continue

        payload_offset = address - ivt_base
        if payload_offset < 0 or payload_offset + args.payload_head_bytes > len(blob):
            print(
                f"[WARN] {name}: payload region (offset {hex(payload_offset)}) "
                f"is outside the blob - payload may be programmed separately."
            )
            continue

        expected_full = binary_path.read_bytes()
        check_len = min(args.payload_head_bytes, len(expected_full))
        expected = expected_full[:check_len]
        actual = blob[payload_offset:payload_offset + check_len]
        if expected == actual:
            print(f"[PASS] {name} payload head ({check_len} B) matches binary")
        else:
            print(f"[FAIL] {name} payload head does not match binary")
            failed += 1

    if failed == 0:
        print("\nAll checks passed.")
        return 0
    print(f"\n{failed} check(s) failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
