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

from nxp.mcp.s32flashtool.config.models import S32FlashToolMcpServerConfig

PROMPTS_DIR = Path(__file__).resolve().parent / 'prompts'


def load_file_text(filename: str) -> str:
    path = PROMPTS_DIR / filename
    return path.read_text(encoding='utf-8')


def register_image_processing_prompts(mcp, config: S32FlashToolMcpServerConfig):
    ###
    @mcp.prompt(
        name='image_processing_board_config_overview',
        description='Guidance for using board image tools to inspect jumper and DIP switch configuration from photos.'
    )
    def image_processing_board_config_overview() -> str:
        return load_file_text('image_processing_board_config_overview.md')
    
    @mcp.resource("s32flashtool://prompts/image_processing/board_config_overview")
    def lifecycle_skills_board_config_overview() -> str:
        return load_file_text('image_processing_board_config_overview.md')
    
    ###
    @mcp.prompt(
        name='image_processing_board_photo_guidance',
        description='Guidance for asking the user for a suitable board image for alignment and ROI inspection.'
    )
    def image_processing_board_photo_guidance() -> str:
        return load_file_text('image_processing_board_photo_guidance.md')
    
    @mcp.resource("s32flashtool://prompts/image_processing/board_photo_guidance")
    def lifecycle_skills_board_photo_guidance() -> str:
        return load_file_text('image_processing_board_photo_guidance.md')
    ###

    @mcp.prompt(
        name='image_processing_check_board_against_expected',
        description='Workflow for comparing a board photo against an expected configuration using semantic ROI tools.'
    )
    def image_processing_check_board_against_expected() -> str:
        return load_file_text('image_processing_check_board_against_expected.md')
    @mcp.resource("s32flashtool://prompts/image_processing/check_board_against_expected")
    def lifecycle_skills_check_board_against_expected() -> str:
        return load_file_text('image_processing_check_board_against_expected.md')
    ###

    @mcp.prompt(
        name='image_processing_boot_mode_assistant',
        description='Guidance for combining visual board configuration checks with boot and flashing prerequisites.'
    )
    def image_processing_boot_mode_assistant() -> str:
        return load_file_text('image_processing_boot_mode_assistant.md')
    @mcp.resource("s32flashtool://prompts/image_processing/boot_mode_assistant")
    def lifecycle_skills_boot_mode_assistant() -> str:
        return load_file_text('image_processing_boot_mode_assistant.md')
    ###

    @mcp.prompt(
        name='image_processing_connect_doc_and_visual_config',
        description='Guidance for linking s32flashtool documentation requirements with image-based board configuration analysis.'
    )
    def image_processing_connect_doc_and_visual_config() -> str:
        return load_file_text('image_processing_connect_doc_and_visual_config.md')
    @mcp.resource("s32flashtool://prompts/image_processing/connect_doc_and_visual_config")
    def lifecycle_skills_connect_doc_and_visual_config() -> str:
        return load_file_text('image_processing_connect_doc_and_visual_config.md')
    ###

    @mcp.prompt(
        name='image_processing_reporting_policy',
        description='Policy for how agents should report detected configuration, uncertainty, and certification when board image tools are used.'
    )
    def image_processing_reporting_policy() -> str:
        return load_file_text('image_processing_reporting_policy.md')
    @mcp.resource("s32flashtool://prompts/image_processing/reporting_policy")
    def lifecycle_skills_reporting_policy() -> str:
        return load_file_text('image_processing_reporting_policy.md')
    ###
