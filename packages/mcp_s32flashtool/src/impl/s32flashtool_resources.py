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

import base64
import json
import logging
from pathlib import Path
from nxp.mcp.s32flashtool.config.models import S32FlashToolMcpServerConfig
from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME, MCP_SERVER_VERSION, MCP_SERVER_DESCRIPTION


__all__ = ["register_s32flashtool_resources"]


_logger = logging.getLogger(MCP_SERVER_NAME)

RESOURCES_DIR = Path(__file__).parent / "resources"

def load_resource_text(path : str) -> str:
    prompt_path = RESOURCES_DIR / path
    _logger.info("load resource from " + str(prompt_path))
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}"
        )
    return prompt_path.read_text(encoding="utf-8")

def register_s32flashtool_resources(mcp, config : S32FlashToolMcpServerConfig):

    @mcp.resource(
        uri="s32flashtool://links/s32flashtool-nxp-webpage",
        name="NXP official S32FlashTool webpage",
    )
    def resource_nxp_webpage():
        return {
            "title": "NXP official S32FlashTool webpage",
            "url": "https://www.nxp.com/design/design-center/software/automotive-software-and-tools/s32-design-studio-ide/s32-flash-tool-for-s32-platform:S32FT-S32PLATFORM",
            "summary": "General information for S32FlashTool."
        }  
    
    @mcp.resource(
        uri="s32flashtool://docs/naming_convention",
        name="Naming convention",
        mime_type="text/plain"
    )
    def resource_naming_convention() -> str:
        """
        Gives hints about names, name equivalents in the S32FlashTool documentation, command line, etc.
        """        
        return load_resource_text("s32flashtool_naming_convention.md")

    @mcp.resource(
        uri="s32flashtool://skills/index",
        name="S32FlashTool skill pack index",
        mime_type="application/json",
    )
    def resource_skill_pack_index() -> dict:
        """Machine-readable routing index for the s32flashtool skill pack.

        Returns the parsed contents of the bundled INDEX.json: load order,
        routing hints, per-skill primary actions, destructive flag and
        confirmation phrase, mode-selection metadata, and URIs to the
        underlying SKILL.md files. An agent can use this to route a user
        request without reading the workflow-index Markdown.
        """
        return json.loads(load_resource_text("INDEX.json"))
