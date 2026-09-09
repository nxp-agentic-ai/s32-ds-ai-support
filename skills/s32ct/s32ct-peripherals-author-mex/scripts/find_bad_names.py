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

"""Find <setting name='Name' value='X'/> entries where X is NOT a valid C
identifier, scoped to selected <instance> blocks of a .mex project.

This script only reads the .mex; it never modifies it.

Usage:
    python find_bad_names.py --mex <project.mex> [--instance NAME ...] [--limit N]
"""
import argparse
import re
import sys
from pathlib import Path

DEFAULT_INSTANCES = ("Can_43_FLEXCAN", "Adc")

C_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Report Name settings that are not valid C identifiers. "
            "Read-only: the .mex is never modified."
        ),
    )
    parser.add_argument(
        "--mex",
        required=True,
        type=Path,
        help="Path to the .mex project file to inspect.",
    )
    parser.add_argument(
        "--instance",
        action="append",
        dest="instances",
        metavar="NAME",
        help=(
            "Instance name to scan. Repeatable. "
            f"Defaults to: {', '.join(DEFAULT_INSTANCES)}"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Maximum number of offending entries to print per instance.",
    )
    return parser.parse_args(argv)


def find_block(text, instance_name):
    """Return (body, start_line) for an instance, or (None, None)."""
    pattern = rf'<instance name="{re.escape(instance_name)}".*?</instance>'
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None, None
    start_line = text[: match.start()].count("\n") + 1
    return match.group(0), start_line


def main(argv=None):
    args = parse_args(argv)

    if not args.mex.is_file():
        print(f"error: --mex file not found: {args.mex}", file=sys.stderr)
        return 1

    text = args.mex.read_text(encoding="utf-8-sig")
    instances = args.instances or list(DEFAULT_INSTANCES)

    total_bad = 0
    for instance_name in instances:
        body, start_line = find_block(text, instance_name)
        if not body:
            print(f"!! {instance_name} not found")
            continue
        print(f"\n=== {instance_name} (instance starts ~line {start_line}) ===")
        bad = []
        for offset, line in enumerate(body.splitlines(), start=start_line):
            match = re.search(r'<setting name="Name" value="([^"]*)"', line)
            if match:
                value = match.group(1)
                if not C_IDENTIFIER.match(value):
                    bad.append((offset, value, line.strip()))
        total_bad += len(bad)
        print(f"  total bad Name values: {len(bad)}")
        for line_no, value, raw in bad[: args.limit]:
            print(f"  line {line_no}: value={value!r}")
            print(f"    {raw}")

    # Non-zero exit when problems were found so this can gate a workflow.
    return 2 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
