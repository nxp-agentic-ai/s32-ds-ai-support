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

import logging

from nxp.mcp.compiler.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


def register_info_resource(server, config, install, tool_flags: dict | None = None) -> None:
    if tool_flags is None:
        tool_flags = {}

    @server.resource(uri="compiler://info")
    def info() -> str:
        lines = [
            "mcp_server: compiler",
            f"status: {'ok' if install else 'ERROR: no install found'}",
            "",
        ]

        if not install:
            lines.append("=== Toolchains ===")
            lines.append("ERROR: No S32DS compiler install found on this host")
            lines.append("Tip: set toolchain_path in config or install S32DS under C:/NXP")
            return "\n".join(lines)

        lines.append("=== Install ===")
        lines.append(f"{'path':<20} {install.path}")
        lines.append(f"{'version':<20} {install.version_label}")
        lines.append(f"{'base_dir':<20} {install.base_dir}")
        lines.append(f"{'compile_output_dir':<20} {install.compile_output_dir}")
        lines.append("")

        if tool_flags.get("gcc"):
            lines.append("=== GCC Toolchain ===")
            lines.append(f"{'root':<20} {install.gcc_toolchain or 'ERROR: not found'}")
            lines.append(f"{'exists':<20} {'SUCCESS' if install.gcc_toolchain.exists() else 'ERROR'}")
            lines.append(f"{'version_glob':<20} {install.gcc_version_glob}")
            lines.append(f"{'bin_glob':<20} {install.gcc_bin_glob}")
            lines.append("")

        if tool_flags.get("lax"):
            lines.append("=== LAX Toolchain ===")
            lines.append(f"{'root':<20} {install.lax_toolchain or 'ERROR: not found'}")
            lines.append(f"{'exists':<20} {'SUCCESS' if install.lax_toolchain.exists() else 'ERROR'}")
            lines.append(f"{'version_glob':<20} {install.lax_version_glob}")
            lines.append(f"{'bin_glob':<20} {install.lax_bin_glob}")
            lines.append("")

        if tool_flags.get("lax_simulator"):
            lines.append("=== LAX Simulator ===")
            lines.append(f"{'root':<20} {install.lax_simulator or 'ERROR: not found'}")
            lines.append(f"{'exists':<20} {'SUCCESS' if install.lax_simulator.exists() else 'ERROR'}")
            lines.append("")

        if tool_flags.get("spt"):
            lines.append("=== SPT3.8 Toolchain ===")
            lines.append(f"{'root':<20} {install.spt_toolchain or 'ERROR: not found'}")
            lines.append(f"{'exists':<20} {'SUCCESS' if install.spt_toolchain.exists() else 'ERROR'}")
            lines.append(f"{'version_glob':<20} {install.spt_version_glob}")
            lines.append(f"{'bin_glob':<20} {install.spt_bin_glob}")
            lines.append("")

        return "\n".join(lines)

