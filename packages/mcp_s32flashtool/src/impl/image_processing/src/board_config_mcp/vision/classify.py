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
from typing import Any, Dict

from PIL import Image



def classify_roi_image(image_path: str) -> Dict[str, Any]:
    img = Image.open(image_path).convert('RGB')
    stat = img.resize((16, 16))
    pixels = list(stat.getdata())
    brightness = sum((r + g + b) / 3.0 for r, g, b in pixels) / max(1, len(pixels))
    return {'image_path': str(Path(image_path)), 'brightness': brightness, 'label': 'unknown'}
