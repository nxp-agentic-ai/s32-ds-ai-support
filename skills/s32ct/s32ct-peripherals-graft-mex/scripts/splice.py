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

"""Splice one or more adapted <instance> blocks into an existing .mex.

This is the reference splicer - it preserves the existing Pins-tool block and
all pre-wired instances, and inserts the new instances just before
</instances> in the Peripherals tool's BOARD_InitPeripherals functional group.

Each input fragment is re-uuid'd before splice (instance-level uuid="..."
attribute), so the validator doesn't see duplicates.

Usage:
    python splice.py --project <existing.mex> --out <new.mex> --instances frag1.xml frag2.xml ...
                     [--description "..."]
                     [--overwrite]

What this script does NOT do:
    Per-driver adaptation (changing hw-channel selectors, renaming
    CanControllerBaudrateConfig per parent, etc.). Either edit the fragment
    files first, or extend this script with a driver-specific `adapt_*`
    function. See `references/per-driver-gotchas.md` for what each driver
    needs.
"""
import argparse
import os
import re
import sys
import uuid


def fresh_uuid():
    return str(uuid.uuid4())


def set_instance_uuid(block):
    """Replace the instance-level uuid="..." with a fresh UUID v4."""
    return re.sub(
        r'(<instance\b[^>]*\buuid=")[^"]+(")',
        lambda m: m.group(1) + fresh_uuid() + m.group(2),
        block,
        count=1,
    )


def splice(project_path, out_path, fragments, description=None, overwrite=False):
    if not os.path.exists(project_path):
        raise FileNotFoundError(project_path)
    if os.path.exists(out_path) and not overwrite and os.path.abspath(out_path) != os.path.abspath(project_path):
        raise FileExistsError(f"{out_path} exists (pass --overwrite to replace)")
    mex = open(project_path, encoding="utf-8").read()

    # Splice point: the last </instances> tag inside the Peripherals tool's
    # BOARD_InitPeripherals functional group. The simplest robust heuristic
    # is "the </instances> that has actual <instance> siblings before it" -
    # for a starter template, this is the only </instances>.
    insert_at = mex.find("</instances>")
    if insert_at < 0:
        raise RuntimeError("Could not find </instances> in target .mex")

    # Indent the new blocks to match siblings; 18 spaces is the convention
    # used by S32CT's pretty-printer.
    indent = "                  "
    patched = mex[:insert_at]
    for frag_path in fragments:
        block = open(frag_path, encoding="utf-8").read()
        block = set_instance_uuid(block)
        patched += "\n" + indent + block.strip() + "\n"
    patched += mex[insert_at:]

    # Regenerate the top-level project UUID for cleanliness
    patched = re.sub(
        r'(<configuration\b[^>]*\buuid=")[^"]+(")',
        lambda m: m.group(1) + fresh_uuid() + m.group(2),
        patched,
        count=1,
    )

    # Optional description rewrite
    if description:
        patched = re.sub(
            r"(<common>.*?<description>).*?(</description>)",
            lambda m: m.group(1) + description + m.group(2),
            patched,
            count=1,
            flags=re.DOTALL,
        )

    open(out_path, "w", encoding="utf-8", newline="\n").write(patched)
    return len(patched), len(patched) - len(mex)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True, help="Existing .mex to extend")
    p.add_argument("--out", required=True, help="Output .mex path")
    p.add_argument(
        "--instances",
        nargs="+",
        required=True,
        help="One or more XML fragment files produced by extract_examples.py",
    )
    p.add_argument("--description", help="Replace the project's <common><description>")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    size, delta = splice(args.project, args.out, args.instances, args.description, args.overwrite)
    print(f"Wrote {args.out}  ({size} bytes, +{delta} vs source)")
    print(f"Spliced {len(args.instances)} <instance> block(s).")

    # Quick XML well-formedness check
    try:
        import xml.etree.ElementTree as ET
        ET.parse(args.out)
        print("XML well-formed.")
    except Exception as e:
        print(f"WARNING: XML parse error after splice: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
