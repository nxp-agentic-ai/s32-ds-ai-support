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

"""Replace the minimal peripheral <instance> blocks and their preceding
comment banner in a .mex project with a richer peripherals block.

The target .mex is modified IN PLACE. A timestamped backup is written
next to it before any change, the spliced result is validated as XML
before being committed, and the computed removal span is bounded to
guard against a runaway delete when the marker comments are ambiguous.

Usage:
    python splice_peripherals.py --mex <project.mex> --block <peripherals_block.xml>
                                 [--dry-run] [--force] [--no-backup]
                                 [--max-removal-bytes N]

Exit codes:
    0 success (or successful --dry-run)
    1 usage / input error
    2 marker resolution failed or removal span rejected
    3 resulting document is not well-formed XML
"""

import argparse
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# Comment banners that mark the start of the peripherals block. Both the
# original minimal banner and the richer per-controller banner are matched
# so the script is idempotent across repeated grafts.
BLOCK_MARKERS = (
    "<!-- Peripheral driver instances matching the Pins-tool routings",
    "<!-- Per-controller driver configuration",
)
BANNER_PREFIX = "<!-- ===="
INSTANCES_CLOSE = "</instances>"

# Safety bound on how much of the .mex a single splice may remove. The
# peripherals block of a fully populated project is a few tens of KB; a
# span far beyond that means the end marker was resolved incorrectly.
DEFAULT_MAX_REMOVAL_BYTES = 200_000


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Splice a richer peripherals block into a .mex project.",
    )
    parser.add_argument(
        "--mex",
        required=True,
        type=Path,
        help="Path to the target .mex project file (modified in place).",
    )
    parser.add_argument(
        "--block",
        required=True,
        type=Path,
        help="Path to the replacement peripherals block XML fragment.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the region that would be replaced and exit without writing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the interactive confirmation prompt before overwriting.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not write a .bak copy. Not recommended.",
    )
    parser.add_argument(
        "--max-removal-bytes",
        type=int,
        default=DEFAULT_MAX_REMOVAL_BYTES,
        help=(
            "Abort if the computed removal span exceeds this many bytes "
            "(default: %(default)s)."
        ),
    )
    return parser.parse_args(argv)


def fail(message, code):
    """Print an error to stderr and exit with the given code."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def locate_block(content):
    """Return the (start, end) character span of the peripherals block.

    start is the offset of the opening banner comment line; end is the
    offset of the line on which the closing </instances> tag appears.
    """
    hits = [content.find(marker) for marker in BLOCK_MARKERS]
    hits = [offset for offset in hits if offset > 0]
    if not hits:
        fail(
            "could not find any peripherals-block marker comment; "
            "the .mex layout is not recognised",
            2,
        )
    marker_start = min(hits)

    # Step back to the opening banner line of that comment block, then snap
    # to the start of that line so the leading indentation is replaced too.
    banner_start = content.rfind(BANNER_PREFIX, 0, marker_start)
    if banner_start < 0:
        fail("could not find the leading banner comment line", 2)
    banner_start = content.rfind("\n", 0, banner_start) + 1

    # The closing </instances> tag that terminates the block.
    close_idx = content.find(INSTANCES_CLOSE, marker_start)
    if close_idx < 0:
        fail(f"could not find {INSTANCES_CLOSE} after the marker", 2)

    # Step back to the start of that line so the original indentation of
    # </instances> is preserved in the suffix.
    line_start = content.rfind("\n", 0, close_idx) + 1
    if line_start <= banner_start:
        fail(
            "resolved an inverted removal span; the marker comments are ambiguous",
            2,
        )
    return banner_start, line_start


def check_span(content, start, end, max_bytes):
    """Validate that the removal span looks like a peripherals block."""
    removed = content[start:end]
    size = len(removed)
    if size > max_bytes:
        fail(
            f"refusing to remove {size} bytes (limit {max_bytes}). The end "
            f"marker was probably resolved incorrectly. Re-run with "
            f"--dry-run to inspect, or raise --max-removal-bytes if this "
            f"span is genuinely expected.",
            2,
        )
    # The span must consist of the banner plus <instance> blocks only. A
    # stray <pins>/<clocks> section means we captured too much.
    for foreign in ("<pins", "<clocks", "<periphs_profile", "</instances>"):
        if foreign in removed:
            fail(
                f"removal span unexpectedly contains {foreign!r}; aborting to "
                f"avoid destroying unrelated configuration. Use --dry-run to inspect.",
                2,
            )
    return removed


def validate_xml(text):
    """Return None if text is well-formed XML, else the parse error."""
    try:
        ET.fromstring(text)
    except ET.ParseError as exc:
        return exc
    return None


def main(argv=None):
    args = parse_args(argv)

    if not args.mex.is_file():
        fail(f"--mex file not found: {args.mex}", 1)
    if not args.block.is_file():
        fail(f"--block file not found: {args.block}", 1)

    # utf-8-sig transparently strips a leading BOM if the editor that
    # produced the file added one; a stray BOM mid-document would break
    # the XML parse.
    content = args.mex.read_text(encoding="utf-8-sig")
    new_block = args.block.read_text(encoding="utf-8-sig")

    start, end = locate_block(content)
    removed = check_span(content, start, end, args.max_removal_bytes)

    replacement = new_block.rstrip() + "\n"
    new_content = content[:start] + replacement + content[end:]

    print(f"Target      : {args.mex}")
    print(f"Replacement : {args.block}")
    print(f"Removing    : {len(removed)} bytes at offset {start}-{end}")
    print(f"Inserting   : {len(replacement)} bytes")
    print(f"Result size : {len(new_content)} bytes (was {len(content)})")

    # Validate before committing anything to disk.
    parse_error = validate_xml(new_content)
    if parse_error is not None:
        fail(f"spliced result is not well-formed XML: {parse_error}", 3)
    print("XML check   : result parses cleanly")

    if args.dry_run:
        print("\n--- first 40 lines of the region that would be removed ---")
        for line in removed.splitlines()[:40]:
            print(f"  - {line}")
        print("\nDry run: no changes written.")
        return 0

    if not args.force:
        print(
            f"\nWARNING: {args.mex.name} will be modified in place and the "
            f"{len(removed)}-byte region above will be replaced."
        )
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted at user request; no changes written.")
            return 0

    if not args.no_backup:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = args.mex.with_suffix(args.mex.suffix + f".{stamp}.bak")
        shutil.copy2(args.mex, backup)
        print(f"Backup      : {backup}")

    args.mex.write_text(new_content, encoding="utf-8")
    print(f"Wrote       : {args.mex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
