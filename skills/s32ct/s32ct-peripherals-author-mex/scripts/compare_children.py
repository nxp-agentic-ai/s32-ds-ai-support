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

"""For each top-level child (struct/array) of the <config_set> in the target
.mex vs a reference .mex, list which ones exist in the reference but are
MISSING in the target. Those auto-create empty
<struct name='0'><setting Name=""></struct> entries that trip the validator.

This script only reads the .mex files; it never modifies them.

Usage:
    python compare_children.py --mex <project.mex>
                               --ref-can <reference_can.mex>
                               --ref-adc <reference_adc.mex>
"""
import argparse
import re
import sys
from pathlib import Path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Compare top-level config_set children against reference .mex "
            "files. Read-only: no file is modified."
        ),
    )
    parser.add_argument(
        "--mex",
        required=True,
        type=Path,
        help="Path to the target .mex project file to inspect.",
    )
    parser.add_argument(
        "--ref-can",
        required=True,
        type=Path,
        help="Path to the reference .mex used to compare the Can instance.",
    )
    parser.add_argument(
        "--ref-adc",
        required=True,
        type=Path,
        help="Path to the reference .mex used to compare the Adc instance.",
    )
    return parser.parse_args(argv)


def read_mex(path, label):
    """Read a .mex file, exiting with a clear message if it is missing."""
    if not path.is_file():
        print(f"error: {label} file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text(encoding="utf-8-sig")


def get_config_set_top_children(text, instance_name, cs_name):
    """Return list of top-level <struct/array name="X"> directly under the
    <config_set name=cs_name> of the given instance."""
    # locate instance
    m = re.search(rf'<instance name="{instance_name}"[^>]*>(.*?)</instance>', text, re.DOTALL)
    if not m:
        return []
    body = m.group(1)
    # locate config_set
    m2 = re.search(rf'<config_set name="{cs_name}">(.*?)</config_set>', body, re.DOTALL)
    if not m2:
        return []
    cs = m2.group(1)
    # find top-level <struct/array name=> at depth 1 only:
    children = []
    depth = 0
    pos = 0
    for tag in re.finditer(r'<(/?)(struct|array)(?: name="([^"]+)")?[^/>]*?(/?)>', cs):
        slash, kind, nm, self_close = tag.groups()
        if slash:
            depth -= 1
        else:
            if depth == 0 and nm:
                children.append((kind, nm))
            if not self_close:
                depth += 1
    return children

def main(argv=None):
    args = parse_args(argv)

    target = read_mex(args.mex, "--mex")
    ref_can = read_mex(args.ref_can, "--ref-can")
    ref_adc = read_mex(args.ref_adc, "--ref-adc")

    for inst, cs, ref_text in [
            ("Can_43_FLEXCAN", "Can", ref_can),
            ("Adc", "Adc", ref_adc)]:
        mine = get_config_set_top_children(target, inst, cs)
        ref = get_config_set_top_children(ref_text, inst, cs)
        mine_names = {n for k, n in mine}
        ref_names = {n for k, n in ref}
        missing_in_mine = ref_names - mine_names
        extra_in_mine = mine_names - ref_names
        print(f"\n=== {inst} / config_set '{cs}' ===")
        print(f"  IN TARGET:    {sorted(mine_names)}")
        print(f"  IN REFERENCE: {sorted(ref_names)}")
        print(f"  MISSING:      {sorted(missing_in_mine)}")
        print(f"  EXTRA:        {sorted(extra_in_mine)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
