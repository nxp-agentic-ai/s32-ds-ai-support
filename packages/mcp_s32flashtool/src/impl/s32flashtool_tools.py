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
import asyncio

from typing import Any, List, Dict, Literal, Optional, get_args

# NOTE: Import TypedDict from typing_extensions rather than typing.
# On Python < 3.12, pydantic (used by FastMCP to build tool schemas) rejects
# typing.TypedDict and raises PydanticUserError. typing_extensions provides a
# backport that pydantic accepts on all supported Python versions.
from typing_extensions import TypedDict


from nxp.mcp.s32flashtool.impl.s32flashtool_utils import *

from nxp.mcp.s32flashtool.config.models import S32FlashToolMcpServerConfig
from nxp.mcp.s32flashtool.metadata.server import MCP_SERVER_NAME

logger = logging.getLogger(MCP_SERVER_NAME)


FTCmd = Literal["fread", "fprogram", "fcrc", "fverify", "fwrite", "mcuid", "boot", "ferase", "ping"]
ALLOWED_FTCMD = set(get_args(FTCmd)) - {""}

GUIDANCE_NO_DEFAULTS = """
Discovery and safety notes (no values are guessed for you):
- There are NO hardware-specific defaults for target, algorithm, interface, or port. Supply them explicitly.
- Discover valid target binaries: s32flashtool_list_available_platform_files(base_folder, bin_type="target").
- Discover valid flash algorithms: s32flashtool_list_available_platform_files(base_folder, bin_type="flash").
- Discover available ports/endpoints: s32flashtool_execute_expert(s32flashtool_folder, list_ports=True).
- Confirm device/algorithm/interface support first: s32flashtool_list_available_platform_files(base_folder, bin_type="supported").
- Always pass absolute paths for target, algorithm, and file_path.
- Never guess a COM port or MCU family when the user has not provided one; ask or discover instead.
""".strip()

class FlashToolClient:
    def __init__(self, base_folder=""):
        self.base_folder = base_folder
        self.connected = False


    async def run(self,
            target: Optional[str] = None,
            algorithm: Optional[str] = None,
            interface: Optional[str] = None,
            port: Optional[str] = None,
            list_ports: bool = False,
            ftcmd: Optional[FTCmd] = None,
            boot: bool = False,
            addr: Optional[str] = None,
            size: Optional[str] = None,
            file_path: Optional[str] = None,
            entrypoint: Optional[str] = None,
            extra_args: Optional[List[str]] = None,
            timeout: Optional[int] = 300,
            preview_only: bool = False,
            confirmed_by_user: bool = False,
        ):
        """
        Generic S32FlashTool command wrapper
        """

        if self.connected:
            return
        self.connected = True

        try:
            expath = Path(self.base_folder) / "bin" / "S32FlashTool.exe"
            logger.info(f"FT execute: {expath}")

            if not expath.exists():
                raise FileNotFoundError(f"s32flashtool.exe not found at {expath}")


            # Runtime validation (VERY important for MCP)
            if ftcmd and ftcmd not in ALLOWED_FTCMD:
                raise ValueError(f"Unsupported ftcmd: {ftcmd}")

            if boot and not file_path:
                raise ValueError("boot requires 'file_path' to be specified")

            if ftcmd in {"fread", "fprogram", "fcrc", "fverify"} and not addr:
                raise ValueError(f"{ftcmd} requires 'addr'")

            cmd = [str(expath)]

            # Target and algorithm
            if target:
                cmd += ["-t", str(Path(target))]
            if algorithm:
                cmd += ["-a", str(Path(algorithm))]

            # Interface and port
            if interface:
                cmd += ["-i", interface]
            if port:
                cmd += ["-p", port]
            elif list_ports:
                cmd += ["-p", "?"]

            # Actions
            if ftcmd:
                cmd.append("-" + ftcmd)

            if boot:
                if not addr:
                    raise ValueError(f"-boot requires 'addr'")
                cmd += ["-boot", str(Path(file_path))]

            # Addressing
            if addr:
                cmd += ["-addr", addr]
            if size:
                cmd += ["-size", size]

            # File based operations
            if file_path and not boot:
                cmd += ["-f", str(Path(file_path))]

            # Boot entrypoint
            if entrypoint:
                cmd += ["-entrypoint", entrypoint]

            # Extra raw args if needed
            if extra_args:
                cmd.extend(extra_args)
            dangerous = _is_dangerous_operation(ftcmd, boot)
            command_preview = " ".join(map(str, cmd))

            if dangerous and preview_only:
                return {
                    "status": "preview",
                    "exit_code": -1,
                    "output": "Preview only. Destructive operation requires explicit user confirmation before execution.",
                    "command": command_preview,
                }

            if dangerous and not confirmed_by_user:
                return {
                    "status": "blocked",
                    "exit_code": -1,
                    "output": "Execution blocked. Destructive operation requires explicit user confirmation.",
                    "command": command_preview,
                }

            # Execute
            logger.info("Executing: %s", command_preview)

            process = await asyncio.create_subprocess_exec(
                *map(str, cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path(self.base_folder) / "bin")
            )

            # Wait for the process to complete and capture output
            stdout, stderr = await process.communicate()

            # Decode the output
            result_stdout = stdout.decode('utf-8', errors='replace').strip()
            result_stderr = stderr.decode('utf-8', errors='replace').strip()

            status = "ok" if process.returncode == 0 else "error"
            return {
                "status": status,
                "exit_code": process.returncode,
                "output": result_stdout or result_stderr,
                "command": command_preview,
            }
        except Exception as e:
            logger.exception("Failed to execute external process")
            return {
                "status": "error",
                "exit_code": -1,
                "output": f"Exception: {str(e)}",
            }
        finally:
            self.connected = False

    async def simple_execute(self):
        if self.connected:
            return
        self.connected = True
        try:
            # Execute the external executable asynchronously
            expath = str(Path(self.base_folder) / "bin" / "S32FlashTool.exe")
            logger.info("FT execute " + expath)
            process = await asyncio.create_subprocess_exec(
                str(expath),  # Path to your executable
                # "--config", "path/to/config.cfg",  # Add your arguments here
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path(self.base_folder) / "bin")
            )

            # Wait for the process to complete and capture output
            stdout, stderr = await process.communicate()

            # Decode the output
            result_stdout = stdout.decode('utf-8', errors='replace').strip()
            result_stderr = stderr.decode('utf-8', errors='replace').strip()

            status = "ok" if process.returncode == 0 else "error"
            return {
                "status": status,
                "exit_code": process.returncode,
                "output": result_stdout or result_stderr,
            }

        except Exception as e:
            logger.exception("Failed to execute external process")
            return {
                "status": "error",
                "exit_code": -1,
                "output": f"Exception: {str(e)}",
            }

        finally:
            self.connected = False

def _is_dangerous_operation(ftcmd: Optional[FTCmd], boot: bool = False) -> bool:
    return bool(boot) or ftcmd in {"fprogram", "ferase", "fwrite"}


# ---------------------------------------------------------------------------
# Stable result envelope returned by every S32FlashTool MCP tool.
#
# Design notes (agentic-consumer oriented):
# - Tools return a NATIVE dict (ToolResult), not a pre-serialized JSON string.
#   FastMCP serializes the dict into structured content, so the client receives
#   a parsed object directly instead of a JSON string it must decode a second
#   time.
# - The shape is UNIFORM across success, error, preview, and blocked outcomes,
#   so a consumer can always branch on the same keys (never array-or-object).
# - Human prose lives under ``message``; machine-usable payloads live under
#   ``data``. There is no content sniffing/guessing.
# ---------------------------------------------------------------------------
Status = Literal["ok", "error", "preview", "blocked"]


class ToolResult(TypedDict, total=False):
    status: Status          # machine-checkable outcome
    exit_code: int          # process/return code (-1 when no process ran)
    message: str            # human-readable summary (prose)
    data: Any               # machine-usable payload (stdout, file list, ...)
    command: str            # previewed/executed command line, when relevant


def _envelope(
    status: Status,
    *,
    exit_code: int = 0,
    message: str = "",
    data: Any = None,
    command: Optional[str] = None,
) -> ToolResult:
    """Build the uniform tool-result envelope as a native dict."""
    result: ToolResult = {"status": status, "exit_code": exit_code}
    if message:
        result["message"] = message
    if data is not None:
        result["data"] = data
    if command is not None:
        result["command"] = command
    return result


def _normalize_run_result(result: Any) -> ToolResult:
    """Map a FlashToolClient.run()/simple_execute() dict onto the envelope.

    The internal client returns {status, exit_code, output[, command]}. Here
    ``output`` is placed under ``data`` (machine payload); for non-ok outcomes
    it is also surfaced as ``message`` (human prose). Non-dict results are
    wrapped defensively so the contract always holds.
    """
    if not isinstance(result, dict):
        return _envelope("ok", data=result)

    status: Status = result.get("status", "ok")
    exit_code = result.get("exit_code", 0)
    output = result.get("output", "")
    command = result.get("command")

    if status in ("error", "preview", "blocked"):
        return _envelope(status, exit_code=exit_code, message=output, data=output, command=command)
    return _envelope(status, exit_code=exit_code, data=output, command=command)


def _missing_parameter(name: str, hint: str) -> ToolResult:
    """Uniform error envelope for a missing required parameter."""
    return _envelope(
        "error",
        exit_code=-1,
        message=f"Missing required parameter '{name}'. Hint: {hint}",
    )


def register_s32flashtool_tools(mcp, config : S32FlashToolMcpServerConfig):
    """Register tools with the MCP server."""

    @mcp.tool(
    name="execute_expert",
    description=("""
        Run any S32FlashTool.exe command-line operation (EXPERT / low-level escape hatch). Returns a
        uniform envelope {status, exit_code, message, data, command} where status is
        "ok"/"error"/"preview"/"blocked". S32FlashTool.exe is resolved from <s32flashtool_folder>/bin.

        Use this when a higher-level tool does not cover the operation you need, or when you must pass
        raw CLI flags. For common cases prefer the dedicated tools: upload_file_to_flash (program),
        read_flash (read/dump), compare_crc_to_flash (CRC verify), get_version, and
        list_available_platform_files (discovery).

        Selecting the operation:
        - ftcmd selects the S32FlashTool action and maps to a CLI flag: one of
          fread, fprogram, fcrc, fverify, fwrite, mcuid, boot, ferase, ping (e.g. ftcmd="mcuid" -> -mcuid).
        - list_ports=True issues "-p ?" to enumerate available ports/endpoints for the given interface.
        - file_path maps to "-f <file>"; addr maps to "-addr"; size maps to "-size"; entrypoint maps to
          "-entrypoint"; extra_args are appended verbatim for flags not modeled here.
        - addr and size must be numeric-like (e.g. hexadecimal "0x00000000").

        Destructive-operation safety (ftcmd in {fprogram, ferase, fwrite} or boot=True):
        - preview_only=True returns the exact command line without executing (status:"preview").
        - Execution requires confirmed_by_user=True AND preview_only=False; otherwise it is blocked
          (status:"blocked"). Always show the previewed command to the user and obtain confirmation first.

        Returns status:"error" if the installation, target, algorithm, or file_path is invalid or
        not found.

        Key parameters (no values are guessed for you):
        - port: serial/CAN/Ethernet endpoint, e.g. COM3, COM7 on Windows. Discover with list_ports=True.
        - target: absolute path to the target binary, e.g. <s32flashtool_folder>/targets/S32N5x.bin.
        - algorithm: absolute path to the flash algorithm under <s32flashtool_folder>/flash/, matching the device.
        - Always use absolute paths for target, algorithm, and file_path.
        """
        + GUIDANCE_NO_DEFAULTS
    )
    )
    async def s32flashtool_execute_expert(
            s32flashtool_folder: str,
            target: Optional[str] = None,
            algorithm: Optional[str] = None,
            interface: Optional[Literal["uart", "can", "ethernet"]] = None,
            port: Optional[str] = None,
            list_ports: bool = False,
            ftcmd: Optional[FTCmd] = None,
            boot: bool = False,
            addr: Optional[str] = None,
            size: Optional[str] = None,
            file_path: Optional[str] = None, #filename, full path
            entrypoint: Optional[str] = None,
            extra_args: Optional[List[str]] = None,
            timeout: Optional[int] = 300,
            preview_only: bool = False,
            confirmed_by_user: bool = False,
        ) -> ToolResult:
        """
        Executes a S32FlashTool operation in the given folder with the given parameters.
        """
        try:
            logger.info("s32flashtool_execute_expert in %s", s32flashtool_folder)
            validate_s32flashtool_installation(s32flashtool_folder)
            validate_numeric_like(addr, "addr")
            validate_numeric_like(size, "size")
            if target:
                target = resolve_relative_to_installation(s32flashtool_folder, target)
                validate_existing_file(target, "target")
            if algorithm:
                algorithm = resolve_relative_to_installation(s32flashtool_folder, algorithm)
                validate_existing_file(algorithm, "algorithm")
            if file_path:
                validate_existing_file(file_path, "file_path")
            ft = FlashToolClient(s32flashtool_folder)

            result = await ft.run(
                target=target,
                algorithm=algorithm,
                interface=interface,
                port=port,
                list_ports=list_ports,
                ftcmd=ftcmd,
                boot=boot,
                addr=addr,
                size=size,
                file_path=file_path,
                entrypoint=entrypoint,
                extra_args=extra_args,
                timeout=timeout,
                preview_only=preview_only,
                confirmed_by_user=confirmed_by_user,
            )

            return _normalize_run_result(result)

        except Exception as e:
            return _envelope("error", exit_code=-1, message=f"S32FlashTool is not reachable or other error: {e}")


    @mcp.tool(
    name="upload_file_to_flash",
    description=("""
        Program (write) a binary file into device flash via S32FlashTool.exe (-fprogram). DESTRUCTIVE.

        Returns a uniform envelope {status, exit_code, message, data, command}; with the default
        preview_only=True it returns status:"preview" with the exact CLI in ``command`` WITHOUT touching
        the device. Returns status:"error" on missing/invalid parameters or a missing installation.

        Use this as the primary tool to flash an image to a board. It always runs the fprogram action,
        so ftcmd is not needed.

        Two-step safety protocol (required):
        1. Call with preview_only=True (default) and show the returned command line to the user.
        2. After explicit user approval, call again with preview_only=False AND confirmed_by_user=True
           to actually program. Execution is blocked otherwise.

        Before flashing, ask the user whether the board is in serial boot mode; if not, provide the
        serial-boot setup hints for the board. If a different flash algorithm was used previously, ask
        the user to restart the board in serial boot. Consult the matching
        supported_<platform>_devices.txt (bin_type="supported" via list_available_platform_files)
        to confirm device/algorithm compatibility - do not guess it.

        Required parameters: s32flashtool_folder, target, algorithm, interface, port, addr (hex start
        address, e.g. 0x00000000), and file_path (absolute path to the image). size is optional.
        file_path maps to "-f <file>". Use absolute paths throughout.

        Key parameters:
        - port: serial/CAN/Ethernet endpoint, e.g. COM3, COM7 on Windows. Discover with
          s32flashtool_execute_expert(list_ports=True) if unknown.
        - target: absolute path to the target binary, e.g. <s32flashtool_folder>/targets/S32N5x.bin.
        - algorithm: absolute path under <s32flashtool_folder>/flash/, matching the device.
        """
        + GUIDANCE_NO_DEFAULTS
    )
    )
    async def s32flashtool_upload_file_to_flash(
            s32flashtool_folder: str,
            target: Optional[str] = None,
            algorithm: Optional[str] = None,
            interface: Optional[Literal["uart", "can", "ethernet"]] = None,
            port: Optional[str] = None,
            addr: Optional[str] = None,
            file_path: Optional[str] = None,
            size: Optional[str] = None,
            extra_args: Optional[List[str]] = None,
            timeout: Optional[int] = 300,
            preview_only: bool = True,
            confirmed_by_user: bool = False,
        ) -> ToolResult:
        """
        Executes a S32FlashTool operation in the given folder with the given parameters.
        """
        try:
            logger.info("s32flashtool_upload_file_to_flash in %s", s32flashtool_folder)
            validate_s32flashtool_installation(s32flashtool_folder)
            if not target:
                return _missing_parameter("target", "Call s32flashtool_list_available_platform_files(base_folder, bin_type='target') to list valid target binaries.")
            if not algorithm:
                return _missing_parameter("algorithm", "Call s32flashtool_list_available_platform_files(base_folder, bin_type='flash') to list valid flash algorithms.")
            if not interface:
                return _missing_parameter("interface", "Specify how the board is connected: uart, can, or ethernet.")
            if not port:
                return _missing_parameter("port", "Call s32flashtool_execute_expert with list_ports=True to discover available ports/endpoints.")
            if not addr:
                return _missing_parameter("addr", "Provide the flash start address as a hexadecimal string like 0x00000000.")
            if not file_path:
                return _missing_parameter("file_path", "Provide the absolute path to the binary file to program.")

            validate_numeric_like(addr, "addr")
            validate_numeric_like(size, "size")
            target = resolve_relative_to_installation(s32flashtool_folder, target)
            algorithm = resolve_relative_to_installation(s32flashtool_folder, algorithm)
            validate_existing_file(target, "target")
            validate_existing_file(algorithm, "algorithm")
            validate_existing_file(file_path, "file_path")
            ft = FlashToolClient(s32flashtool_folder)

            result = await ft.run(
                target=target,
                algorithm=algorithm,
                interface=interface,
                port=port,
                ftcmd="fprogram",
                addr=addr,
                size=size,
                file_path=file_path,
                extra_args=extra_args,
                timeout=timeout,
                preview_only=preview_only,
                confirmed_by_user=confirmed_by_user,
            )

            return _normalize_run_result(result)

        except Exception as e:
            return _envelope("error", exit_code=-1, message=f"S32FlashTool is not reachable: {e}")

    @mcp.tool(
    name="compare_crc_to_flash",
    description=(  """
        Verify flash contents by CRC via S32FlashTool.exe (-fcrc). Requests a CRC over a flash region
        on the device and compares it against the CRC computed from the given file. Read-only / non
        destructive. Returns a uniform envelope {status, exit_code, message, data, command}, or
        status:"error" on missing/invalid parameters or a missing installation. Always runs the fcrc
        action, so ftcmd is not needed.

        Use this as a fast verification step after programming (cheaper than reading back the whole
        region with read_flash).

        Before running, ask the user whether the board is in serial boot mode; if not, provide the
        serial-boot setup hints. If a different flash algorithm was used previously, ask the user to
        restart the board in serial boot.

        IMPORTANT: do not CRC very large regions in one call - S32FlashTool.exe uses a 15s default
        timeout. Split large ranges into smaller chunks.

        Required parameters: s32flashtool_folder, target, algorithm, interface, port, addr (hex start
        address, e.g. 0x00000000), and file_path (absolute path to the file to compare). size is
        optional. file_path maps to "-f <file>". Use absolute paths throughout.

        To inspect the exact command line before running, use s32flashtool_execute_expert(ftcmd="fcrc",
        preview_only=True).
        """
        + GUIDANCE_NO_DEFAULTS
    )
    )
    async def s32flashtool_compare_crc_to_flash(
            s32flashtool_folder: str,
            target: Optional[str] = None,
            algorithm : Optional[str] = None,
            interface: Optional[Literal["uart", "can", "ethernet"]] = None,
            port: Optional[str] = None,
            addr : Optional[str] = None,
            file_path: Optional[str] = None,
            size: Optional[str] = None,
            extra_args: Optional[List[str]] = None,
            timeout: Optional[int] = 300,
        ) -> ToolResult:
        """
        Executes a S32FlashTool operation (fcrc) in the given folder with the given parameters.
        """
        try:
            logger.info("s32flashtool_compare_crc_to_flash in %s", s32flashtool_folder)
            validate_s32flashtool_installation(s32flashtool_folder)
            if not target:
                return _missing_parameter("target", "Call s32flashtool_list_available_platform_files(base_folder, bin_type='target') to list valid target binaries.")
            if not algorithm:
                return _missing_parameter("algorithm", "Call s32flashtool_list_available_platform_files(base_folder, bin_type='flash') to list valid flash algorithms.")
            if not interface:
                return _missing_parameter("interface", "Specify how the board is connected: uart, can, or ethernet.")
            if not port:
                return _missing_parameter("port", "Call s32flashtool_execute_expert with list_ports=True to discover available ports/endpoints.")
            if not addr:
                return _missing_parameter("addr", "Provide the flash start address as a hexadecimal string like 0x00000000.")
            if not file_path:
                return _missing_parameter("file_path", "Provide the absolute path to the comparison file.")

            validate_numeric_like(addr, "addr")
            validate_numeric_like(size, "size")
            target = resolve_relative_to_installation(s32flashtool_folder, target)
            algorithm = resolve_relative_to_installation(s32flashtool_folder, algorithm)
            validate_existing_file(target, "target")
            validate_existing_file(algorithm, "algorithm")
            validate_existing_file(file_path, "file_path")
            ft = FlashToolClient(s32flashtool_folder)

            result = await ft.run(
                target=target,
                algorithm=algorithm,
                interface=interface,
                port=port,
                ftcmd="fcrc",
                extra_args=extra_args,
                size=size,
                addr=addr,
                file_path=file_path,
                timeout=timeout,
            )

            return _normalize_run_result(result)

        except Exception as e:
            return _envelope("error", exit_code=-1, message=f"S32FlashTool is not reachable: {e}")

    @mcp.tool(
    name="read_flash",
    description=(  """
        Read (download) a flash memory region from the device via S32FlashTool.exe (-fread). Read-only /
        non destructive. Returns a uniform envelope {status, exit_code, message, data, command}; when
        file_path is given the data is written there, otherwise it is returned under ``data``. Always
        runs the fread action, so ftcmd is not needed.

        Use this to dump, inspect, back up, or verify flash contents.

        Before running, ask the user whether the board is in serial boot mode; if not, provide the
        serial-boot setup hints. If a different flash algorithm was used previously, ask the user to
        restart the board in serial boot.

        Required parameters: s32flashtool_folder, target, algorithm, interface, port, and addr (hex start
        address, e.g. 0x00000000). size selects how many bytes to read. Optional: binary_output=True maps
        to "-b" (raw binary), file_path maps to "-f <file>" (its parent folder must already exist). Use
        absolute paths throughout.

        To inspect the exact command line before running, use s32flashtool_execute_expert(ftcmd="fread",
        preview_only=True).
        """
        + GUIDANCE_NO_DEFAULTS
    )
    )
    async def s32flashtool_read_flash(
        s32flashtool_folder: str,
        target: Optional[str] = None,
        algorithm: Optional[str] = None,
        interface: Optional[str] = None,
        port: Optional[str] = None,
        addr: Optional[str] = None,
        size: Optional[str] = None,
        binary_output: bool = False,
        file_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        timeout: Optional[int] = 300,
    ) -> ToolResult:
        """
        Uses S32FlashTool.exe from the subfolder bin of the given folder with the given parameters
        and reads from the target flash memory.

        Runs a command-line operation with S32FlashTool.exe.
        The ftcmd parameter is not necessary, as fread is automatically used.

        The binary_output parameter maps to the command line option '-b'.
        The file_path parameter maps to the command line option '-f <filename>'.

        Requires target, flash memory algorithm, interface, port, address, size,
        and the S32FlashTool folder.
        Use full paths for filenames used as parameters.

        Hints for AI agents and users:
        - No hardware-specific defaults are applied for target, algorithm, interface, or port.
        - Discover valid target binaries with s32flashtool_list_available_platform_files(base_folder, bin_type="target").
        - Discover valid flash algorithms with s32flashtool_list_available_platform_files(base_folder, bin_type="flash").
        - Discover available ports/endpoints with s32flashtool_execute_expert(list_ports=True).

        - Use absolute paths for target, algorithm, and file_path.
        - Do not guess a COM port or MCU family if the user did not specify them.
        - Before target operations, consult the corresponding supported device list in the
        installation doc folder (for example supported_s32n5_devices.txt).
        """
        try:
            validate_s32flashtool_installation(s32flashtool_folder)

            target = resolve_relative_to_installation(s32flashtool_folder, target)
            algorithm = resolve_relative_to_installation(s32flashtool_folder, algorithm)
            file_path = resolve_relative_to_installation(s32flashtool_folder, file_path)

            validate_existing_file(target, "target")
            validate_existing_file(algorithm, "algorithm")

            if file_path is not None:
                parent = Path(file_path).parent
                if not parent.exists():
                    raise FileNotFoundError(f"'file_path' parent folder not found: {parent}")

            validate_numeric_like(addr, "addr")
            validate_numeric_like(size, "size")

            cli_extra_args: List[str] = []
            if binary_output:
                cli_extra_args.append("-b")
            if file_path:
                cli_extra_args.extend(["-f", file_path])
            if extra_args:
                cli_extra_args.extend(extra_args)

            ft = FlashToolClient(s32flashtool_folder)

            result = await ft.run(
                target=target,
                algorithm=algorithm,
                interface=interface,
                port=port,
                ftcmd="fread",
                addr=addr,
                size=size,
                extra_args=cli_extra_args,
                timeout=timeout,
            )

            return _normalize_run_result(result)

        except Exception as e:
            return _envelope("error", exit_code=-1, message=f"S32FlashTool is not reachable: {e}")


    @mcp.tool(
    name="list_available_platform_files",
    description="""
    Discover S32FlashTool installation assets and return their ABSOLUTE paths, so they can be passed
    directly to the other tools (target, algorithm, file_path) without guessing. Read-only / safe.

    Call this FIRST whenever target, algorithm, supported-device, or example values are unknown.

    Parameters:
    - base_folder: absolute path to the S32FlashTool installation root.
    - bin_type: one of "target", "flash", "supported", "blob", "example_pdf".

    Returns a uniform envelope {status, data, message}. On success ``data`` is a list of entries; the
    entry format depends on bin_type:
    - "target": target binaries in <base_folder>/targets. Each entry is an absolute .bin path
      (use as the 'target' argument of other tools).
    - "flash": flash algorithms in <base_folder>/flash. Each entry is an absolute .bin path
      (use as the 'algorithm' argument of other tools).
    - "supported": supported_*.txt docs in <base_folder>/doc. Each entry is an absolute path. Files are
      per processor family (e.g. supported_s32n5_devices.txt -> S32N5 family) and list supported
      processors, flash algorithms, interfaces, and limitations. Consult before processor-specific ops.
    - "blob": example/test binaries in <base_folder>/examples, each entry:
      "<platform> | <board_name> | <flash_type> | <absolute_bin_file>".
    - "example_pdf": board PDFs in <base_folder>/examples, each entry:
      "<platform> | <pdf_filename> | <absolute_pdf_path>".

    Returns status:"error" (with an explanatory ``message``) on failure or an unrecognized bin_type.
    """
    )
    async def s32flashtool_list_available_platform_files(base_folder: str, bin_type: str = None) -> ToolResult:
        try:
            logger.info(f"list_available_platform_files executing in {base_folder} with {bin_type}")
            match bin_type:
                case "target":
                    return _envelope("ok", data=list_files_by_extension(base_folder, subfolder="targets", extension=".bin"))
                case "flash":
                    return _envelope("ok", data=list_files_by_extension(base_folder, subfolder="flash", extension=".bin"))
                case "blob":
                    return _envelope("ok", data=list_available_test_blob_binaries(base_folder + "/examples"))
                case "example_pdf":
                    return _envelope("ok", data=list_pdfs_with_platform(base_folder + "/examples"))
                case "supported":
                    return _envelope("ok", data=list_available_supported_devices_text_files(base_folder))
                case _:
                    logger.info(f"list_available_platform_files unprocessed {bin_type}")
                    return _envelope("error", exit_code=-1, message=f"Unrecognized bin_type: {bin_type}")

        except Exception as e:
            return _envelope("error", exit_code=-1, message=f"list_available_platform_files: {e}")


    @mcp.tool(
    name="get_version",
    description="""
        Report a version string: either this MCP server's version or the installed S32FlashTool's
        version. Read-only / safe; runs S32FlashTool.exe with no arguments and returns its first
        output line. Use as a quick sanity check that the installation is reachable before any device
        communication or flash operation.

        Parameters:
        - app="mcp": return the MCP server version (path is ignored).
        - app="" (any other value): set path to the S32FlashTool installation folder; the tool runs the
          installed S32FlashTool.exe and returns its version/identification string.

        Returns a uniform envelope {status, exit_code, data, message}. ``data`` holds the version
        string on success; status:"error" (with ``message``) on failure.
    """
    )
    async def s32flashtool_get_version_(app: str, path: Optional[str] = None) -> ToolResult:
        """
        Get S32FlashTool version by executing the s32flashtool.exe with no parameters in the given folder.
        """
        try:
            match app:
                case "mcp":
                    return _envelope("ok", exit_code=0, data=mcp.version)
                case _:
                    logger.info("s32flashtool_get_version executing in %s", path)
                    ft = FlashToolClient(path)
                    resp = await ft.simple_execute()

                    if isinstance(resp, dict):
                        first_line = resp.get("output", "").split('\n')[0]
                        exit_code = resp.get("exit_code", 0)
                        status = resp.get("status", "ok")
                        # get_version runs S32FlashTool.exe with NO command. In that
                        # mode the tool prints its version banner and then exits
                        # non-zero (observed exit code 4) purely because no operation
                        # was requested - it is not a real failure. As long as a
                        # version line was captured, normalize BOTH status and
                        # exit_code to success so the probe reports "ok". If no output
                        # was produced, preserve the original failure signal.
                        if first_line:
                            status = "ok"
                            exit_code = 0
                        return _envelope(
                            status,
                            exit_code=exit_code,
                            data=first_line,
                        )
                    return _envelope("ok", exit_code=0, data=str(resp).split('\n')[0])

        except Exception as e:
            return _envelope("error", exit_code=-1, message=f"S32FlashTool is not reachable: {e}")