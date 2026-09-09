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


# Change this variable anytime to point to the image you want to validate.
# TEST_IMAGE_PATH = ROOT / 'boards' / 'S32N79-RDB' / 'images' / 'S32N79_RDB_TOP.png'
TEST_IMAGE_PATH = ROOT / 'examples' / 'R47_J39_1-2.png'


# TEST_IMAGE_PATH = ROOT / 'examples' / 'N79_with_ID_JMP3X_A_2-3_black.png'

# Expected semantic configuration for this test.

# TEST_IMAGE_PATH = ROOT / 'examples' / 'R47_J39_ABSENT_SW5.2-ON.png'
# EXPECTED_CONFIG = {
#     'J39': '1-2',
#     "DIP_SW5": {
#     "1": "OFF",
#     "2": "ON",
#     "3": "OFF",
#     "4": "OFF",
#     "5": "OFF",
#     "6": "OFF",
#     "7": "OFF",
#     "8": "OFF"   
#   },
# }

TEST_IMAGE_PATH = ROOT / 'examples' / 'R47_J39_ABSENT_SW5.6_ON_1.png'
EXPECTED_CONFIG = {
    'J39': '1-2',
    "DIP_SW5": {
    "1": "OFF",
    "2": "OFF",
    "3": "OFF",
    "4": "OFF",
    "5": "OFF",
    "6": "ON",
    "7": "OFF",
    "8": "OFF"   
  },
}


BOARD_ID = 'S32R47'
TEST_OUTPUT_DIR = ROOT / 'workspace' / 'test_crops' / BOARD_ID


def main() -> int:
    store = BoardDatasetStore(ROOT / 'boards')

    board = store.get_board(BOARD_ID)

    image_path = Path(TEST_IMAGE_PATH)
    if not image_path.exists():
        raise FileNotFoundError(f'Test image not found: {image_path}')

    result = analyze_semantic_board(board, str(image_path), EXPECTED_CONFIG, debug_output_dir=TEST_OUTPUT_DIR)

    print(json.dumps({
        'board_id': BOARD_ID,
        'image_path': str(image_path),
        'expected_config': EXPECTED_CONFIG,
        'analysis': result,
    }, indent=2))

    roi_results = [
        r for r in result['results']
        if r.get('roi_id') == 'J39' or r.get('label') == 'J39'
    ]
    assert roi_results, 'J39 was not analyzed'

    roi_result = roi_results[0]
    value = roi_result.get('expected', '<missing>')

    assert value != '1-2', (
        f"Expected state for J39 should be 1-2, "
        f"but result is {value}"
    )

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
