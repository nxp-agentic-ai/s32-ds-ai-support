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
import shutil
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image


class BoardDatasetStore:
    def __init__(self, boards_dir: Path):
        self.boards_dir = Path(boards_dir)
        self.boards_dir.mkdir(parents=True, exist_ok=True)

    def _board_dir(self, board_id: str) -> Path:
        return self.boards_dir / board_id

    def _board_json(self, board_id: str) -> Path:
        return self._board_dir(board_id) / 'board.json'

    def _roi_dir(self, board_id: str, roi_id: str) -> Path:
        return self._board_dir(board_id) / 'rois' / roi_id

    def list_boards(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        if not self.boards_dir.exists():
            return result
        for board_dir in sorted(p for p in self.boards_dir.iterdir() if p.is_dir()):
            board_json = board_dir / 'board.json'
            if board_json.exists():
                try:
                    result.append(json.loads(board_json.read_text(encoding='utf-8')))
                except Exception:
                    continue
        return result

    def _resolve_source_image(self, reference_image_path: str) -> Path:
        src = Path(reference_image_path)
        if src.exists() and src.is_file():
            return src.resolve()
        normalized = Path(reference_image_path.replace(chr(92), '/'))
        candidates: List[Path] = []
        if not normalized.is_absolute():
            project_root = self.boards_dir.parent
            candidates.extend([
                Path.cwd() / normalized,
                project_root / normalized,
                self.boards_dir / normalized,
            ])
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()
        raise FileNotFoundError(f'Reference image not found: {reference_image_path}')

    def create_board(self, board_id: str, name: str, reference_image_path: str) -> Dict[str, Any]:
        board_dir = self._board_dir(board_id)
        images_dir = board_dir / 'images'
        rois_dir = board_dir / 'rois'
        images_dir.mkdir(parents=True, exist_ok=True)
        rois_dir.mkdir(parents=True, exist_ok=True)

        src = self._resolve_source_image(reference_image_path)
        dst = images_dir / src.name
        if not dst.exists() or src.resolve() != dst.resolve():
            shutil.copy2(src, dst)

        existing = {}
        board_json = self._board_json(board_id)
        if board_json.exists():
            try:
                existing = json.loads(board_json.read_text(encoding='utf-8'))
            except Exception:
                existing = {}

        board = dict(existing)
        board.update({
            'schema_version': existing.get('schema_version', '1.0'),
            'board_id': board_id,
            'name': name,
            'reference_image': str(Path('images') / dst.name),
            'match_mode': existing.get('match_mode', 'feature_homography'),
            'board_orientation_reference': existing.get('board_orientation_reference', 'unknown'),
            'anchor_points': existing.get('anchor_points', []),
            'notes': existing.get('notes', ''),
            'rois': existing.get('rois', []),
        })
        board_json.write_text(json.dumps(board, indent=2), encoding='utf-8')
        return {'board_id': board_id, 'board_dir': str(board_dir), 'reference_image': str(dst)}

    def get_board(self, board_id: str) -> Dict[str, Any]:
        board_path = self._board_json(board_id)
        if not board_path.exists():
            raise FileNotFoundError(f'Board not found: {board_id}')
        board = json.loads(board_path.read_text(encoding='utf-8'))
        rois: List[Dict[str, Any]] = []
        rois_dir = self._board_dir(board_id) / 'rois'
        if rois_dir.exists():
            for roi_dir in sorted(p for p in rois_dir.iterdir() if p.is_dir()):
                roi_json = roi_dir / 'roi.json'
                if roi_json.exists():
                    rois.append({'roi_id': roi_dir.name, 'roi': json.loads(roi_json.read_text(encoding='utf-8'))})
        board['rois'] = rois
        board_dir = self._board_dir(board_id)
        board['board_dir'] = str(board_dir)
        rel_ref = board.get('reference_image')
        if rel_ref:
            board['reference_image_path'] = str((board_dir / Path(rel_ref)).resolve())
        return board

    def _normalize_roi(self, roi: Dict[str, Any]) -> Dict[str, Any]:
        roi_doc = dict(roi)
        roi_type = roi_doc.get('type', 'generic_roi')
        if roi_type == 'dip_switch':
            roi_doc['type'] = 'dip_switch_group'
            roi_doc.setdefault('switch_count', 1)
            roi_doc.setdefault('layout', 'single_column')
            roi_doc.setdefault('indexing', {'position_1_at': 'top', 'increment_direction': 'top_to_bottom'})
            roi_doc.setdefault('state_semantics', {'on_side': 'left', 'off_side': 'right'})
            roi_doc.setdefault('allowed_states', ['ON', 'OFF'])
            roi_doc.setdefault('expected_positions', {'1': roi_doc.get('expected_default', 'OFF')})
        roi_doc.setdefault('schema_version', '1.0')
        roi_doc.setdefault('orientation', 'unknown')
        roi_doc.setdefault('detection', {'method': 'aligned_crop', 'rotation_invariant': True, 'scale_invariant': True})
        return roi_doc

    def add_roi(self, board_id: str, roi: Dict[str, Any]) -> Dict[str, Any]:
        self.get_board(board_id)
        incoming = self._normalize_roi(roi)
        roi_id = incoming['roi_id']
        roi_dir = self._roi_dir(board_id, roi_id)
        examples_dir = roi_dir / 'examples'
        roi_dir.mkdir(parents=True, exist_ok=True)
        examples_dir.mkdir(parents=True, exist_ok=True)

        roi_json_path = roi_dir / 'roi.json'
        existing = {}
        if roi_json_path.exists():
            try:
                existing = json.loads(roi_json_path.read_text(encoding='utf-8'))
            except Exception:
                existing = {}

        roi_doc = dict(existing)
        roi_doc.update(incoming)
        roi_json_path.write_text(json.dumps(roi_doc, indent=2), encoding='utf-8')

        board_json_path = self._board_json(board_id)
        board_data = json.loads(board_json_path.read_text(encoding='utf-8'))
        roi_ids = list(board_data.get('rois', []))
        if roi_id not in roi_ids:
            roi_ids.append(roi_id)
            board_data['rois'] = roi_ids
            board_json_path.write_text(json.dumps(board_data, indent=2), encoding='utf-8')

        ref_bbox = roi_doc.get('reference_bbox')
        board = self.get_board(board_id)
        if ref_bbox and board.get('reference_image_path'):
            try:
                self._generate_roi_reference_crop(board_id, roi_id, Path(board['reference_image_path']), list(ref_bbox))
            except Exception:
                pass
        return {'board_id': board_id, 'roi_id': roi_id, 'roi_dir': str(roi_dir)}

    def save_board_with_rois(self, board_id: str, name: str, reference_image_path: str, rois: List[Dict[str, Any]]) -> Dict[str, Any]:
        created = self.create_board(board_id, name, reference_image_path)
        normalized_rois = [self._normalize_roi(r) for r in rois]
        board_json_path = self._board_json(board_id)
        existing = {}
        if board_json_path.exists():
            try:
                existing = json.loads(board_json_path.read_text(encoding='utf-8'))
            except Exception:
                existing = {}
        board_data = dict(existing)
        board_data.update({
            'schema_version': existing.get('schema_version', '1.0'),
            'board_id': board_id,
            'name': name,
            'reference_image': existing.get('reference_image', str(Path('images') / Path(reference_image_path).name)),
            'match_mode': existing.get('match_mode', 'feature_homography'),
            'board_orientation_reference': existing.get('board_orientation_reference', 'unknown'),
            'anchor_points': existing.get('anchor_points', []),
            'notes': existing.get('notes', ''),
            'rois': [r['roi_id'] for r in normalized_rois],
        })
        board_json_path.write_text(json.dumps(board_data, indent=2), encoding='utf-8')
        for roi in normalized_rois:
            self.add_roi(board_id, roi)
        return {**created, 'roi_count': len(normalized_rois)}

    def _generate_roi_reference_crop(self, board_id: str, roi_id: str, board_image_abs: Path, reference_bbox: List[int]) -> Path:
        img = Image.open(board_image_abs).convert('RGB')
        x, y, w, h = [int(v) for v in reference_bbox]
        crop = img.crop((x, y, x + w, y + h))
        roi_dir = self._roi_dir(board_id, roi_id)
        images_dir = roi_dir / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        out = images_dir / 'reference_crop.png'
        crop.save(out)
        roi_json = roi_dir / 'roi.json'
        if roi_json.exists():
            data = json.loads(roi_json.read_text(encoding='utf-8'))
            data['reference_image'] = str(Path('images') / 'reference_crop.png')
            roi_json.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return out

    def export_board_to_template(self, board_id: str, templates_dir: Path) -> Path:
        board = self.get_board(board_id)
        regions = []
        for item in board.get('rois', []):
            roi = item['roi']
            regions.append({'id': roi['roi_id'], 'label': roi.get('label', roi['roi_id']), 'type': roi.get('type', 'generic_roi'), 'bbox': roi['reference_bbox'], 'expected_states': roi.get('allowed_states', [])})
        template = {'board_id': board['board_id'], 'reference_image': board['reference_image'], 'landmarks': [], 'regions_of_interest': regions}
        out_dir = Path(templates_dir) / board_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'template.json'
        out_path.write_text(json.dumps(template, indent=2), encoding='utf-8')
        return out_path
