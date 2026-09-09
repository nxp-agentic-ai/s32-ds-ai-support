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

"""Extract <instance ... type_id="DRIVER"> ... </instance> blocks from an RTD
example .mex into one XML fragment per match.

The output fragments are then ready to be passed to `splice.py`.

Usage:
    python extract_examples.py --driver Spi --example <path.mex> --out work/Spi.xml
    python extract_examples.py --driver Pwm --example <path.mex> --out work/Pwm.xml
"""
import argparse
import os
import re
import sys


def extract(driver, example_path):
    """Return the list of <instance ...>...</instance> strings for this type_id."""
    if not os.path.exists(example_path):
        raise FileNotFoundError(example_path)
    txt = open(example_path, encoding="utf-8").read()
    pattern = re.compile(
        rf'<instance\b[^>]*type_id="{re.escape(driver)}"[^>]*>.*?</instance>',
        re.DOTALL,
    )
    return pattern.findall(txt)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--driver", required=True)
    p.add_argument("--example", required=True, help="Path to RTD example .mex")
    p.add_argument("--out", required=True, help="Output XML fragment path (will be created)")
    p.add_argument(
        "--index",
        type=int,
        default=0,
        help="When the example contains multiple instances of this driver, pick one by 0-based index",
    )
    args = p.parse_args()

    matches = extract(args.driver, args.example)
    if not matches:
        print(f"No <instance type_id=\"{args.driver}\"> found in {args.example}")
        sys.exit(2)
    if args.index >= len(matches):
        print(
            f"Requested index {args.index} but only {len(matches)} instance(s) of "
            f"'{args.driver}' in {args.example}"
        )
        sys.exit(2)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    block = matches[args.index]
    open(args.out, "w", encoding="utf-8", newline="\n").write(block)
    print(f"Wrote {args.out}  ({len(block)} bytes)  [instance {args.index} of {len(matches)}]")


if __name__ == "__main__":
    main()
