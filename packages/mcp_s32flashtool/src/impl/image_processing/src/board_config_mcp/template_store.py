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
from pathlib import Path
from typing import List

from pydantic import ValidationError

from .schemas import BoardTemplate, ROIRegion


class TemplateStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def template_dir(self, board_id: str) -> Path:
        return self.base_dir / board_id

    def template_path(self, board_id: str) -> Path:
        return self.template_dir(board_id) / "template.json"

    def _template_path(self, board_id: str) -> Path:
        return self.template_path(board_id)

    def save_template(self, template: BoardTemplate):
        path = self.template_path(template.board_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(template.model_dump(), indent=2), encoding="utf-8")
        return path

    def get_template(self, board_id: str) -> BoardTemplate:
        path = self.template_path(board_id)
        if not path.exists():
            raise FileNotFoundError(f"Template not found for board_id={board_id}: {path}")
        return BoardTemplate.model_validate_json(path.read_text(encoding="utf-8"))

    def load_template(self, board_id: str) -> BoardTemplate:
        return self.get_template(board_id)

    def list_templates(self) -> List[BoardTemplate]:
        items: List[BoardTemplate] = []
        for p in self.base_dir.glob("*/template.json"):
            try:
                items.append(BoardTemplate.model_validate_json(p.read_text(encoding="utf-8")))
            except (OSError, ValidationError, ValueError):
                continue
        return sorted(items, key=lambda x: x.board_id)

    def add_roi(self, board_id: str, roi: dict) -> BoardTemplate:
        template = self.get_template(board_id)
        template.regions_of_interest.append(ROIRegion.model_validate(roi))
        self.save_template(template)
        return template
