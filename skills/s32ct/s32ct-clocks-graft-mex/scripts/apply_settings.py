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

"""Apply `(setting_id, value)` edits to ClockConfig0 of a .mex.

Two modes:

  - `--preset NAME` looks up a hardcoded preset table (mirrored from
    `references/performance-presets.md`). Use this when the user asks for
    a named tier ("max performance", "low power") rather than handcrafted
    settings.

  - `--set ID=VALUE [ID=VALUE ...]` applies arbitrary settings.

Idempotent: running with the same args twice yields the same output. Safe
to combine with `s32ct.sanitize` afterwards.

Usage:
    python apply_settings.py <project.mex> --preset s32k312:max_performance --out new.mex
    python apply_settings.py <project.mex> --set CORE_MFD.scale=160 \\
                                                MC_CGM_MUX_0_DIV0.scale=2 \\
                            --out new.mex
"""
import argparse
import re
import sys
from pathlib import Path


# Subset of the presets documented in references/performance-presets.md.
# Extend as more MCU families are exercised.
PRESETS: dict[str, list[tuple[str, str]]] = {
    "s32k312:max_performance": [
        ("FXOSC_PM", "Crystal_mode"),
        ("CORE_PLL_PD", "Power_up"),
        ("CORE_PLLODIV_0_DE", "Enabled"),
        ("CORE_PLLODIV_1_DE", "Enabled"),
        ("CORE_MFD.scale", "160"),
        ("POSTDIV.scale", "2"),
        ("PHI0.scale", "3"),
        ("PHI1.scale", "3"),
        ("MC_CGM_MUX_0.sel", "PHI0"),
        ("MC_CGM_MUX_0_DIV0.scale", "2"),
        ("MC_CGM_MUX_0_DIV1.scale", "2"),
        ("MC_CGM_MUX_0_DIV2.scale", "4"),
        ("MC_CGM_MUX_0_DIV3.scale", "2"),
        ("MC_CGM_MUX_0_DIV4.scale", "2"),
        ("MODULE_CLOCKS.MC_CGM_AUX3_DIV0.scale", "2"),
    ],
    "s32k312:mid_performance": [
        ("FXOSC_PM", "Crystal_mode"),
        ("CORE_PLL_PD", "Power_up"),
        ("CORE_MFD.scale", "120"),
        ("MC_CGM_MUX_0.sel", "PHI0"),
        ("MC_CGM_MUX_0_DIV0.scale", "1"),
        ("MC_CGM_MUX_0_DIV1.scale", "2"),
        ("MC_CGM_MUX_0_DIV2.scale", "4"),
        ("MODULE_CLOCKS.MC_CGM_AUX3_DIV0.scale", "2"),
    ],
    "s32k312:low_power_run": [
        ("FXOSC_PM", "Disabled"),
        ("CORE_PLL_PD", "Power_down"),
        ("MC_CGM_MUX_0.sel", "FIRC"),
        ("MC_CGM_MUX_0_DIV0.scale", "1"),
        ("MC_CGM_MUX_0_DIV1.scale", "1"),
        ("MC_CGM_MUX_0_DIV2.scale", "2"),
    ],
    "s32k312:safe": [
        ("FXOSC_PM", "Disabled"),
        ("CORE_PLL_PD", "Power_down"),
        ("MC_CGM_MUX_0.sel", "FIRC"),
        ("MC_CGM_MUX_0_DIV0.scale", "2"),
        ("MC_CGM_MUX_0_DIV1.scale", "2"),
        ("MC_CGM_MUX_0_DIV2.scale", "4"),
    ],
}


def apply_setting(txt: str, setting_id: str, value: str) -> tuple[str, bool]:
    """Replace the `value=...` of `<setting id="X" ...>`.

    The element may carry extra attributes (`locked="true"` is common),
    so we match `<setting id="X"` then rewrite just the `value="..."`
    attribute, leaving the rest of the open tag alone.

    Returns (new_text, changed). If the setting doesn't exist, the .mex
    is left untouched (the Clocks tool typically stores only settings
    whose value differs from default - to add a brand-new setting, you'd
    need to splice the element rather than rewrite it).
    """
    pat = re.compile(
        r'(<setting id="' + re.escape(setting_id) + r'"[^>]*?\bvalue=")[^"]*(")'
    )
    new_txt, n = pat.subn(lambda m: m.group(1) + value + m.group(2), txt, count=1)
    return new_txt, bool(n)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mex")
    p.add_argument("--preset", help="Named preset (e.g. s32k312:max_performance)")
    p.add_argument(
        "--set",
        nargs="+",
        default=[],
        help="Explicit ID=VALUE pairs (after --preset, if both used).",
    )
    p.add_argument("--out", required=True, help="Output .mex path")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    src = Path(args.mex)
    if not src.exists():
        print(f"file not found: {src}", file=sys.stderr)
        sys.exit(2)

    out = Path(args.out)
    if out.exists() and not args.overwrite and out != src:
        print(f"output exists (pass --overwrite): {out}", file=sys.stderr)
        sys.exit(2)

    edits: list[tuple[str, str]] = []
    if args.preset:
        if args.preset not in PRESETS:
            print(f"unknown preset {args.preset!r}; choose one of: {sorted(PRESETS)}", file=sys.stderr)
            sys.exit(2)
        edits.extend(PRESETS[args.preset])
    for kv in args.set:
        if "=" not in kv:
            print(f"--set entries must be ID=VALUE: got {kv!r}", file=sys.stderr)
            sys.exit(2)
        k, v = kv.split("=", 1)
        edits.append((k.strip(), v.strip()))

    if not edits:
        print("no edits requested (use --preset and/or --set)", file=sys.stderr)
        sys.exit(2)

    txt = src.read_text(encoding="utf-8-sig")
    applied: list[str] = []
    missing: list[str] = []
    for k, v in edits:
        txt, ok = apply_setting(txt, k, v)
        (applied if ok else missing).append(f"{k}={v}")

    # Validate the edited document before it is written. apply_setting works
    # on raw text, so a malformed value or an unexpected layout could corrupt
    # the .mex; refuse to persist anything that no longer parses as XML.
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(txt)
    except ET.ParseError as exc:
        print(f"XML parse error after applying settings: {exc}", file=sys.stderr)
        print("No file written.", file=sys.stderr)
        sys.exit(2)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(txt, encoding="utf-8", newline="\n")

    print(f"Wrote {out}  ({len(txt)} bytes)")
    print(f"Applied: {len(applied)} edit(s)")
    for s in applied:
        print(f"  {s}")
    if missing:
        print(f"Missing in .mex (setting not present, no change made): {len(missing)}")
        for s in missing:
            print(f"  {s}")


if __name__ == "__main__":
    main()
