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

"""Public manifest for S32DS action executables.

``STATIC_ACTIONS`` are the actions served locally by this MCP server (they do
not depend on the S32DS IDE being up). Discovered IDE methods are synthesized
dynamically at runtime and merged on top - see
:mod:`nxp.mcp.s32ds.actions.dynamic`.

Extension point: to expose a new static action, implement it as an
``ActionExecutable`` and add it to ``STATIC_ACTIONS`` below.
"""

from .start_tool import START_TOOL_ACTION

STATIC_ACTIONS = (START_TOOL_ACTION,)

__all__ = ["STATIC_ACTIONS", "START_TOOL_ACTION"]
