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

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from board_config_mcp.dataset_store import BoardDatasetStore
from board_config_mcp.runtime_rules import analyze_semantic_board

DEBUG_OUTPUT_DIR = ROOT / 'workspace' / 'test_crops' / 'S32N79-RDB'


TEST_CASES = [
    {
        "image": ROOT / 'examples' / 'S32N79_AT_landscape_cropped.png',
        "expected": {
            'ID_JMP3X_A': 'ABSENT',
            "ID_SW3": {
                "1": "OFF",
                "2": "OFF",
                "3": "OFF",
                "4": "OFF",
                "5": "ON",
                "6": "OFF",
                "7": "ON",
                "8": "ON",
                "9": "OFF",
                "10": "ON"
            },
        },
        "name": "test_case_1"
    },
    {
        "image": ROOT / 'examples' / 'N79_with_ID_JMP3X_A_2-3.png',
        "expected": {
            'ID_JMP3X_A': 'ABSENT',
            "ID_SW3": {
                "1": "OFF",
                "2": "OFF",
                "3": "OFF",
                "4": "ON",
                "5": "ON",
                "6": "OFF",
                "7": "OFF",
                "8": "ON",
                "9": "OFF",
                "10": "ON"
            },
        },
        "name": "test_case_2"
    },
    {
        "image": ROOT / 'examples' / 'S32N79_ATaran.png',
        "expected": {
            'ID_JMP3X_A': 'ABSENT',
            "ID_SW3": {
                "1": "OFF",
                "2": "OFF",
                "3": "OFF",
                "4": "OFF",
                "5": "ON",
                "6": "OFF",
                "7": "ON",
                "8": "ON",
                "9": "OFF",
                "10": "ON"
            },
        },
        "name": "test_case_3"
    },
    {
        "image": ROOT / 'examples' / 'S32N79_ATaran_90.png',
        "expected": {
            'ID_JMP3X_A': 'ABSENT',
            "ID_SW3": {
                "1": "OFF",
                "2": "OFF",
                "3": "OFF",
                "4": "OFF",
                "5": "ON",
                "6": "OFF",
                "7": "ON",
                "8": "ON",
                "9": "OFF",
                "10": "ON"
            },
        },
        "name": "test_case_4"
    },
    {
        "image": ROOT / 'examples' / 'S32N79_ATaran_180.png',
        "expected": {
            'ID_JMP3X_A': 'ABSENT',
            "ID_SW3": {
                "1": "OFF",
                "2": "OFF",
                "3": "OFF",
                "4": "OFF",
                "5": "ON",
                "6": "OFF",
                "7": "ON",
                "8": "ON",
                "9": "OFF",
                "10": "ON"
            },
        },
        "name": "test_case_5"
    },
    {
        "image": ROOT / 'examples' / 'S32N79_ATaran_270.png',
        "expected": {
            'ID_JMP3X_A': 'ABSENT',
            "ID_SW3": {
                "1": "OFF",
                "2": "OFF",
                "3": "OFF",
                "4": "OFF",
                "5": "ON",
                "6": "OFF",
                "7": "ON",
                "8": "ON",
                "9": "OFF",
                "10": "ON"
            },
        },
        "name": "test_case_6"
    },
    {
        "image": ROOT / 'examples' / 'S32N79_ATaran_S3.4-ON.png',
        "expected": {
            "ID_SW3": {
                "1": "OFF",
                "2": "OFF",
                "3": "OFF",
                "4": "OFF",
                "5": "ON",
                "6": "OFF",
                "7": "ON",
                "8": "ON",
                "9": "OFF",
                "10": "ON"
            },
        },
        "name": "test_case_7"
    },
]


def main() -> int:
    store = BoardDatasetStore(ROOT / 'boards')
    board = store.get_board('S32N79-RDB')
    selected_test = "test_case_7";

    all_results = {}

    for test in TEST_CASES:
        
        # ✅ Skip tests that don't match
        if selected_test and test["name"] != selected_test:
            continue

        print(f"Running {test['name']}...")

        result = analyze_semantic_board(
            board,
            str(test["image"]),
            test["expected"],
            str(DEBUG_OUTPUT_DIR),
            align_to_reference=True
        )

        all_results[test["name"]] = result

    print(json.dumps(all_results, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
