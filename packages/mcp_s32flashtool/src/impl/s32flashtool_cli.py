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

"""Lightweight S32FlashTool command-line runner.

This client executes a fully formed S32FlashTool command string (as produced by
``build_s32flashtool_command_string``) or a raw command line, and returns a
uniform result dictionary. It is intentionally minimal so it can be reused by
the search-first action handlers without depending on the higher-level tool
wrappers.
"""

from __future__ import annotations

import asyncio
import os
import shlex
from logging import Logger
from pathlib import Path
from typing import Any, Optional

from nxp.mcp.s32flashtool.impl.constants import CLI_EXE_NAME


__all__ = ["FlashToolClient_CLI"]


# The CLI executable name is shared via the dependency-free constants module so
# other modules can reference it without importing this client (which would risk
# a circular import).
_EXE_NAME = CLI_EXE_NAME

# On Windows (posix=False), shlex leaves surrounding quotes on tokens
# and does not process escaped quotes. Strip a single matching pair of
# surrounding single or double quotes, then unescape any occurrences of
# that same quote inside the token, so the executable-name comparison
# and the spawned argv see the bare path (including paths that legitimately
# contain quote characters, e.g. "path with \"quotes\""). On POSIX,
# shlex.split(posix=True) already handled all unquoting/unescaping.
def _unquote_windows_token(token: str) -> str:
    if len(token) >= 2 and token[0] in ('"', "'") and token[-1] == token[0]:
        quote = token[0]
        inner = token[1:-1]
        return inner.replace("\\" + quote, quote)
    return token

class FlashToolClient_CLI:
    """Run S32FlashTool CLI executable from a resolved installation folder."""

    def __init__(self, sft_folder: str = "", logger: Optional[Logger] = None) -> None:
        self.sft_folder = sft_folder
        self.logger = logger

    def _log(self, message: str) -> None:
        if self.logger is not None:
            self.logger.debug(message)

    async def run(self, command_string: Optional[str] = None) -> dict[str, Any]:
        """Execute a command string and capture stdout/stderr.

        The command string is expected to already contain the full path to
        S32FlashTool CLI executable (as built by the CLI builder). When only arguments are
        provided, S32FlashTool CLI executable is resolved from ``sft_folder/bin``.
        """

        try:
            if not command_string or not command_string.strip():
                raise ValueError("command_string must be a non-empty command line")

            # Split the command string with platform-appropriate rules. On
            # Windows, command lines use backslash paths, so posix=False avoids
            # shlex treating backslashes as escape characters. On POSIX, use the
            # default posix=True so that quoting/escaping is handled correctly
            # and matches how build_s32flashtool_command_string quotes via
            # shlex.join. shlex already strips quotes as part of splitting, so
            # tokens must NOT be stripped again afterwards - doing so would
            # corrupt arguments that legitimately contain quote characters.
            is_windows = os.name == "nt"
            argv = shlex.split(command_string, posix=not is_windows)

            # Only unquote on Windows; POSIX tokens are already fully unquoted by shlex.
            if is_windows:
                argv = [_unquote_windows_token(token) for token in argv]

            # If the first token is not S32FlashTool CLI executable, resolve it
            # from the installation bin folder and treat the whole string as
            # arguments.
            first = argv[0] if argv else ""
            if not first.lower().endswith(_EXE_NAME.lower()):
                expath = Path(self.sft_folder) / "bin" / _EXE_NAME
                argv = [str(expath), *argv]

            self._log(f"FT CLI execute: {command_string}")

            process = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path(self.sft_folder) / "bin") if self.sft_folder else None,
            )

            stdout, stderr = await process.communicate()

            result_stdout = stdout.decode("utf-8", errors="replace").strip()
            result_stderr = stderr.decode("utf-8", errors="replace").strip()
            status = "ok" if process.returncode == 0 else "error"
            return {
                "status": status,
                "exit_code": process.returncode,
                "output": result_stdout or result_stderr,
                "command": command_string,
            }
        except Exception as exc:  # defensive: surface as uniform error result
            if self.logger is not None:
                self.logger.exception("Failed to execute S32FlashTool CLI command")
            return {
                "status": "error",
                "exit_code": -1,
                "output": f"Exception: {exc}",
                "command": command_string,
            }
