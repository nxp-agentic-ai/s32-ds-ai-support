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

"""The canonical 4-step stderr filter for `toolsc.exe -ShowProblems`.

This is the *only* honest validation gate: `toolsc.exe` returns exit_code=0
even when its Problems View contains errors. Trust this filter, never the
exit code.

The filter has three stages:

  1. Keep only lines that contain `SEVERE: [TOOL]` or `SEVERE: [Generation`.
  2. Drop the 9 known framework-noise patterns that always appear even on a
     clean .mex (Eclipse / SerDes / expression-evaluator / etc.).
  3. De-duplicate the remainder.

If any line survives, it's a *real* problem and you can match it against
`references/error-decision-tree.md`.

Usage:
    python filter_problems.py --stderr <path-to-captured-stderr.txt>
    # exit 0 if 0 real problems, 1 otherwise. Prints the problems verbatim.
"""
import argparse
import re
import sys


NOISE_PATTERNS = [
    r"Cannot get container for IPath",
    r"No script file found while trying to recompile the codegeneration script for SerDes Config Tool",
    r"Error in expression parsing\. Missing right bracket '\)' .* in expression: \(featureDefined\(`FEATURE_",
    r"Problem occurred during invocation of function derefAsr",
    r"Port_GetNumOfPinConfig",
    r"getTotalNumOfChans",
    r"getTotalNumOfGroups",
    r"getChildById",
    r'\[DATA\] \[Siul2_Port\] Trying to apply item defaults or quick selection on setting with id ".*PortPinPcr"',
]
NOISE_RE = re.compile("|".join(NOISE_PATTERNS))


def filter_stderr(stderr_path):
    """Return (all_lines_count, after_severity_filter, real_problems_unique)."""
    txt = open(stderr_path, encoding="utf-8", errors="replace").read()
    lines = txt.splitlines()

    candidates = [l for l in lines if "SEVERE: [TOOL]" in l or "SEVERE: [Generation" in l]
    real = [l for l in candidates if not NOISE_RE.search(l)]

    # De-dup by message tail (drop the timestamp prefix)
    seen = set()
    uniq = []
    for l in real:
        key = l[l.find("SEVERE:"):] if "SEVERE:" in l else l
        if key not in seen:
            seen.add(key)
            uniq.append(l)
    return len(lines), len(candidates), uniq


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stderr", required=True, help="Path to captured stderr file")
    p.add_argument("--quiet", action="store_true", help="Only print the verdict (PASS/FAIL N)")
    args = p.parse_args()

    n_total, n_sev, real = filter_stderr(args.stderr)
    if not args.quiet:
        print(f"Total stderr lines: {n_total}")
        print(f"After SEVERE:[TOOL]/[Generation] filter: {n_sev}")
        print(f"After framework-noise filter: {len(real)}")
        print()
    if real:
        if not args.quiet:
            print("=== REAL PROBLEMS ===")
        for l in real:
            print(l)
        print(f"FAIL ({len(real)} real problem(s))")
        sys.exit(1)
    else:
        print("PASS (0 real problems after filter)")
        sys.exit(0)


if __name__ == "__main__":
    main()
