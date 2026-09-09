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

"""Locate an RTD example .mex for a given driver.

The lift-and-adapt workflow depends on having an example. This script:

1. Finds the RTD version installed for the requested driver
   (`RTD/<Driver>_<RTD_VER>` folder under
   `<S32DS_INSTALL>/S32DS/software/<PLATFORM_SDK>`).
2. Picks the closest example for the target MCU family, preferring an exact
   MCU match (`S32K312`) then the family default (`S32K344` for S32K3xx).
3. Prints the absolute path of the example `.mex` it would use.

Usage:
    python discover.py --driver Spi --mcu S32K312 [--sdk PlatformSDK_S32K3]
                       [--s32ds C:\\NXP\\S32DS.3.6.6]
                       [--list]
"""
import argparse
import glob
import os
import re
import sys


# Heuristic: when the target MCU has no example of its own, fall back to this
# family representative. Extend as new MCU families come online.
FAMILY_FALLBACK = {
    "S32K312": ["S32K344", "S32K358", "S32K388", "S32K389", "S32K396"],
    "S32K314": ["S32K344", "S32K358"],
    "S32K322": ["S32K344"],
    "S32K324": ["S32K344"],
    # populate as needed:
    "S32G274A": ["S32G274A", "S32G2"],
    "S32M276": ["S32M276", "S32M274"],
}


def find_rtd_dir(s32ds, sdk, driver):
    base = os.path.join(s32ds, "S32DS", "software", sdk, "RTD")
    candidates = glob.glob(os.path.join(base, f"{driver}_TS_*"))
    if not candidates:
        return None
    # Just pick the first; typical install has only one
    return candidates[0]


def find_examples(rtd_dir):
    """Return list of (mcu_token, example_dir, mex_path) for every example."""
    out = []
    examples_root = os.path.join(rtd_dir, "examples", "S32DS")
    if not os.path.isdir(examples_root):
        return out
    for family in os.listdir(examples_root):
        family_dir = os.path.join(examples_root, family)
        if not os.path.isdir(family_dir):
            continue
        for entry in os.listdir(family_dir):
            ex_dir = os.path.join(family_dir, entry)
            if not os.path.isdir(ex_dir):
                continue
            # Each example dir has exactly one .mex
            for mex in glob.glob(os.path.join(ex_dir, "*.mex")):
                # Try to extract the MCU token from the dir name (e.g. Spi_Transfer_S32K344)
                m = re.search(r"_(S32[A-Z0-9]+)$", entry)
                token = m.group(1) if m else family
                out.append((token, entry, mex))
    return out


def _example_simplicity_score(example_dir):
    """Lower score = simpler / cleaner starter. Examples named with extra
    qualifiers (Flexio, Dma, HalfDuplex, BctuIp, RepeatedTransfer, ...) tend to
    pull in cross-references this skill doesn't need; plain "<Driver>_*" or
    "<Driver>_example_*" examples are the best lift targets.
    """
    name = example_dir.lower()
    score = 0
    for bad in ("flexio", "dma", "halfduplex", "bctu", "_ip_", "repeated", "fcm", "lowpower"):
        if bad in name:
            score += 1
    return score


def pick_example(examples, target_mcu):
    """Pick the closest example for the target MCU, preferring the simplest one."""
    if not examples:
        return None

    def best_of(subset):
        subset = list(subset)
        if not subset:
            return None
        subset.sort(key=lambda t: _example_simplicity_score(t[1]))
        return subset[0]

    # 1) exact match
    r = best_of([e for e in examples if e[0] == target_mcu])
    if r:
        return r
    # 2) family fallback
    for fallback in FAMILY_FALLBACK.get(target_mcu, []):
        r = best_of([e for e in examples if e[0] == fallback])
        if r:
            return r
    # 3) anything that looks like the right family
    family_prefix = target_mcu[:4]  # e.g. "S32K"
    r = best_of([e for e in examples if e[0].startswith(family_prefix)])
    if r:
        return r
    # 4) last resort
    return best_of(examples)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--driver", required=True, help="Driver folder name (e.g. Spi, Can_43_FLEXCAN)")
    p.add_argument("--mcu", required=True, help="Target MCU id (e.g. S32K312)")
    p.add_argument("--sdk", default="PlatformSDK_S32K3", help="Platform SDK folder name")
    p.add_argument("--s32ds", default=r"C:\NXP\S32DS.3.6.6", help="S32DS install root")
    p.add_argument("--list", action="store_true", help="List all examples for this driver")
    args = p.parse_args()

    rtd = find_rtd_dir(args.s32ds, args.sdk, args.driver)
    if rtd is None:
        print(f"No RTD folder found for driver '{args.driver}' under {args.s32ds}\\S32DS\\software\\{args.sdk}\\RTD")
        sys.exit(2)

    examples = find_examples(rtd)
    if args.list:
        print(f"All examples for {args.driver} (RTD={os.path.basename(rtd)}):")
        for tok, ed, mex in examples:
            print(f"  [{tok:<10}] {ed}: {mex}")
        return

    pick = pick_example(examples, args.mcu)
    if pick is None:
        print(f"No example .mex found for driver '{args.driver}' under {rtd}")
        sys.exit(2)
    tok, ed, mex = pick
    print(f"Driver:        {args.driver}")
    print(f"RTD folder:    {rtd}")
    print(f"Selected MCU:  {tok}  (target was {args.mcu})")
    print(f"Example dir:   {ed}")
    print(f"Example .mex:  {mex}")


if __name__ == "__main__":
    main()
