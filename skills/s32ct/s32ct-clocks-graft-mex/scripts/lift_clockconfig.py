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

"""Lift `<clock_configuration>` from an example .mex into the target.

Workflow C: when an authoritative example exists (typically an RTD
example .mex or a sibling NXP EVB project for the same MCU/package),
the safest path is to copy its whole ClockConfig0 block into the user's
project, replacing the existing one.

After lift, the target needs:
  1) `s32ct.sanitize` to rewrite any `/Mcu/...` refs that don't
     resolve on the target.
  2) `s32ct.validate tool_name=Clocks` (and Peripherals + Pins regression).

Usage:
    python lift_clockconfig.py --target project.mex --example ref.mex --out new.mex
"""
import argparse
import re
import sys
from pathlib import Path


def extract_clock_configuration(txt: str, name: str = "ClockConfig0") -> str | None:
    pat = (
        rf'<clock_configuration\b[^>]*name="{re.escape(name)}"[^>]*>.*?'
        r'</clock_configuration>'
    )
    m = re.search(pat, txt, re.DOTALL)
    return m.group(0) if m else None


def replace_clock_configuration(txt: str, new_block: str, name: str = "ClockConfig0") -> str:
    pat = (
        rf'<clock_configuration\b[^>]*name="{re.escape(name)}"[^>]*>.*?'
        r'</clock_configuration>'
    )
    new_txt, n = re.subn(pat, lambda _: new_block, txt, count=1, flags=re.DOTALL)
    if n == 0:
        raise RuntimeError(f"No <clock_configuration name='{name}'> in target")
    return new_txt


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True, help="The .mex to extend")
    p.add_argument("--example", required=True, help="The source RTD example .mex")
    p.add_argument("--name", default="ClockConfig0", help="ClockConfig name (default: ClockConfig0)")
    p.add_argument("--out", required=True, help="Output .mex path")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    tgt = Path(args.target)
    ex = Path(args.example)
    out = Path(args.out)
    for label, p_ in (("target", tgt), ("example", ex)):
        if not p_.exists():
            print(f"{label} not found: {p_}", file=sys.stderr)
            sys.exit(2)
    if out.exists() and not args.overwrite and out != tgt:
        print(f"output exists (pass --overwrite): {out}", file=sys.stderr)
        sys.exit(2)

    tgt_txt = tgt.read_text(encoding="utf-8")
    ex_txt = ex.read_text(encoding="utf-8")

    new_block = extract_clock_configuration(ex_txt, args.name)
    if new_block is None:
        print(f"<clock_configuration name='{args.name}'> not in example", file=sys.stderr)
        sys.exit(2)

    try:
        merged = replace_clock_configuration(tgt_txt, new_block, args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    # Quick XML well-formedness sanity check
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(merged)
    except ET.ParseError as e:
        print(f"XML parse error after splice: {e}", file=sys.stderr)
        sys.exit(2)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(merged, encoding="utf-8", newline="\n")
    print(f"Wrote {out}  ({len(merged)} bytes; new block size = {len(new_block)} B)")
    print("Next steps:")
    print(f"  1) Run s32ct.sanitize on {out} to rewrite any dangling /Mcu/... refs.")
    print(f"  2) Run s32ct.validate tool_name=Clocks on {out}.")
    print(f"  3) Run s32ct.validate (all tools) for Pins/Peripherals regression.")


if __name__ == "__main__":
    main()
