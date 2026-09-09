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

"""Systematically clean up cross-references in a freshly-spliced .mex so it
can validate against the typical template (which lacks Mcl and has only
McuClockReferencePoint_0).

This is idempotent - re-running it after manual edits is free.

Three sweeps, in order:

  1. Mcu clock-ref redirect
     Every value matching
       /Mcu/Mcu/McuModuleConfiguration/<segment>/<segment2>
     that doesn't already end in McuClockReferencePoint_0 is rewritten to
       /Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/McuClockReferencePoint_0

  2. Mcl-referencing array sweep
     Every <array name="X">...</array> whose body contains "/Mcl/" is replaced
     by a self-closing <array name="X"/>. Nested arrays are handled
     correctly.

  3. Singleton ref blank
     For a configurable list of <setting name="..." value="..."/> fields whose
     value references an absent driver, blank the value (keep the tag).

The set of singleton fields is documented in
`references/cross-reference-map.md`. Extend as new fields surface.

Usage:
    python sanitize.py --mex <path-to-.mex> [--canonical-clockref PATH]
"""
import argparse
import os
import re
import sys

# Make the bundled helper importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from balanced_array import find_all_balanced_arrays  # noqa: E402


SINGLETON_BLANK = [
    # (field name, regex pattern of values to blank)
    ("UartHwChannelRef", r"/Mcl/"),
    # Add more as discovered. Document in cross-reference-map.md.
]


def sanitize(mex_path, canonical_clockref=None):
    """Apply all three sweeps. Returns (txt, stats_dict)."""
    if not os.path.exists(mex_path):
        raise FileNotFoundError(mex_path)
    txt = open(mex_path, encoding="utf-8").read()
    stats = {"mcu_refs_redirected": 0, "mcl_arrays_emptied": 0, "singletons_blanked": 0}

    if canonical_clockref is None:
        canonical_clockref = (
            "/Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/McuClockReferencePoint_0"
        )

    # --- Sweep 1: Mcu clock-ref redirect ---
    def repath(m):
        full = m.group(0)
        if "/McuClockReferencePoint_0" in full:
            return full
        stats["mcu_refs_redirected"] += 1
        return f'value="{canonical_clockref}"'

    txt = re.sub(r'value="/Mcu/Mcu/McuModuleConfiguration/[^"]+"', repath, txt)

    # --- Sweep 2: Mcl-referencing arrays -> self-closed ---
    # We do this by collecting all arrays first, then rewriting end->start so
    # offsets stay valid.
    arrays = list(find_all_balanced_arrays(txt))
    for name, op_start, body_start, body_end, close_end in reversed(arrays):
        if "/Mcl/" in txt[body_start:body_end]:
            txt = txt[:op_start] + f'<array name="{name}"/>' + txt[close_end:]
            stats["mcl_arrays_emptied"] += 1

    # --- Sweep 3: singletons ---
    for field, value_pattern in SINGLETON_BLANK:
        rx = re.compile(
            rf'<setting name="{re.escape(field)}" value="[^"]*?{value_pattern}[^"]*"/>'
        )
        new_txt, n = rx.subn(f'<setting name="{field}" value=""/>', txt)
        stats["singletons_blanked"] += n
        txt = new_txt

    # Sanity check
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(txt)
    except ET.ParseError as e:
        raise RuntimeError(f"Sanitize produced malformed XML: {e}")

    return txt, stats


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mex", required=True, help="Path to .mex (sanitised in-place)")
    p.add_argument(
        "--canonical-clockref",
        help="Override the clock-ref redirect target (default: McuClockReferencePoint_0 under McuClockSettingConfig_0)",
    )
    args = p.parse_args()
    txt, stats = sanitize(args.mex, args.canonical_clockref)
    open(args.mex, "w", encoding="utf-8", newline="\n").write(txt)
    print(f"Sanitised {args.mex}:")
    print(f"  Mcu clock refs redirected: {stats['mcu_refs_redirected']}")
    print(f"  Mcl-referencing arrays emptied: {stats['mcl_arrays_emptied']}")
    print(f"  Singleton refs blanked: {stats['singletons_blanked']}")


if __name__ == "__main__":
    main()
