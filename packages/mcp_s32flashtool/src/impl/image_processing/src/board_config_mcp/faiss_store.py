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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from .schemas import ROIExampleRecord
from .vision.embeddings import compute_embedding

try:
    import faiss  # type: ignore
    FAISS_AVAILABLE = True
except Exception:
    faiss = None
    FAISS_AVAILABLE = False


@dataclass
class SearchHit:
    score: float
    metadata: Dict[str, Any]


class FaissStore:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.board_meta_path = self.index_dir / 'board_metadata.json'
        self.roi_meta_path = self.index_dir / 'roi_metadata.json'
        self.board_index_path = self.index_dir / 'board.index'
        self.roi_index_path = self.index_dir / 'roi.index'
        self.board_metadata: List[Dict[str, Any]] = self._load_meta(self.board_meta_path)
        self.roi_metadata: List[Dict[str, Any]] = self._load_meta(self.roi_meta_path)
        self.roi_examples: List[ROIExampleRecord] = []
        self.board_index = self._load_index(self.board_index_path)
        self.roi_index = self._load_index(self.roi_index_path)

    def _load_meta(self, path: Path) -> List[Dict[str, Any]]:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        return []

    def _load_index(self, path: Path):
        if not FAISS_AVAILABLE or not path.exists():
            return None
        return faiss.read_index(str(path))

    def _ensure_index(self, current, dim: int):
        if current is not None:
            return current
        if not FAISS_AVAILABLE:
            return None
        return faiss.IndexFlatIP(dim)

    def _to_vector(self, emb: np.ndarray) -> np.ndarray:
        vec = np.asarray(emb, dtype=np.float32).reshape(1, -1)
        norm = np.linalg.norm(vec, axis=1, keepdims=True)
        norm[norm == 0] = 1.0
        return vec / norm

    def add_board_image(self, board_id: str, image_path: str, kind: str = 'board_reference', bbox: Optional[Iterable[int]] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        emb = compute_embedding(image_path, bbox=bbox)
        vec = self._to_vector(emb)
        self.board_index = self._ensure_index(self.board_index, vec.shape[1])
        if self.board_index is not None:
            self.board_index.add(vec)
        metadata = {
            'board_id': board_id,
            'image_path': str(image_path),
            'kind': kind,
            'bbox': list(bbox) if bbox is not None else None,
        }
        if extra:
            metadata.update(extra)
        self.board_metadata.append(metadata)
        return metadata

    def add_roi_example(self, record: ROIExampleRecord) -> Dict[str, Any]:
        self.roi_examples.append(record)
        emb = compute_embedding(record.image_path)
        vec = self._to_vector(emb)
        self.roi_index = self._ensure_index(self.roi_index, vec.shape[1])
        if self.roi_index is not None:
            self.roi_index.add(vec)
        metadata = {
            'board_id': record.board_id,
            'roi_id': record.roi_id,
            'label': record.label,
            'component_type': record.component_type,
            'state': record.state,
            'image_path': record.image_path,
        }
        self.roi_metadata.append(metadata)
        return metadata

    def search_board_image(self, image_path: str, top_k: int = 3, bbox: Optional[Iterable[int]] = None) -> List[Dict[str, Any]]:
        if self.board_index is None or not self.board_metadata:
            return []
        query = self._to_vector(compute_embedding(image_path, bbox=bbox))
        scores, ids = self.board_index.search(query, min(top_k, len(self.board_metadata)))
        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            meta = dict(self.board_metadata[int(idx)])
            meta['score'] = float(score)
            results.append(meta)
        return results

    def search_roi_image(self, image_path: str, top_k: int = 5, bbox: Optional[Iterable[int]] = None) -> List[Dict[str, Any]]:
        if self.roi_index is None or not self.roi_metadata:
            return []
        query = self._to_vector(compute_embedding(image_path, bbox=bbox))
        scores, ids = self.roi_index.search(query, min(top_k, len(self.roi_metadata)))
        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            meta = dict(self.roi_metadata[int(idx)])
            meta['score'] = float(score)
            results.append(meta)
        return results

    def save(self) -> None:
        self.board_meta_path.write_text(json.dumps(self.board_metadata, indent=2), encoding='utf-8')
        self.roi_meta_path.write_text(json.dumps(self.roi_metadata, indent=2), encoding='utf-8')
        if FAISS_AVAILABLE and self.board_index is not None:
            faiss.write_index(self.board_index, str(self.board_index_path))
        if FAISS_AVAILABLE and self.roi_index is not None:
            faiss.write_index(self.roi_index, str(self.roi_index_path))
