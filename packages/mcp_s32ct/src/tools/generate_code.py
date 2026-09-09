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

"""``generate_code`` - headless code generation from an existing .mex."""
import logging
from typing import Literal, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import S32CTContext, generate_code_impl

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_generate_code_tool(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    @server.tool(
        name="generate_code",
        description=(
            "Headless code generation in S32 Configuration Tools for a single tool "
            "of an existing .mex project. tool_name in {Pins, Clocks, Peripherals, "
            "DCD, IVT, eFUSE, GTM, QuadSPI, FFC}. export_kind in {ExportAll, "
            "ExportSrc, ExportHTML, ExportCSV, ExportRegisters, ExportMEX}. "
            "Portable across both S32CT distributions (standalone `desktop` and "
            "`integrated_s32ds`); the right launcher prefix is selected from the "
            "active server context. See the `s32ct-distributions` skill."
        ),
    )
    def generate_code(
        project_path: str,
        tool_name: Literal["Pins", "Clocks", "Peripherals", "DCD", "IVT", "eFUSE", "GTM", "QuadSPI", "FFC"],
        output_dir: str,
        export_kind: Literal[
            "ExportAll", "ExportSrc", "ExportHTML", "ExportCSV", "ExportRegisters", "ExportMEX"
        ] = "ExportAll",
        enable_if_disabled: bool = True,
        sdk_version: Optional[str] = None,
        s32ct_launcher: Optional[str] = None,
        launcher_ini: Optional[str] = None,
    ) -> str:
        try:
            return generate_code_impl(
                ctx,
                project_path=project_path,
                tool_name=tool_name,
                output_dir=output_dir,
                export_kind=export_kind,
                enable_if_disabled=enable_if_disabled,
                sdk_version=sdk_version,
                s32ct_launcher=s32ct_launcher,
                launcher_ini=launcher_ini,
            )
        except Exception as e:
            _logger.exception("generate_code failed")
            return f"generate_code error: {e}"
