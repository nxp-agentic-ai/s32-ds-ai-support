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

from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


EMBEDDING_SIZE = 512


def load_image_rgb(image_path: str | Path) -> np.ndarray:
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def crop_bbox(image: np.ndarray, bbox: Iterable[int] | None) -> np.ndarray:
    if bbox is None:
        return image
    x, y, w, h = [int(v) for v in bbox]
    x = max(0, x)
    y = max(0, y)
    return image[y:y + max(1, h), x:x + max(1, w)]


def compute_embedding(image_path: str | Path, bbox: Iterable[int] | None = None) -> np.ndarray:
    image = load_image_rgb(image_path)
    image = crop_bbox(image, bbox)
    if image.size == 0:
        raise ValueError("Empty image crop for embedding")

    small = cv2.resize(image, (32, 32), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)

    parts = []

    for ch in cv2.split(small):
        hist = cv2.calcHist([ch], [0], None, [32], [0, 256]).flatten()
        parts.append(hist)

    for ch in cv2.split(hsv):
        hist = cv2.calcHist([ch], [0], None, [32], [0, 256]).flatten()
        parts.append(hist)

    parts.append(gray.flatten().astype(np.float32))

    emb = np.concatenate(parts).astype(np.float32)
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm
    return emb
