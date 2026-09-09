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

"""List existing <instance> blocks and McuClockReferencePoint_* names in a .mex.

Run as step 1 of the workflow so you know what's already present (which drivers
to extend vs. replace) and what clock points the redirect step in
`sanitize.py` will land on.

Usage:
    python inventory.py <path-to-.mex>
"""
import re
import sys


def inventory(mex_path):
    txt = open(mex_path, encoding="utf-8").read()

    print("=== <instance> blocks ===")
    for m in re.finditer(
        r'<instance\s+name="([^"]+)"[^>]*type="([^"]+)"[^>]*type_id="([^"]+)"[^>]*mode="([^"]+)"',
        txt,
    ):
        name, ty, tid, mode = m.groups()
        # Find the end of this instance to measure its size
        end = txt.find("</instance>", m.start())
        size = end - m.start() if end > 0 else -1
        print(
            f"  name={name:<30} type={ty:<30} type_id={tid:<30} mode={mode:<10}  ({size} bytes)"
        )

    print("\n=== McuClockReferencePoint_* names ===")
    for m in re.finditer(r'<setting name="Name" value="(McuClockReferencePoint_\d+)"/>', txt):
        print(f"  {m.group(1)}")

    print("\n=== Functional groups ===")
    for m in re.finditer(r'<functional_group name="([^"]+)"', txt):
        print(f"  {m.group(1)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    inventory(sys.argv[1])
