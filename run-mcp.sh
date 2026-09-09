#!/usr/bin/env bash
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

# ============================================================
#  run-mcp.sh - Wrapper to run a python -m module with args
#  inside the project's virtual environment.
#
#  Usage:
#      bash run-mcp.sh <module> [args...]
#
#  Examples:
#      bash run-mcp.sh nxp.mcp.gateway configs/gateway.stdio.yaml
#      bash run-mcp.sh nxp.mcp.gateway configs/gateway.http.yaml
# ============================================================

set -euo pipefail

# --- Resolve script directory (works no matter where it's called from) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONUTF8=1

# --- Validate arguments ---
if [ $# -eq 0 ]; then
    echo "[run-mcp] ERROR: missing module name."
    echo "Usage: $(basename "$0") <module> [args...]"
    echo "Example: $(basename "$0") nxp.mcp.gateway configs/gateway.stdio.yaml"
    exit 1
fi

# --- Move into project root ---
cd "$SCRIPT_DIR" || {
    echo "[run-mcp] ERROR: cannot cd to \"$SCRIPT_DIR\""
    exit 1
}

# --- Activate virtual environment (only if it exists) ---
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/.venv/bin/activate"
else
    echo "[run-mcp] INFO: no venv found at \"$SCRIPT_DIR/.venv\", using system Python" >&2
fi

# --- Verify python is available on PATH ---
if ! command -v python >/dev/null 2>&1; then
    echo "[run-mcp] ERROR: 'python' not found on PATH. Install Python or create a .venv at \"$SCRIPT_DIR/.venv\"."
    exit 1
fi

# --- Run python with all passed arguments ---
python -m "$@"
