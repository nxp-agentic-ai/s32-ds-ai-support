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
from typing import Optional

from pydantic import BaseModel

from nxp.mcp.s32flashtool.config.models import S32FlashToolMcpServerConfig

from .dataset_store import BoardDatasetStore
from .faiss_store import FaissStore
from .runtime_rules import analyze_semantic_board, get_board_photo_hints
from .template_store import TemplateStore
from .vision.sample_data import generate_sample_board_assets

from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)

BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / 'templates'
EXAMPLES_DIR = BASE_DIR / 'examples'
DATA_DIR = BASE_DIR / 'data'
BOARDS_DIR = BASE_DIR / 'boards'

templates = TemplateStore(TEMPLATES_DIR)
faiss_store = FaissStore(DATA_DIR / 'faiss')
dataset = BoardDatasetStore(BOARDS_DIR)


class CreateBoardRequest(BaseModel):
    board_id: str
    name: str
    reference_image_path: str


def register_image_processing_tools(mcp, config: S32FlashToolMcpServerConfig):
    @mcp.tool(
        name='board_image_health',
        description='Health check for the integrated board image processing module.'
    )
    def board_image_health() -> dict:
        return {'status': 'ok', 'service': 'board-config-mcp'}

    @mcp.tool(
        name='board_image_list_boards',
        description='List all documented boards available in the image-processing dataset.'
    )
    def board_image_list_boards() -> dict:
        return {'boards': dataset.list_boards()}

    @mcp.tool(
        name='board_image_get_board',
        description='Load one documented board definition, including ROI metadata and resolved reference image path.'
    )
    def board_image_get_board(board_id: str) -> dict:
        return dataset.get_board(board_id)

    @mcp.tool(
        name='board_image_create_board',
        description='Create a new documented board entry from a board id, display name, and reference image path.'
    )
    def board_image_create_board(request: dict) -> dict:
        req = CreateBoardRequest.model_validate(request)
        result = dataset.create_board(req.board_id, req.name, req.reference_image_path)
        return {'status': 'ok', **result}

    @mcp.tool(
        name='board_image_export_template',
        description='Export a documented board into the template format used by the image-processing analyzer.'
    )
    def board_image_export_template(board_id: str) -> dict:
        out = dataset.export_board_to_template(board_id, TEMPLATES_DIR)
        return {'status': 'ok', 'template_path': str(out)}

    @mcp.tool(
        name='board_image_get_photo_hints',
        description='Return guidance for how to take a useful board photo for later alignment and semantic analysis.'
    )
    def board_image_get_photo_hints(board_id: str, mode: str = 'auto') -> dict:
        board = dataset.get_board(board_id)
        hints = get_board_photo_hints(board, mode=mode)
        return {
            'board_id': board_id,
            'mode': mode,
            'hints': hints,
        }

    @mcp.tool(
        name='board_image_detect_config',
        description="""
        Analyze a board image using the documented board definition and return detected semantic 
        ROI states without enforcing an expected configuration.
        Hint: For board setup questions (serial boot, jumper/switch positions, boot mode), first consult the matching board PDF in the S32FlashTool examples folder if available. 
        Do not assume the image-analysis expected configuration is the official hardware setup. 
        Use the board PDF as the authoritative source, then compare the detected image configuration against it.
        """
    )
    def board_image_detect_config(image_path: str, board_id: str, debug_output_dir: Optional[str] = None) -> dict:
        board = dataset.get_board(board_id)
        logger.info('MCP board_image_detect_config board_id=%s image=%s', board_id, image_path)
        return analyze_semantic_board(board, image_path, expected_config={}, debug_output_dir=debug_output_dir, align_to_reference=True)

    @mcp.tool(
        name='board_image_check_config',
        description="""
        Analyze a board image, return the detected semantic board configuration, 
        compare it against an expected configuration, and provide certification status plus reason.
        Hint: For board setup questions (serial boot, jumper/switch positions, boot mode), first consult the matching board PDF in the S32FlashTool examples folder if available. 
        Do not assume the image-analysis expected configuration is the official hardware setup. 
        Use the board PDF as the authoritative source, then compare the detected image configuration against it.
        """
    )
    def board_image_check_config(image_path: str, board_id: str, expected_config: Optional[dict] = None, debug_output_dir: Optional[str] = None) -> dict:
        board = dataset.get_board(board_id)
        logger.info('MCP board_image_check_config board_id=%s image=%s', board_id, image_path)
        return analyze_semantic_board(board, image_path, expected_config or {}, debug_output_dir=debug_output_dir, align_to_reference=True)

    @mcp.tool(
        name='board_image_analyze_semantic_config',
        description="""
        Run semantic board analysis for a documented board and return ROI results, 
        detected configuration summary, and certification fields.
        Hint: For board setup questions (serial boot, jumper/switch positions, boot mode), first consult the matching board PDF in the S32FlashTool examples folder if available. 
        Do not assume the image-analysis expected configuration is the official hardware setup. 
        Use the board PDF as the authoritative source, then compare the detected image configuration against it.
        """
    )
    def board_image_analyze_semantic_config(image_path: str, board_id: str, expected_config: Optional[dict] = None) -> dict:
        board = dataset.get_board(board_id)
        return analyze_semantic_board(board, image_path, expected_config or {})

    @mcp.tool(
        name='board_image_generate_sample_image',
        description='Generate synthetic sample board images and ROI example assets for local testing of the image-processing workflow.'
    )
    def board_image_generate_sample_image(output_dir: Optional[str] = None) -> dict:
        out_dir = Path(output_dir) if output_dir else EXAMPLES_DIR
        assets = generate_sample_board_assets(out_dir)
        return {'status': 'ok', **{k: str(v) for k, v in assets.items()}}
