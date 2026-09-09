#!/usr/bin/env sh
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
#
# ============================================================================
# check_problems.sh - POSIX counterpart of check_problems.bat.
# ============================================================================
# Why this script exists:
#   The launcher always exits 0 even when the Problems View has errors.
#   Real errors appear on STDERR as `SEVERE: [TOOL]` and `SEVERE: [Generation`
#   lines emitted by the Java validation logger. The MCP wrapper truncates
#   stderr at ~3 KB so you cannot see them through the wrapper alone.
#
#   This script:
#     1. Copies the .mex to a scratch staging path.
#     2. Runs the launcher with explicit stderr -> file.
#     3. Greps the captured stderr for real [TOOL]/[Generation lines.
#
# Usage:
#   ./check_problems.sh <abs path to .mex> [ToolName]
#       ToolName = Pins | Clocks | Peripherals | DCD | IVT | eFUSE | GTM
#                  | QuadSPI | FFC     (default: Peripherals)
#
# Environment:
#   S32CT_EXE    full path to the launcher binary. Required.
#                e.g. /opt/nxp/S32ConfigTools.2025.R1.9/B260206/toolsc
#   PROBE_DIR    capture directory. Default: ${TMPDIR:-/tmp}/s32ct_probe_out
#   PROBE_MEX    staged .mex path.  Default: $PROBE_DIR/probe.mex
#
# Pass = exit code 0 AND filtered output is empty.
# Fail = any line printed under "Real Problems-view lines" below.
# ============================================================================

set -u

INPUT_MEX="${1:-}"
TOOL="${2:-Peripherals}"

S32CT_EXE="${S32CT_EXE:-}"
PROBE_DIR="${PROBE_DIR:-${TMPDIR:-/tmp}/s32ct_probe_out}"
PROBE_MEX="${PROBE_MEX:-$PROBE_DIR/probe.mex}"

if [ -z "$INPUT_MEX" ]; then
    echo "Usage: $0 <abs path to .mex> [ToolName]" >&2
    exit 2
fi

if [ -z "$S32CT_EXE" ] || [ ! -x "$S32CT_EXE" ]; then
    echo "ERROR: S32CT_EXE not set or not executable: ${S32CT_EXE:-<unset>}" >&2
    echo "Set the environment variable S32CT_EXE before invoking this script." >&2
    exit 3
fi

if [ ! -f "$INPUT_MEX" ]; then
    echo "ERROR: input .mex not found: $INPUT_MEX" >&2
    exit 2
fi

mkdir -p "$PROBE_DIR" || exit 3

# 1. Stage the .mex in the scratch directory.
# NOTE: this overwrites $PROBE_MEX without prompting. The probe location is
# a scratch staging area, not a project file - disclose the destination so
# the caller can see what is being replaced.
echo "Staging \"$INPUT_MEX\""
echo "     -> \"$PROBE_MEX\" (existing file at this path is overwritten)"
if ! cp -f "$INPUT_MEX" "$PROBE_MEX"; then
    echo "ERROR: failed to copy \"$INPUT_MEX\" to \"$PROBE_MEX\"" >&2
    exit 4
fi

# 2. Run the tool, redirecting stdout/stderr to files.
"$S32CT_EXE" -Load "$PROBE_MEX" -HeadlessTool "$TOOL" -Enable -ShowProblems \
    >"$PROBE_DIR/out.txt" 2>"$PROBE_DIR/err.txt"
EC=$?

echo "--- exit_code=$EC"
echo "--- stdout bytes:"
wc -c <"$PROBE_DIR/out.txt"
echo "--- stderr bytes:"
wc -c <"$PROBE_DIR/err.txt"

# 3. Grep stderr for real Problems-view lines. The filter excludes generic
#    framework chatter that appears on every clean run.
echo "--- Real Problems-view lines (filtered):"
grep -e 'SEVERE: \[TOOL\]' -e 'SEVERE: \[Generation' "$PROBE_DIR/err.txt" 2>/dev/null \
    | grep -v 'No script file found while trying to recompile the codegeneration script for SerDes Config Tool' \
    >"$PROBE_DIR/real_problems.txt"

if [ -s "$PROBE_DIR/real_problems.txt" ]; then
    cat "$PROBE_DIR/real_problems.txt"
    echo "--- FAIL: real problems above ---"
    exit 1
fi

echo "--- (none)"
echo "--- PASS: 0 real problems after filtering ---"
exit 0
