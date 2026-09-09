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

"""Loader for S32Trace Trace-view CSV exports.

Column schema (as emitted by S32Trace / S32DS):
  Index(n), Source(t), Type(t), Left-hand key(t), Right-hand key(t),
  Description(lt), Address(nh), Destination(nh), Timestamp(n),

Two row shapes exist:
  - Parent (event) row: non-empty Index, Source, Type, Timestamp.
  - Detail (continuation) row: Index/Source/Type/Timestamp blank; only
    Description populated.  Detail rows belong to the preceding parent row.

Detail rows whose Description starts with '0x' are parsed as disassembly:
  "0x321008ca mrc p15, #0, r2, c0, c0, #5"
  -> instr_pc = 0x321008ca, instr_text = "mrc p15, #0, r2, c0, c0, #5"
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Column aliases - map S32Trace header name suffixes to semantic names.
# The type annotation suffix in parentheses (n, t, lt, nh) is stripped.
# ---------------------------------------------------------------------------
_ALIAS_MAP: dict[str, str] = {
    "index": "index",
    "source": "core",
    "type": "event_type",
    "left-hand key": "lhk",
    "right-hand key": "rhk",
    "description": "description",
    "address": "address",
    "destination": "destination",
    "timestamp": "timestamp",
}

_PC_DETAIL_RE = re.compile(r"^(0x[0-9a-fA-F]+)\s+(.*)")


def _strip_type_suffix(name: str) -> str:
    """Remove the '(n)', '(t)', '(lt)', '(nh)' suffix that S32Trace appends."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name.strip()).strip().lower()


def _build_column_map(raw_headers: list[str]) -> dict[str, str]:
    """Return mapping {original_col_name -> semantic_name} for recognized columns."""
    result: dict[str, str] = {}
    for raw in raw_headers:
        stripped = _strip_type_suffix(raw)
        semantic = _ALIAS_MAP.get(stripped)
        if semantic:
            result[raw] = semantic
    return result


def load_trace_csv(csv_path: str | Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Load a Trace-view CSV and return (parent_df, details_list).

    ``parent_df``
        One row per parent event with semantic column names plus derived columns:
        - ``address_int`` (int | None): ``Address`` parsed as integer.
        - ``destination_int`` (int | None): ``Destination`` parsed as integer.
        - ``timestamp_int`` (int | None): ``Timestamp`` parsed as integer.
        - ``detail_count`` (int): number of detail rows attached.

    ``details_list``
        Parallel list aligned with ``parent_df.index``.  Each entry is a list
        of dicts ``{description, instr_pc (int|None), instr_text (str|None)}``.

    Raises
    ------
    ValueError
        If the file cannot be parsed as a valid Trace-view CSV (missing
        mandatory columns).
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # Read raw lines with csv module to separate parents from details.
    raw_rows: list[list[str]] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            raw_rows.append(row)

    if not raw_rows:
        raise ValueError("CSV is empty.")

    raw_headers = raw_rows[0]
    col_map = _build_column_map(raw_headers)

    # Require at minimum Index and Description.
    semantic_to_raw: dict[str, str] = {v: k for k, v in col_map.items()}
    if "index" not in semantic_to_raw or "description" not in semantic_to_raw:
        raise ValueError(
            "CSV does not appear to be a Trace-view export: "
            "missing 'Index' and/or 'Description' columns. "
            f"Found headers: {raw_headers}"
        )

    # Map header name to column position.
    pos: dict[str, int] = {h: i for i, h in enumerate(raw_headers)}
    n_cols = len(raw_headers)

    def _get(row: list[str], col_raw: str) -> str:
        idx = pos.get(col_raw, -1)
        if idx < 0 or idx >= len(row):
            return ""
        return row[idx].strip()

    # Group into parent + detail lists.
    parent_records: list[dict[str, Any]] = []
    details_list: list[list[dict[str, Any]]] = []
    current_details: list[dict[str, Any]] = []

    for row in raw_rows[1:]:
        # Pad short rows.
        if len(row) < n_cols:
            row = row + [""] * (n_cols - len(row))

        index_val = _get(row, semantic_to_raw.get("index", "Index(n)"))
        if index_val:
            # Save previous details group.
            if parent_records:
                details_list.append(current_details)
            current_details = []

            # Build parent record.
            record: dict[str, Any] = {}
            for raw_col, sem in col_map.items():
                record[sem] = _get(row, raw_col)

            # Derived typed columns.
            record["address_int"] = _parse_hex_or_int(record.get("address", ""))
            record["destination_int"] = _parse_hex_or_int(record.get("destination", ""))
            record["timestamp_int"] = _parse_int(record.get("timestamp", ""))
            parent_records.append(record)
        else:
            # Detail row - only Description matters.
            desc = _get(row, semantic_to_raw.get("description", "Description(lt)"))
            if not desc:
                continue
            detail: dict[str, Any] = {"description": desc, "instr_pc": None, "instr_text": None}
            m = _PC_DETAIL_RE.match(desc)
            if m:
                detail["instr_pc"] = int(m.group(1), 16)
                detail["instr_text"] = m.group(2).strip()
            current_details.append(detail)

    # Flush last group.
    if parent_records:
        details_list.append(current_details)

    if not parent_records:
        raise ValueError("CSV contains no parent (event) rows.")

    parent_df = pd.DataFrame(parent_records)
    parent_df["detail_count"] = [len(d) for d in details_list]

    for _col in ("address_int", "destination_int", "timestamp_int"):
        if _col in parent_df.columns:
            parent_df[_col] = parent_df[_col].astype("Int64")

    return parent_df, details_list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_hex_or_int(value: str) -> int | None:
    """Parse '0x321008ca' or '12345' or empty string."""
    value = value.strip()
    if not value:
        return None
    try:
        if value.startswith("0x") or value.startswith("0X"):
            return int(value, 16)
        return int(value)
    except ValueError:
        return None


def _parse_int(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
