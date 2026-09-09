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

from PIL import Image, ImageDraw



def annotate_image_file(image_path: str, bboxes: Iterable[Iterable[int]], output_path: str) -> dict:
    img = Image.open(image_path).convert('RGB')
    draw = ImageDraw.Draw(img)
    for bbox in bboxes:
        x, y, w, h = [int(v) for v in bbox]
        draw.rectangle((x, y, x + w, y + h), outline='red', width=3)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return {'output_path': str(out)}
