#!/usr/bin/env python3
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

"""
patch_mex_pointers.py
=====================

Parameter-driven implementation of Step 3 of the s32ct-ivt-build-blob skill.

Applies three coordinated edits to an S32 Configuration Tools `.mex`:

  3a. For each --payload "<name>" <binary> <address>:
        - locate <ivt_pointer ... name="<name>" ...>
        - set size       = byte length of <binary>
        - set start_addr = <address>
        - set file_path  = <absolute path to binary>
        - set reserved   = "false"

  3b. For each --enable <name>=<value>:
        - locate <setting name="<name>" .../> anywhere in the .mex
        - set value="<value>"   (used for same-bitfield enable bits that
          -SetValue would clobber)

  3c. For each --disable "<name>":
        - locate <ivt_pointer ... name="<name>" ...>
        - set reserved="true"

The script is idempotent - running it twice produces the same result as
running it once.

Usage:
    python patch_mex_pointers.py <path/to/blob.mex>
        --payload "CM7_0 Application" C:/work/cm7_0.bin 0x00400100
        --payload "CM7_1 Application" C:/work/cm7_1.bin 0x00400B00
        --payload "CM7_2 application" C:/work/cm7_2.bin 0x00401500
        --disable "HSE_B Firmware Image"
        --enable cm7_1=true
        --enable cm7_2=true
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def _read(mex_path: Path) -> str:
    return mex_path.read_text(encoding="utf-8")


def _write(mex_path: Path, content: str) -> None:
    mex_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 3a - patch a payload-bearing pointer
# ---------------------------------------------------------------------------
def patch_payload(
    content: str,
    pointer_name: str,
    binary_path: str,
    address: str,
) -> Tuple[str, int]:
    """Return (new_content, bytes_embedded). Raises if the pointer is absent."""
    if not os.path.isfile(binary_path):
        raise FileNotFoundError(f"Binary not found: {binary_path}")
    size = os.path.getsize(binary_path)

    # Match an entire <ivt_pointer ... name="<pointer_name>" ...> opening tag
    # (one line in S32CT-emitted .mex files). Escape regex meta in the name.
    pattern = re.compile(
        r'(<ivt_pointer\s+[^>]*?\bname="'
        + re.escape(pointer_name)
        + r'"[^>]*?>)',
        re.DOTALL,
    )

    def _patch(match: re.Match[str]) -> str:
        tag = match.group(1)
        tag = _set_attr(tag, "size", str(size))
        tag = _set_attr(tag, "start_address", address)
        tag = _set_attr(tag, "file_path", binary_path)
        tag = _set_attr(tag, "reserved", "false")
        return tag

    new_content, n = pattern.subn(_patch, content, count=1)
    if n == 0:
        raise KeyError(
            f'ivt_pointer name="{pointer_name}" not found in .mex. '
            f"Check the MCU's data model for the exact pointer name."
        )
    return new_content, size


# ---------------------------------------------------------------------------
# 3b - flip a same-bitfield enable in <setting name="..." value="..."/>
# ---------------------------------------------------------------------------
def patch_enable(content: str, name: str, value: str) -> Tuple[str, int]:
    pattern = re.compile(
        r'(<setting\s+name="' + re.escape(name) + r'"\s+value=")[^"]*(")'
    )
    new_content, n = pattern.subn(r"\g<1>" + value + r"\g<2>", content, count=1)
    return new_content, n


# ---------------------------------------------------------------------------
# 3c - disable a default-active pointer
# ---------------------------------------------------------------------------
def patch_disable(content: str, pointer_name: str) -> Tuple[str, int]:
    pattern = re.compile(
        r'(<ivt_pointer\s+[^>]*?\bname="'
        + re.escape(pointer_name)
        + r'"[^>]*?>)',
        re.DOTALL,
    )

    def _patch(match: re.Match[str]) -> str:
        return _set_attr(match.group(1), "reserved", "true")

    new_content, n = pattern.subn(_patch, content, count=1)
    return new_content, n


# ---------------------------------------------------------------------------
# attribute setter: replace `name="..."` in a tag, inserting it before `/>`
# if missing.
# ---------------------------------------------------------------------------
def _set_attr(tag: str, name: str, value: str) -> str:
    attr = re.compile(r"\b" + re.escape(name) + r'="[^"]*"')
    new_attr = f'{name}="{value}"'
    if attr.search(tag):
        return attr.sub(new_attr, tag, count=1)
    # Insert before the closing `>` or `/>`.
    if tag.rstrip().endswith("/>"):
        return tag.rstrip()[:-2].rstrip() + f" {new_attr}/>"
    return tag.rstrip()[:-1].rstrip() + f" {new_attr}>"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("mex", type=Path, help="Path to the .mex to patch in place.")
    parser.add_argument(
        "--payload",
        nargs=3,
        action="append",
        metavar=("POINTER_NAME", "BINARY_PATH", "ADDRESS"),
        default=[],
        help="A payload-bearing pointer. Repeat once per binary.",
    )
    parser.add_argument(
        "--disable",
        action="append",
        metavar="POINTER_NAME",
        default=[],
        help="A default-active pointer to mark reserved. Repeat as needed.",
    )
    parser.add_argument(
        "--enable",
        action="append",
        metavar="NAME=VALUE",
        default=[],
        help="A <setting name=NAME value=VALUE/> override. Repeat as needed.",
    )
    args = parser.parse_args(argv)

    if not args.mex.is_file():
        print(f"error: {args.mex} not found", file=sys.stderr)
        return 2

    content = _read(args.mex)

    embedded = []
    for name, path, addr in args.payload:
        content, size = patch_payload(content, name, path, addr)
        embedded.append((name, addr, size, path))
        print(f"[payload] {name:30s} addr={addr}  size={size}  file={path}")

    for spec in args.enable:
        if "=" not in spec:
            print(f"error: --enable expects NAME=VALUE, got {spec!r}", file=sys.stderr)
            return 2
        name, value = spec.split("=", 1)
        content, n = patch_enable(content, name, value)
        status = "ok" if n else "not found"
        print(f"[enable]  {name}={value}  ({status})")

    for name in args.disable:
        content, n = patch_disable(content, name)
        status = "ok" if n else "not found (already absent?)"
        print(f"[disable] {name:30s}  ({status})")

    _write(args.mex, content)
    print(f"\nPatched {args.mex}")
    print(f"  payloads embedded : {len(embedded)}")
    print(f"  enables overridden: {len(args.enable)}")
    print(f"  pointers disabled : {len(args.disable)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
