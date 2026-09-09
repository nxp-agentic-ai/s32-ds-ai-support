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

"""API action executables for the S32FlashTool GUI (Eclipse RCP).
"""

from nxp.mcp.s32flashtool.impl.actions._gui_launch_build_factory import (
    make_launch_action,
)

__all__ = ["GUI_LAUNCH_ACTION", "GUI_LAUNCH_ACTIONS"]

GUI_LAUNCH_ACTION = make_launch_action("launch")

GUI_LAUNCH_ACTIONS = (
    GUI_LAUNCH_ACTION,    
)
