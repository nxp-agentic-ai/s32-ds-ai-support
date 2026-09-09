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

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


ROIType = Literal['dip_switch', 'jumper', 'connector', 'testpoint']


class RegionOfInterest(BaseModel):
    id: str
    label: str
    type: ROIType
    bbox: List[int]
    expected_states: List[str] = Field(default_factory=list)


ROIRegion = RegionOfInterest


class TemplateModel(BaseModel):
    board_id: str
    reference_image: str
    landmarks: List[dict] = Field(default_factory=list)
    regions_of_interest: List[RegionOfInterest] = Field(default_factory=list)


BoardTemplate = TemplateModel


class AnalyzeBoardRequest(BaseModel):
    image_path: str
    board_id: str
    expected_config: Dict[str, str]


class ROIExampleRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    board_id: str
    roi_id: str
    roi_label: str = Field(alias='label')
    component_type: str
    state: str
    image_path: str

    @property
    def label(self) -> str:
        return self.roi_label
