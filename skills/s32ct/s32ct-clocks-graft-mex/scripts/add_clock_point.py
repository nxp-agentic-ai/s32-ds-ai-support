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

"""Add a new `McuClockReferencePoint_*` to the Mcu instance.

Counterpart of the "max-performance" workflow: tuning the clock tree
without giving drivers per-domain reference points means generated C
still computes baud rates against `McuClockReferencePoint_0` (typically
CORE_CLK). Add named points like `LPUART_CLK`, `LPSPI_CLK`, `CAN_PE_CLK`
so drivers can be repointed at the correct semantic clock.

The Mcu instance's `McuClockReferencePoint` array typically lives at:

  <instance type_id="Mcu">
    <config_set name="McuModuleConfiguration">
      <struct name="McuClockSettingConfig" type_id="..." mode="...">
        ... (probably "_0", the only one)
        <array name="McuClockReferencePoint">
          <struct name="0">
            <setting name="Name" value="McuClockReferencePoint_0"/>
            <setting name="McuClockFrequencySelect" value="CORE_CLK"/>
          </struct>
          <!-- new ones get appended here -->
        </array>
      </struct>
    </config_set>
  </instance>

Usage:
    python add_clock_point.py <mex> --name LPUART_CLK --select AIPS_SLOW_CLK --out new.mex
    python add_clock_point.py <mex> --name CAN_PE_CLK --select AIPS_PLAT_CLK \\
        --name LPSPI_CLK  --select AIPS_PLAT_CLK --out new.mex
"""
import argparse
import re
import sys
from pathlib import Path


def add_points(txt: str, points: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Append `(name, select)` pairs to the McuClockReferencePoint array.

    Returns (new_text, list_of_skipped_due_to_duplicate_name).
    """
    skipped: list[str] = []

    # Locate the McuClockReferencePoint array
    open_tag = '<array name="McuClockReferencePoint">'
    op = txt.find(open_tag)
    if op < 0:
        raise RuntimeError("Could not find <array name=\"McuClockReferencePoint\"> in this .mex")

    bs = op + len(open_tag)
    # Walk to matching </array> with depth accounting (handles nested arrays)
    depth = 1
    end = None
    token_re = re.compile(r"<array\b[^>]*?(/?)>|</array>")
    for m in token_re.finditer(txt, bs):
        tok = m.group(0)
        if tok == "</array>":
            depth -= 1
            if depth == 0:
                end = m.start()
                break
        elif tok.endswith("/>"):
            continue
        else:
            depth += 1
    if end is None:
        raise RuntimeError("Could not find matching </array>")

    body = txt[bs:end]
    # Find existing struct indices to avoid collisions
    existing_idx = [int(m.group(1)) for m in re.finditer(r'<struct name="(\d+)">', body)]
    existing_names = set(
        re.findall(r'<setting name="Name" value="(McuClockReferencePoint_\d+|[A-Z_]+_CLK)"/>', body)
    )
    # Also detect named clock points (the user may have already added some)
    existing_arbitrary = set(
        re.findall(r'<setting name="Name" value="([^"]+)"/>', body)
    )

    next_idx = (max(existing_idx) + 1) if existing_idx else 0
    indent = "                                          "  # matches sibling indent

    additions = []
    for name, select in points:
        if name in existing_arbitrary or name in existing_names:
            skipped.append(name)
            continue
        block = (
            f"\n{indent}<struct name=\"{next_idx}\">\n"
            f"{indent}   <setting name=\"Name\" value=\"{name}\"/>\n"
            f"{indent}   <setting name=\"McuClockFrequencySelect\" value=\"{select}\"/>\n"
            f"{indent}</struct>"
        )
        additions.append(block)
        next_idx += 1

    new_body = body.rstrip("\n") + "\n" + "\n".join(additions) + "\n" + indent[:-3]
    new_txt = txt[:bs] + new_body + txt[end:]
    return new_txt, skipped


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mex")
    p.add_argument("--name", action="append", required=True, help="Clock point name (repeatable)")
    p.add_argument("--select", action="append", required=True, help="Frequency-select clock-output id (paired with --name)")
    p.add_argument("--out", required=True)
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    if len(args.name) != len(args.select):
        print("each --name needs a paired --select (same count)", file=sys.stderr)
        sys.exit(2)

    src = Path(args.mex)
    if not src.exists():
        print(f"file not found: {src}", file=sys.stderr)
        sys.exit(2)
    out = Path(args.out)
    if out.exists() and not args.overwrite and out != src:
        print(f"output exists (pass --overwrite): {out}", file=sys.stderr)
        sys.exit(2)

    txt = src.read_text(encoding="utf-8")
    pairs = list(zip(args.name, args.select))
    new_txt, skipped = add_points(txt, pairs)

    # XML well-formedness sanity check
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(new_txt)
    except ET.ParseError as e:
        print(f"XML parse error after edit: {e}", file=sys.stderr)
        sys.exit(2)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(new_txt, encoding="utf-8", newline="\n")
    print(f"Wrote {out}  ({len(new_txt)} bytes, +{len(new_txt) - len(txt)} added)")
    print(f"Added {len(pairs) - len(skipped)} clock point(s).")
    if skipped:
        print(f"Skipped {len(skipped)} (already present): {skipped}")
    print("Now re-point driver *ClockRef settings at the new entries, then re-validate.")


if __name__ == "__main__":
    main()
