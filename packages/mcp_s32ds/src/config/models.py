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

from dataclasses import dataclass, field
from typing import Dict, Any
from nxp.mcp.shared.config.models import BaseMcpServerConfig


@dataclass(slots=True)
class CorpusEntry:
	index_path: str = ""
	metadata_path: str = ""


@dataclass(slots=True)
class S32dsSettings:
	model_path: str = ""
	corpora: Dict[str, CorpusEntry] = field(default_factory=dict)
	s32ds_rest_port: int = 8088
	top_k_default: int = 5  # TODO: Need this here?
	min_score_threshold: float = 0.35  # TODO: Need this here?


@dataclass(slots=True)
class S32dsMcpServerConfig(BaseMcpServerConfig):
	"""Full configuration for the S32DS MCP server."""
	settings: S32dsSettings = field(default_factory=S32dsSettings)
