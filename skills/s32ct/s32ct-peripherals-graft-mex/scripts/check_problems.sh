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
# check_problems.sh - POSIX counterpart of check_problems.bat.
#
# Canonical validation invocation for the peripherals graft workflow.
#
# Usage:
#   ./check_problems.sh <name> <Tool> [<s32ct_install>]
#
#   <name>  : basename used for the .mex (without extension); the script
#             expects $S32CT_PROBE_DIR/<name>.mex to exist already. Copy
#             your work-in-progress .mex there before invoking.
#   <Tool>  : Pins | Clocks | Peripherals | DCD | IVT | eFUSE | GTM
#             | QuadSPI | FFC
#
# Environment:
#   S32CT_INSTALL   install root holding the launcher (or pass as arg 3)
#   S32CT_PROBE_DIR staging dir for the probe .mex and capture files.
#                   Default: ${TMPDIR:-/tmp}/s32ct_probe
#   S32CT_LAUNCHER  launcher binary name. Default: toolsc
#
# Output:
#   stdout -> $S32CT_PROBE_DIR/<name>_<tool>_stdout.txt
#   stderr -> $S32CT_PROBE_DIR/<name>_<tool>_stderr.txt
#
# The exit code the launcher returns is ECHOED but must be IGNORED - it
# returns 0 even on validation errors. Run filter_problems.py on the
# stderr file to get the honest answer.

set -u

usage() {
    echo "Usage: $0 <basename> <Tool> [<s32ct_install>]" >&2
    echo "Example: $0 probe Peripherals" >&2
    exit 2
}

NAME="${1:-}"
TOOL="${2:-}"
S32CT="${3:-${S32CT_INSTALL:-}}"

[ -n "$NAME" ] || usage
[ -n "$TOOL" ] || usage

if [ -z "$S32CT" ]; then
    echo "ERROR: S32CT install path not specified." >&2
    echo "Pass as third argument, or set the S32CT_INSTALL environment variable." >&2
    echo "Example: $0 probe Peripherals /opt/nxp/S32ConfigTools.<release>" >&2
    exit 2
fi

PROBE_DIR="${S32CT_PROBE_DIR:-${TMPDIR:-/tmp}/s32ct_probe}"
LAUNCHER_NAME="${S32CT_LAUNCHER:-toolsc}"
LAUNCHER="$S32CT/$LAUNCHER_NAME"

if [ ! -x "$LAUNCHER" ]; then
    echo "ERROR: launcher not found or not executable: $LAUNCHER" >&2
    echo "Set S32CT_LAUNCHER if your install uses a different binary name." >&2
    exit 3
fi

MEX="$PROBE_DIR/$NAME.mex"
if [ ! -f "$MEX" ]; then
    echo "Cannot find $MEX - copy your .mex there first." >&2
    exit 2
fi

OUT="$PROBE_DIR/${NAME}_${TOOL}_stdout.txt"
ERR="$PROBE_DIR/${NAME}_${TOOL}_stderr.txt"

"$LAUNCHER" -Load "$MEX" -HeadlessTool "$TOOL" -Enable -ShowProblems \
    >"$OUT" 2>"$ERR"
echo "exit=$?  (DO NOT TRUST - filter the stderr file)"
echo "stderr -> $ERR"
exit 0
