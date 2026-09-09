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

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    CV2_AVAILABLE = True
except Exception:
    cv2 = None
    np = None
    CV2_AVAILABLE = False

from .vision.align import _load_bgr, align_board_image, match_partial_region_features


logger = logging.getLogger(__name__)
VALID_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp'}
DEFAULT_ALIGNMENT_POLICY = {
    'full_board': {
        'min_inliers': 30,
        'min_score': 0.30,
        'min_inside_fraction': 0.70,
    },
    'partial_region': {
        'min_inliers': 15,
        'min_score': 0.20,
        'min_inside_fraction': 0.40,
    },
}


def _crop_bbox(img: Image.Image, bbox: List[int]) -> Image.Image:
    x, y, w, h = [int(v) for v in bbox]
    return img.crop((x, y, x + w, y + h))


def _mean_rgb(img: Image.Image) -> Tuple[float, float, float]:
    rgb = img.convert('RGB')
    data = list(rgb.getdata())
    if not data:
        return 0.0, 0.0, 0.0
    r = sum(p[0] for p in data) / len(data)
    g = sum(p[1] for p in data) / len(data)
    b = sum(p[2] for p in data) / len(data)
    return r, g, b


def _brightness(img: Image.Image) -> float:
    r, g, b = _mean_rgb(img)
    return (r + g + b) / 3.0


def _load_state_examples(examples_root: Path) -> Dict[str, List[Path]]:
    result: Dict[str, List[Path]] = {}
    if not examples_root.exists():
        return result
    for state_dir in sorted(p for p in examples_root.iterdir() if p.is_dir()):
        images = [p for p in sorted(state_dir.iterdir()) if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTS]
        if images:
            result[state_dir.name] = images
    return result


def _image_signature(img: Image.Image) -> Tuple[float, float, float, float]:
    img = img.convert('RGB').resize((32, 32))
    w, h = img.size
    left = img.crop((0, 0, w // 2, h))
    right = img.crop((w // 2, 0, w, h))
    top = img.crop((0, 0, w, h // 2))
    bottom = img.crop((0, h // 2, w, h))
    return (_brightness(left), _brightness(right), _brightness(top), _brightness(bottom))


def _signature_distance(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b))


def _best_example_match(query_img: Image.Image, examples_root: Path) -> Dict[str, Any] | None:
    state_examples = _load_state_examples(examples_root)
    if not state_examples:
        return None
    qsig = _image_signature(query_img)
    best_state = None
    best_path = None
    best_score = None
    for state, paths in state_examples.items():
        for path in paths:
            try:
                sig = _image_signature(Image.open(path).convert('RGB'))
            except Exception:
                continue
            dist = _signature_distance(qsig, sig)
            if best_score is None or dist < best_score:
                best_score = dist
                best_state = state
                best_path = path
    if best_state is None or best_score is None:
        return None
    confidence = max(0.5, min(0.99, 1.0 - (best_score / 300.0)))
    return {'state': best_state, 'confidence': round(confidence, 3), 'path': str(best_path)}


def _roi_examples_root(board: Dict[str, Any], roi_doc: Dict[str, Any]) -> Path:
    return Path(board['board_dir']) / 'rois' / roi_doc['roi_id'] / 'examples'


def _family_examples_root(board: Dict[str, Any], roi_doc: Dict[str, Any]) -> Path | None:
    family = roi_doc.get('component_family')
    if not family:
        return None
    project_root = Path(board['board_dir']).parents[1]
    roi_type = (roi_doc.get('type') or '').lower()
    family_type_map = {
        'jumper_3pin': 'jumper_3pin',
        'dip_switch_group': 'dip_switch_position',
    }
    family_type = family_type_map.get(roi_type)
    if not family_type:
        return None
    return project_root / 'component_families' / family_type / family / 'examples'


def _map_visual_to_semantic_for_jumper3(visual_state: str, roi_doc: Dict[str, Any]) -> str:
    if visual_state in {'1-2', '2-3', 'ABSENT'}:
        return visual_state
    scheme = ((roi_doc.get('pin_numbering') or {}).get('scheme') or 'left_to_right').lower()
    if visual_state == 'ABSENT':
        return 'ABSENT'
    if visual_state == 'LEFT_PAIR':
        return '1-2' if scheme in {'left_to_right', 'top_to_bottom'} else '2-3'
    if visual_state == 'RIGHT_PAIR':
        return '2-3' if scheme in {'left_to_right', 'top_to_bottom'} else '1-2'
    return visual_state


def _bbox_polygon(bbox: List[int]) -> np.ndarray:
    x, y, w, h = [int(v) for v in bbox]
    return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.float32)


def _polygon_area(poly: np.ndarray) -> float:
    return float(abs(cv2.contourArea(poly.astype(np.float32))))


def _clip_polygon_to_rect(poly: np.ndarray, width: int, height: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    pts = poly.astype(np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(mask, [pts], 255)
    ys, xs = np.where(mask > 0)
    if len(xs) == 0 or len(ys) == 0:
        return np.empty((0, 2), dtype=np.float32)
    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float32)


def _roi_is_inside_query(roi_bbox: List[int], query_polygon: np.ndarray, coverage_threshold: float = 0.35) -> tuple[bool, float]:
    roi_poly = _bbox_polygon(roi_bbox)
    x, y, w, h = [int(v) for v in roi_bbox]
    canvas_w = int(max(np.max(query_polygon[:, 0]), x + w) + 10)
    canvas_h = int(max(np.max(query_polygon[:, 1]), y + h) + 10)
    if canvas_w <= 0 or canvas_h <= 0:
        return False, 0.0

    roi_mask = np.zeros((canvas_h, canvas_w), dtype=np.uint8)
    query_mask = np.zeros((canvas_h, canvas_w), dtype=np.uint8)
    cv2.fillPoly(roi_mask, [roi_poly.astype(np.int32).reshape((-1, 1, 2))], 255)
    cv2.fillPoly(query_mask, [query_polygon.astype(np.int32).reshape((-1, 1, 2))], 255)
    overlap = cv2.bitwise_and(roi_mask, query_mask)
    roi_area = max(1, int(np.count_nonzero(roi_mask)))
    overlap_area = int(np.count_nonzero(overlap))
    coverage = overlap_area / roi_area
    return coverage >= coverage_threshold, coverage


def _polygon_inside_fraction(poly: np.ndarray, width: int, height: int) -> float:
    if poly.size == 0:
        return 0.0
    total_area = _polygon_area(poly)
    if total_area <= 1.0:
        return 0.0
    clipped = _clip_polygon_to_rect(poly, width, height)
    if clipped.size == 0:
        return 0.0
    clipped_area = _polygon_area(clipped)
    return max(0.0, min(1.0, clipped_area / total_area))


def _alignment_quality(result: Dict[str, Any], ref_width: int, ref_height: int) -> float:
    if not result.get('success'):
        return -1.0
    polygon = result.get('query_corners_in_reference')
    if not polygon:
        return -1.0
    poly = np.array(polygon, dtype=np.float32)
    inside_fraction = _polygon_inside_fraction(poly, ref_width, ref_height)
    inliers = float(result.get('inliers', 0))
    score = float(result.get('score', 0.0))
    if inside_fraction < 0.5:
        return -1.0
    return score + min(0.4, inliers / 500.0) + 0.2 * inside_fraction


def _resolve_alignment_policy(board: Dict[str, Any], mode: str) -> Dict[str, float]:
    board_policy = board.get('alignment_policy') or {}
    mode_policy = board_policy.get(mode) or {}
    default_mode_policy = DEFAULT_ALIGNMENT_POLICY.get(mode, {})
    resolved = dict(default_mode_policy)
    resolved.update(mode_policy)
    return {
        'min_inliers': float(resolved.get('min_inliers', default_mode_policy.get('min_inliers', 20))),
        'min_score': float(resolved.get('min_score', default_mode_policy.get('min_score', 0.25))),
        'min_inside_fraction': float(resolved.get('min_inside_fraction', default_mode_policy.get('min_inside_fraction', 0.5))),
    }


def _alignment_verdict(result: Dict[str, Any], ref_width: int, ref_height: int, policy: Dict[str, float]) -> Dict[str, Any]:
    if not result.get('success'):
        return {
            'accepted': False,
            'ignore_downstream': True,
            'reason': result.get('reason', 'alignment_failed'),
            'quality': -1.0,
            'inside_fraction': 0.0,
            'score': float(result.get('score', 0.0) or 0.0),
            'inliers': int(result.get('inliers', 0) or 0),
            'policy': policy,
        }
    polygon = result.get('query_corners_in_reference')
    if not polygon:
        return {
            'accepted': False,
            'ignore_downstream': True,
            'reason': 'missing_query_polygon',
            'quality': -1.0,
            'inside_fraction': 0.0,
            'score': float(result.get('score', 0.0) or 0.0),
            'inliers': int(result.get('inliers', 0) or 0),
            'policy': policy,
        }
    poly = np.array(polygon, dtype=np.float32)
    inside_fraction = _polygon_inside_fraction(poly, ref_width, ref_height)
    inliers = int(result.get('inliers', 0) or 0)
    score = float(result.get('score', 0.0) or 0.0)
    quality = _alignment_quality(result, ref_width, ref_height)

    if inside_fraction < policy['min_inside_fraction']:
        return {
            'accepted': False,
            'ignore_downstream': True,
            'reason': 'projected_polygon_outside_reference',
            'quality': quality,
            'inside_fraction': inside_fraction,
            'score': score,
            'inliers': inliers,
            'policy': policy,
        }
    if inliers < policy['min_inliers']:
        return {
            'accepted': False,
            'ignore_downstream': True,
            'reason': 'too_few_inliers',
            'quality': quality,
            'inside_fraction': inside_fraction,
            'score': score,
            'inliers': inliers,
            'policy': policy,
        }
    if score < policy['min_score']:
        return {
            'accepted': False,
            'ignore_downstream': True,
            'reason': 'low_inlier_ratio',
            'quality': quality,
            'inside_fraction': inside_fraction,
            'score': score,
            'inliers': inliers,
            'policy': policy,
        }
    return {
        'accepted': True,
        'ignore_downstream': False,
        'reason': 'ok',
        'quality': quality,
        'inside_fraction': inside_fraction,
        'score': score,
        'inliers': inliers,
        'policy': policy,
    }


def _align_image_to_board_reference(board: Dict[str, Any], image_path: str, debug_output_dir: Path | None = None) -> Tuple[Image.Image, Dict[str, Any]]:
    test_img = Image.open(Path(image_path)).convert('RGB')
    ref_path = Path(board.get('reference_image_path') or '')
    if not CV2_AVAILABLE or not ref_path.exists():
        logger.error('Alignment unavailable: cv2 missing or reference image missing for board %s', board.get('board_id'))
        return test_img, {'aligned': False, 'reason': 'cv2 unavailable or reference image missing', 'mode': 'none'}

    ref_bgr = _load_bgr(str(ref_path))
    ref_h, ref_w = ref_bgr.shape[:2]

    logger.info('Trying full-board alignment for board %s on image %s', board.get('board_id'), image_path)
    full_result = align_board_image(str(ref_path), str(image_path))
    logger.info('Trying partial-region alignment for board %s on image %s', board.get('board_id'), image_path)
    partial_result = match_partial_region_features(str(ref_path), str(image_path))

    full_policy = _resolve_alignment_policy(board, 'full_board')
    partial_policy = _resolve_alignment_policy(board, 'partial_region')
    full_verdict = _alignment_verdict(full_result, ref_w, ref_h, full_policy)
    partial_verdict = _alignment_verdict(partial_result, ref_w, ref_h, partial_policy)
    full_quality = float(full_verdict['quality'])
    partial_quality = float(partial_verdict['quality'])

    logger.debug('Full alignment result: good_matches=%s inliers=%s score=%s verdict=%s', full_result.get('good_matches'), full_result.get('inliers'), full_result.get('score'), full_verdict)
    logger.debug('Partial alignment result: good_matches=%s inliers=%s score=%s verdict=%s', partial_result.get('good_matches'), partial_result.get('inliers'), partial_result.get('score'), partial_verdict)

    chosen = None
    chosen_mode = None
    chosen_verdict = None
    if full_verdict['accepted'] and (full_quality >= partial_quality or not partial_verdict['accepted']):
        chosen = full_result
        chosen_mode = 'full_board'
        chosen_verdict = full_verdict
    elif partial_verdict['accepted']:
        chosen = partial_result
        chosen_mode = 'partial_region'
        chosen_verdict = partial_verdict

    if chosen is not None:
        logger.info('Selected alignment mode=%s for board %s', chosen_mode, board.get('board_id'))
        aligned_bgr = chosen.get('aligned_bgr')
        rgb = cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB)
        aligned_img = Image.fromarray(rgb)
        info = {
            'aligned': True,
            'alignment_failed': False,
            'ignore_downstream': False,
            'mode': chosen_mode,
            'method': chosen.get('method', 'orb'),
            'good_matches': chosen.get('good_matches'),
            'inliers': chosen.get('inliers'),
            'score': chosen.get('score'),
            'quality': chosen_verdict['quality'] if chosen_verdict else None,
            'inside_fraction': chosen_verdict['inside_fraction'] if chosen_verdict else None,
            'reference_image_path': str(ref_path),
            'query_polygon_in_reference': chosen.get('query_corners_in_reference'),
            'full_alignment': {k: v for k, v in full_result.items() if k != 'aligned_bgr'},
            'partial_alignment': {k: v for k, v in partial_result.items() if k != 'aligned_bgr'},
            'full_alignment_verdict': full_verdict,
            'partial_alignment_verdict': partial_verdict,
        }
        if debug_output_dir is not None:
            debug_output_dir.mkdir(parents=True, exist_ok=True)
            aligned_name = 'aligned_full_board.png' if chosen_mode == 'full_board' else 'aligned_partial_region.png'
            aligned_path = debug_output_dir / aligned_name
            overlay_path = debug_output_dir / f"{aligned_name.rsplit('.', 1)[0]}_overlay.png"
            aligned_img.save(aligned_path)
            overlay = ref_bgr.copy()
            if chosen.get('query_corners_in_reference'):
                query_polygon = np.array(chosen['query_corners_in_reference'], dtype=np.float32)
                cv2.polylines(overlay, [query_polygon.astype(np.int32).reshape((-1, 1, 2))], True, (0, 0, 255), 4)
            cv2.imwrite(str(overlay_path), overlay)
            info['aligned_image_path'] = str(aligned_path)
            info['overlay_image_path'] = str(overlay_path)
        return aligned_img, info

    logger.warning('Alignment failed for board %s; downstream operations should be ignored', board.get('board_id'))
    return test_img, {
        'aligned': False,
        'alignment_failed': True,
        'ignore_downstream': True,
        'reason': 'full and partial alignment failed or were rejected by quality checks',
        'mode': 'none',
        'full_alignment': {k: v for k, v in full_result.items() if k != 'aligned_bgr'},
        'partial_alignment': {k: v for k, v in partial_result.items() if k != 'aligned_bgr'},
        'full_alignment_verdict': full_verdict,
        'partial_alignment_verdict': partial_verdict,
    }


def classify_jumper_2pin(board: Dict[str, Any], roi_doc: Dict[str, Any], roi_img: Image.Image) -> Dict[str, Any]:
    roi_examples = _best_example_match(roi_img, _roi_examples_root(board, roi_doc))
    if roi_examples:
        return {'detected': roi_examples['state'], 'confidence': roi_examples['confidence'], 'source': 'roi_examples', 'example_path': roi_examples['path']}
    brightness = _brightness(roi_img)
    detected = 'PRESENT' if brightness < 170 else 'ABSENT'
    return {'detected': detected, 'confidence': 0.85, 'source': 'heuristic'}


def classify_jumper_3pin(board: Dict[str, Any], roi_doc: Dict[str, Any], roi_img: Image.Image) -> Dict[str, Any]:
    roi_examples = _best_example_match(roi_img, _roi_examples_root(board, roi_doc))
    if roi_examples:
        semantic = _map_visual_to_semantic_for_jumper3(roi_examples['state'], roi_doc)
        return {'detected': semantic, 'confidence': roi_examples['confidence'], 'source': 'roi_examples', 'example_path': roi_examples['path']}

    family_root = _family_examples_root(board, roi_doc)
    if family_root:
        family_match = _best_example_match(roi_img, family_root)
        if family_match:
            semantic = _map_visual_to_semantic_for_jumper3(family_match['state'], roi_doc)
            return {'detected': semantic, 'confidence': family_match['confidence'], 'source': 'family_examples', 'example_path': family_match['path'], 'visual_state': family_match['state']}

    w, h = roi_img.size
    horizontal = w >= h
    if horizontal:
        left = roi_img.crop((0, 0, w // 2, h))
        right = roi_img.crop((w // 2, 0, w, h))
    else:
        left = roi_img.crop((0, 0, w, h // 2))
        right = roi_img.crop((0, h // 2, w, h))
    l_b = _brightness(left)
    r_b = _brightness(right)
    if abs(l_b - r_b) < 8:
        detected = 'ABSENT' if max(l_b, r_b) > 175 else '1-2'
    else:
        visual = 'LEFT_PAIR' if l_b < r_b else 'RIGHT_PAIR'
        detected = _map_visual_to_semantic_for_jumper3(visual, roi_doc)
    return {'detected': detected, 'confidence': 0.8, 'source': 'heuristic', 'brightness_left': l_b, 'brightness_right': r_b}


def _auto_switch_regions(roi_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    bbox = roi_doc['reference_bbox']
    x, y, w, h = [int(v) for v in bbox]
    count = max(1, int(roi_doc.get('switch_count', 1)))
    layout = roi_doc.get('layout', 'single_column')
    regions = []
    if layout == 'single_row':
        seg = w / count
        for i in range(count):
            regions.append({'index': i + 1, 'label': f"{roi_doc.get('label', roi_doc['roi_id'])}.{i + 1}", 'reference_bbox': [round(x + i * seg), y, max(1, round(seg)), h]})
    else:
        seg = h / count
        for i in range(count):
            regions.append({'index': i + 1, 'label': f"{roi_doc.get('label', roi_doc['roi_id'])}.{i + 1}", 'reference_bbox': [x, round(y + i * seg), w, max(1, round(seg))]})
    return regions


def classify_dip_switch_group(board: Dict[str, Any], roi_doc: Dict[str, Any], board_img: Image.Image, debug_output_dir: Path | None = None) -> Dict[str, Any]:
    switch_regions = roi_doc.get('switch_regions') or _auto_switch_regions(roi_doc)
    on_side = ((roi_doc.get('state_semantics') or {}).get('on_side') or 'left').lower()
    family_root = _family_examples_root(board, roi_doc)
    results: List[Dict[str, Any]] = []
    for item in switch_regions:
        crop = _crop_bbox(board_img, item['reference_bbox'])
        if debug_output_dir is not None:
            crop.save(debug_output_dir / f"{roi_doc['roi_id']}__pos_{item['index']}.png")

        roi_examples_root = _roi_examples_root(board, roi_doc)
        roi_match = _best_example_match(crop, roi_examples_root)
        source = None
        example_path = None
        if roi_match:
            detected = roi_match['state']
            confidence = roi_match['confidence']
            source = 'roi_examples'
            example_path = roi_match['path']
        else:
            family_match = _best_example_match(crop, family_root) if family_root else None
            if family_match:
                detected = family_match['state']
                confidence = family_match['confidence']
                source = 'family_examples'
                example_path = family_match['path']
            else:
                w, h = crop.size
                if on_side in ('left', 'right'):
                    left = crop.crop((0, 0, w // 2, h))
                    right = crop.crop((w // 2, 0, w, h))
                    left_b = _brightness(left)
                    right_b = _brightness(right)
                    if on_side == 'left':
                        detected = 'ON' if left_b > right_b else 'OFF'
                    else:
                        detected = 'ON' if right_b > left_b else 'OFF'
                    confidence = 0.7 + min(0.25, abs(left_b - right_b) / 255.0)
                else:
                    a = crop.crop((0, 0, w, h // 2))
                    b = crop.crop((0, h // 2, w, h))
                    a_b = _brightness(a)
                    b_b = _brightness(b)
                    detected = 'ON' if (a_b < b_b if on_side == 'top' else b_b < a_b) else 'OFF'
                    confidence = 0.7 + min(0.25, abs(a_b - b_b) / 255.0)
                source = 'heuristic'
        idx = str(item['index'])
        expected_positions = roi_doc.get('expected_positions') or {}
        expected = expected_positions.get(idx)
        status = 'OK' if expected is None or detected == expected else 'MISMATCH'
        action = None if status == 'OK' else f"Set {roi_doc.get('label', roi_doc['roi_id'])} position {idx} to {expected}"
        result = {'index': item['index'], 'label': item.get('label', idx), 'detected': detected, 'expected': expected, 'status': status, 'confidence': round(confidence, 3), 'action': action, 'source': source}
        if example_path:
            result['example_path'] = example_path
        results.append(result)
    overall_status = 'PASS' if all(r['status'] == 'OK' for r in results) else 'FAIL'
    return {'type': 'dip_switch_group', 'positions': results, 'overall_status': overall_status}


def get_board_photo_hints(board: Dict[str, Any], mode: str = 'auto') -> List[str]:
    hints = [
        'Take the picture from above, as perpendicular to the board as possible.',
        'Use good focus so jumper caps and DIP switch sliders are sharp.',
        'Avoid glare and strong reflections on black plastic and metal pins.',
        'Use uniform lighting and avoid deep shadows over the ROI area.',
    ]
    if mode in {'auto', 'full_board'}:
        hints.append('If possible, include the full board in the image for the most reliable alignment.')
    if mode in {'auto', 'partial_region'}:
        hints.append('For partial images, include distinctive nearby components or silkscreen, not only the target ROI.')
    orientation_ref = board.get('board_orientation_reference')
    if orientation_ref:
        hints.append(f'Board reference orientation: {orientation_ref}.')
    extra = board.get('photo_hints') or []
    if isinstance(extra, list):
        hints.extend(str(x) for x in extra)
    return hints


def analyze_semantic_board(board: Dict[str, Any], image_path: str, expected_config: Dict[str, Any] | None = None, debug_output_dir: str | None = None, align_to_reference: bool = True) -> Dict[str, Any]:
    expected_config = expected_config or {}
    logger.info('Starting board analysis board_id=%s image=%s', board.get('board_id'), image_path)
    debug_dir = Path(debug_output_dir) if debug_output_dir else None
    working_img, align_info = _align_image_to_board_reference(board, image_path, debug_dir if align_to_reference else None) if align_to_reference else (Image.open(Path(image_path)).convert('RGB'), {'aligned': False, 'alignment_failed': False, 'ignore_downstream': False, 'reason': 'alignment disabled', 'mode': 'none'})
    if debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)
    if align_info.get('ignore_downstream'):
        logger.error('Alignment rejected for board_id=%s image=%s reason=%s', board.get('board_id'), image_path, align_info.get('reason'))
        return {
            'board_id': board['board_id'],
            'overall_status': 'ALIGNMENT_FAILED',
            'alignment': align_info,
            'results': [],
            'message': 'Alignment process failed; downstream ROI operations should be ignored.',
        }
    results: List[Dict[str, Any]] = []
    overall_status = 'PASS'

    query_polygon = None
    if align_info.get('mode') == 'partial_region' and align_info.get('query_polygon_in_reference'):
        query_polygon = np.array(align_info['query_polygon_in_reference'], dtype=np.float32)

    for item in board.get('rois', []):
        roi = item['roi'] if 'roi' in item else item
        roi_type = roi.get('type', 'generic_roi')
        label = roi.get('label', roi.get('roi_id'))

        if query_polygon is not None:
            inside, coverage = _roi_is_inside_query(roi['reference_bbox'], query_polygon)
            if not inside:
                logger.debug('ROI %s is outside partial image coverage=%.3f', roi.get('roi_id'), coverage)
                results.append({
                    'roi_id': roi['roi_id'],
                    'label': label,
                    'type': roi_type,
                    'detected': 'outside the image',
                    'expected': expected_config.get(label, expected_config.get(roi['roi_id'])),
                    'status': 'OUTSIDE',
                    'coverage': round(float(coverage), 3),
                    'confidence': 1.0,
                    'action': None,
                })
                continue

        roi_img = _crop_bbox(working_img, roi['reference_bbox'])
        if debug_dir is not None:
            roi_img.save(debug_dir / f"{roi['roi_id']}.png")
        if roi_type == 'jumper_2pin':
            out = classify_jumper_2pin(board, roi, roi_img)
            expected = expected_config.get(label, expected_config.get(roi['roi_id'], roi.get('expected_default')))
            status = 'OK' if expected is None or out['detected'] == expected else 'MISMATCH'
            if status != 'OK':
                overall_status = 'FAIL'
            results.append({'roi_id': roi['roi_id'], 'label': label, 'type': roi_type, 'detected': out['detected'], 'expected': expected, 'status': status, 'confidence': out['confidence'], 'source': out.get('source'), 'action': None if status == 'OK' else f"Set {label} to {expected}"})
        elif roi_type == 'jumper_3pin':
            out = classify_jumper_3pin(board, roi, roi_img)
            expected = expected_config.get(label, expected_config.get(roi['roi_id'], roi.get('expected_default')))
            status = 'OK' if expected is None or out['detected'] == expected else 'MISMATCH'
            if status != 'OK':
                overall_status = 'FAIL'
            results.append({'roi_id': roi['roi_id'], 'label': label, 'type': roi_type, 'detected': out['detected'], 'expected': expected, 'status': status, 'confidence': out['confidence'], 'source': out.get('source'), 'visual_state': out.get('visual_state'), 'action': None if status == 'OK' else f"Move shunt on {label} to {expected}"})
        elif roi_type == 'dip_switch_group':
            cfg = expected_config.get(label, expected_config.get(roi['roi_id'], roi.get('expected_positions', {})))
            roi_for_eval = dict(roi)
            if isinstance(cfg, dict):
                roi_for_eval['expected_positions'] = cfg
            out = classify_dip_switch_group(board, roi_for_eval, working_img, debug_dir)
            if out['overall_status'] != 'PASS':
                overall_status = 'FAIL'
            results.append({'roi_id': roi['roi_id'], 'label': label, **out})
        else:
            results.append({'roi_id': roi['roi_id'], 'label': label, 'type': roi_type, 'status': 'REVIEW', 'reason': 'No semantic analyzer for ROI type'})
    logger.info('Board analysis finished board_id=%s overall_status=%s', board.get('board_id'), overall_status)
    return {'board_id': board['board_id'], 'overall_status': overall_status, 'alignment': align_info, 'results': results}
