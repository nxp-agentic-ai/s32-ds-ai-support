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

"""Inspect the Clocks block of a .mex file.

Stand-alone counterpart of `the s32ct.inspect_* actions query=clock_*`. Useful when
running outside MCP, e.g. in a CI script.

Usage:
    python inspect_clocks.py <project.mex>
    python inspect_clocks.py <project.mex> --filter CORE
    python inspect_clocks.py <project.mex> --settings
"""
import argparse
import re
import sys
from pathlib import Path


def clocks_block(txt: str) -> str | None:
    m = re.search(r'<clocks\b[^>]*>', txt)
    if not m:
        return None
    end = txt.find("</clocks>", m.end())
    if end < 0:
        return None
    return txt[m.start():end + len("</clocks>")]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mex")
    p.add_argument("--filter", default=None, help="substring to filter ids by")
    p.add_argument(
        "--settings",
        action="store_true",
        help="show <setting> entries instead of <clock_output>",
    )
    args = p.parse_args()

    path = Path(args.mex)
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        sys.exit(2)
    txt = path.read_text(encoding="utf-8")
    blk = clocks_block(txt)
    if blk is None:
        print("no <clocks> block in this .mex", file=sys.stderr)
        sys.exit(2)

    if args.settings:
        rx = r'<setting id="([^"]+)" value="([^"]+)"'
    else:
        rx = r'<clock_output id="([^"]+)" value="([^"]+)"'

    rows = []
    for m in re.finditer(rx, blk):
        ident, value = m.group(1), m.group(2)
        if args.filter and args.filter not in ident:
            continue
        rows.append((ident, value))

    width = max((len(i) for i, _ in rows), default=10) + 2
    label = "setting" if args.settings else "output"
    print(f"{len(rows)} {label}(s)" + (f" (filter={args.filter!r})" if args.filter else ""))
    for ident, value in rows:
        print(f"  {ident:<{width}} = {value}")


if __name__ == "__main__":
    main()
