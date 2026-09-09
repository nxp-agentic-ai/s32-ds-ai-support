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
from board_config_mcp.vision.sample_data import generate_sample_board_assets


def main() -> int:
    assets = generate_sample_board_assets(ROOT / 'examples')
    store = BoardDatasetStore(ROOT / 'boards')
    board_id = 'SEMANTIC_SAMPLE'
    store.create_board(board_id, 'Semantic Sample', str(assets['board_image']))
    store.add_roi(board_id, {
        'roi_id': 'JP3', 'label': 'JP3', 'type': 'jumper_3pin', 'reference_bbox': [610, 340, 60, 50],
        'orientation': 'horizontal', 'pin_numbering': {'scheme': 'left_to_right', 'pins': [1,2,3], 'pin1_side': 'left'},
        'allowed_states': ['1-2', '2-3', 'ABSENT'], 'expected_default': '1-2',
        'detection': {'method': 'aligned_crop', 'rotation_invariant': True, 'scale_invariant': True}
    })
    store.add_roi(board_id, {
        'roi_id': 'SW1', 'label': 'SW1', 'type': 'dip_switch_group', 'reference_bbox': [520, 210, 80, 50],
        'orientation': 'horizontal', 'switch_count': 4, 'layout': 'single_row',
        'indexing': {'position_1_at': 'left', 'increment_direction': 'left_to_right'},
        'state_semantics': {'on_side': 'left', 'off_side': 'right'},
        'allowed_states': ['ON', 'OFF'], 'expected_positions': {'1': 'ON', '2': 'OFF', '3': 'ON', '4': 'OFF'},
        'switch_regions': [
            {'index': 1, 'label': 'SW1.1', 'reference_bbox': [520,210,20,50]},
            {'index': 2, 'label': 'SW1.2', 'reference_bbox': [540,210,20,50]},
            {'index': 3, 'label': 'SW1.3', 'reference_bbox': [560,210,20,50]},
            {'index': 4, 'label': 'SW1.4', 'reference_bbox': [580,210,20,50]}
        ],
        'detection': {'method': 'aligned_crop', 'rotation_invariant': True, 'scale_invariant': True, 'classification_mode': 'per_switch'}
    })
    board = store.get_board(board_id)
    result = analyze_semantic_board(board, str(assets['board_image']), {'JP3': '1-2'})
    print(json.dumps(result, indent=2))
    assert result['board_id'] == board_id
    assert any(r['type'] == 'dip_switch_group' for r in result['results'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
