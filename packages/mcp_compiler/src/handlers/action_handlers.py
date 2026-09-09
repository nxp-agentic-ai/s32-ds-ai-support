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

"""Action handlers for the compiler MCP component.

Each handler corresponds to one ActionExecutable defined in src/actions/.
Handlers delegate to the existing toolchain implementation modules in
src/tools/ which contain the subprocess execution and result-building logic.

Handler signatures follow the shared dispatcher convention:
    async def handler(params: dict, session_manager: object | None = None) -> object
"""

import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from nxp.mcp.compiler.impl.launcher import CompilerInstallInfo
from nxp.mcp.compiler.impl.utils import create_timestamped_dir


@dataclass
class GccResult:
    """Result of a GCC toolchain operation.

    Fields:
        output_file:   Relative path (from base_dir) to the -o output artifact.
                       Use ``artifact_path`` for the absolute path to pass to
                       subsequent tool calls.
        artifact_path: Absolute path to the -o output artifact (ELF, object, ...).
                       Pass this directly to the next gcc_execute call - each call
                       runs in its own working directory so relative paths do NOT
                       survive across calls.  Always use this field when chaining.
        saved_to:      Absolute path to the per-call scratch directory.
    """
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    command: str
    output_file: Optional[str]
    artifact_path: Optional[str]
    saved_to: Optional[str]


@dataclass
class LaxResult:
    """Result of a LAX toolchain operation.

    Fields:
        output_file:   Relative path (from base_dir) to the -o output artifact.
                       Use ``artifact_path`` for the absolute path to pass to
                       subsequent tool calls.
        artifact_path: Absolute path to the -o output artifact (ELF, object, ...).
                       Pass this directly to the next lax_execute call - each call
                       runs in its own working directory so relative paths do NOT
                       survive across calls.  Always use this field when chaining.
        saved_to:      Absolute path to the per-call scratch directory.
    """
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    command: str
    output_file: Optional[str]
    artifact_path: Optional[str]
    saved_to: Optional[str]


@dataclass
class SptResult:
    """Result of an SPT toolchain operation.

    Fields:
        output_file:   Relative path (from base_dir) to the -o output artifact.
                       Use ``artifact_path`` for the absolute path to pass to
                       subsequent tool calls.
        artifact_path: Absolute path to the -o output artifact (ELF, object, ...).
                       Pass this directly to the next spt_execute call - each call
                       runs in its own working directory so relative paths do NOT
                       survive across calls.  Always use this field when chaining.
        saved_to:      Absolute path to the per-call scratch directory.
    """
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    command: str
    output_file: Optional[str]
    artifact_path: Optional[str]
    saved_to: Optional[str]


@dataclass
class LaxSimulatorResult:
    """Result of a LAX simulator execution."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    command: str
    saved_to: Optional[str]


class CompilerInstallManager:
    """Session manager wrapper that carries the resolved CompilerInstallInfo.

    Passed to every handler by the shared action dispatcher so handlers can
    access toolchain paths without relying on module-level globals.
    """

    def __init__(self, install: CompilerInstallInfo) -> None:
        self.install = install


def _tokenize_args(args: str) -> list[str]:
    """Tokenize an args string using shlex, handling quoted paths correctly.

    Falls back to simple split when the string contains unmatched quotes.
    """
    try:
        return shlex.split(args)
    except ValueError:
        return args.split()


# ---------------------------------------------------------------------------
# GCC handlers
# ---------------------------------------------------------------------------

async def handle_list_gcc_tools(
    params: dict,
    session_manager: Optional[CompilerInstallManager] = None,
) -> object:
    """Return a formatted string listing discovered GCC toolchain bin dirs and binaries."""
    install = session_manager.install if session_manager else None
    if install is None:
        return "ERROR: No compiler install available."

    gcc_root = install.gcc_toolchain
    version_glob = install.gcc_version_glob
    bin_glob = install.gcc_bin_glob

    if not gcc_root.exists():
        return f"ERROR: GCC toolchain root not found: {gcc_root}"

    output = "GCC Compiler Toolchains\n"
    output += "=" * 70 + "\n\n"
    output += f"Toolchain root:    {gcc_root}\n"
    output += f"Version glob:      {version_glob}\n"
    output += f"Bin glob:          {bin_glob}\n\n"

    version_folders = sorted(gcc_root.glob(version_glob))
    if not version_folders:
        return output + f"ERROR: No version folders matched '{version_glob}' under {gcc_root}"

    for version_folder in version_folders:
        output += f"{version_folder.name}\n"
        output += f"   {'-' * 50}\n"
        bin_dirs = sorted(version_folder.glob(bin_glob))
        if not bin_dirs:
            output += f"ERROR: No bin dirs matched '{bin_glob}'\n\n"
            continue
        for bin_dir in bin_dirs:
            output += f"{bin_dir.relative_to(gcc_root)}\n"
            tools = sorted(bin_dir.iterdir()) if bin_dir.is_dir() else []
            for tool in tools:
                output += f"{tool.name}\n"
        output += "\n"

    return output


async def handle_gcc_execute(
    params: dict,
    session_manager: Optional[CompilerInstallManager] = None,
) -> object:
    """Execute a GCC toolchain binary and return a GccResult as a dict."""
    install = session_manager.install if session_manager else None
    if install is None:
        return asdict(GccResult(
            success=False, stdout="", stderr="No compiler install available.",
            exit_code=-1, command="", output_file=None, artifact_path=None, saved_to=None,
        ))

    toolchain_bin_dir: str = params.get("toolchain_bin_dir", "")
    binary: str = params.get("binary", "")
    args: str = params.get("args", "")
    input_code: Optional[str] = params.get("input_code", None)
    input_language: str = params.get("input_language", "c")
    save_output: bool = params.get("save_output", True)
    timeout_sec: int = params.get("timeout_sec", 300)

    output_dir = install.compile_output_dir
    base_dir = install.base_dir

    work_dir = create_timestamped_dir(output_dir, binary.replace(".exe", ""))

    def _fail(stderr: str, command: str = "") -> dict:
        return asdict(GccResult(
            success=False, stdout="", stderr=stderr, exit_code=-1,
            command=command, output_file=None, artifact_path=None,
            saved_to=str(work_dir.relative_to(base_dir)) if work_dir.exists() else None,
        ))

    try:
        bin_path = Path(toolchain_bin_dir) / binary
        if not bin_path.exists():
            bin_path_exe = Path(toolchain_bin_dir) / f"{binary}.exe"
            if bin_path_exe.exists():
                bin_path = bin_path_exe
            else:
                return _fail(
                    f"Binary '{binary}' not found in '{toolchain_bin_dir}'.\n"
                    "Tip: call compiler.list_gcc_tools to see available binaries.",
                    command=str(bin_path),
                )

        arg_list = _tokenize_args(args)

        source_file: Optional[Path] = None
        if input_code is not None:
            ext_map = {"c": ".c", "c++": ".cpp", "asm": ".s"}
            ext = ext_map.get(input_language.lower(), ".c")
            source_file = work_dir / f"source{ext}"
            source_file.write_text(input_code, encoding="utf-8")
            arg_list = [str(source_file)] + arg_list

        cmd = [str(bin_path)] + arg_list
        cmd_str = subprocess.list2cmdline(cmd)

        info_file = work_dir / "gcc_info.txt"
        info_file.write_text(
            f"Time:     {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Binary:   {bin_path}\n"
            f"Language: {input_language}\n"
            f"Args:     {args}\n"
            f"Command:  {cmd_str}\n"
            + (f"\n--- Source Code ---\n{input_code}\n" if input_code else ""),
            encoding="utf-8",
        )

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=work_dir, timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            return asdict(GccResult(
                success=False,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\nTimeout after {timeout_sec}s running: {cmd_str}",
                exit_code=-1, command=cmd_str,
                output_file=None, artifact_path=None,
                saved_to=str(work_dir.relative_to(base_dir)),
            ))
        except FileNotFoundError:
            return asdict(GccResult(
                success=False, stdout="",
                stderr=f"Binary not found at runtime: {bin_path}",
                exit_code=-1, command=cmd_str,
                output_file=None, artifact_path=None,
                saved_to=str(work_dir.relative_to(base_dir)),
            ))

        if save_output:
            log_file = work_dir / "gcc_output.log"
            log_file.write_text(
                f"Exit Code: {result.returncode}\n"
                f"Command:   {cmd_str}\n"
                f"\n--- STDOUT ---\n{result.stdout}\n"
                f"\n--- STDERR ---\n{result.stderr}\n",
                encoding="utf-8",
            )

        output_file: Optional[str] = None
        artifact_path: Optional[str] = None
        if "-o" in arg_list:
            try:
                o_idx = arg_list.index("-o")
                candidate = work_dir / arg_list[o_idx + 1]
                if candidate.exists():
                    output_file = str(candidate.relative_to(base_dir))
                    artifact_path = str(candidate.resolve())
            except (ValueError, IndexError):
                pass

        return asdict(GccResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            command=cmd_str,
            output_file=output_file,
            artifact_path=artifact_path,
            saved_to=str(work_dir.relative_to(base_dir)),
        ))

    except Exception as exc:
        return _fail(f"Unexpected error: {exc}")


# ---------------------------------------------------------------------------
# LAX Simulator handlers
# ---------------------------------------------------------------------------

async def handle_list_lax_simulator_tools(
    params: dict,
    session_manager: Optional[CompilerInstallManager] = None,
) -> object:
    """Return a formatted string listing discovered LAX simulator binaries."""
    install = session_manager.install if session_manager else None
    if install is None:
        return "ERROR: No compiler install available."

    simulator_root = install.lax_simulator

    if not simulator_root.exists():
        return f"ERROR: LAX simulator root not found: {simulator_root}"

    output = "LAX VSP Simulator\n"
    output += "=" * 70 + "\n\n"
    output += f"Simulator root:    {simulator_root}\n\n"

    entries = sorted(simulator_root.iterdir()) if simulator_root.is_dir() else []
    if not entries:
        return output + "ERROR: No files found in LAX simulator directory"

    output += "[binaries]\n"
    output += f"   {'-' * 50}\n"
    bin_count = 0
    for entry in entries:
        if entry.is_file() and entry.suffix.lower() in (".exe", ""):
            output += f"   * {entry.name}\n"
            bin_count += 1
    if bin_count == 0:
        output += "   (no executable binaries found)\n"

    output += "\n[all files]\n"
    output += f"   {'-' * 50}\n"
    for entry in entries:
        if entry.is_file():
            output += f"   - {entry.name}\n"
        elif entry.is_dir():
            output += f"   [dir] {entry.name}/\n"

    return output


async def handle_lax_simulator_execute(
    params: dict,
    session_manager: Optional[CompilerInstallManager] = None,
) -> object:
    """Execute a LAX simulator binary (runsim) on a compiled .eld file."""

    def _sim_fail(msg: str) -> dict:
        return asdict(LaxSimulatorResult(
            success=False, stdout="", stderr=msg,
            exit_code=-1, command="", saved_to=None,
        ))

    install = session_manager.install if session_manager else None
    if install is None:
        return _sim_fail("ERROR: No compiler install available.")

    binary: str = (params or {}).get("binary", "")
    args: str = (params or {}).get("args", "")
    executable_file: Optional[str] = (params or {}).get("executable_file")
    save_output: bool = (params or {}).get("save_output", True)
    timeout_sec: int = (params or {}).get("timeout_sec", 300)

    if not binary:
        return _sim_fail("ERROR: 'binary' parameter is required.")

    simulator_root = install.lax_simulator
    output_dir = install.compile_output_dir
    base_dir = install.base_dir

    work_dir = create_timestamped_dir(output_dir, f"sim_{binary.replace('.exe', '')}")

    try:
        bin_path = simulator_root / binary
        if not bin_path.exists():
            bin_path_exe = simulator_root / f"{binary}.exe"
            if bin_path_exe.exists():
                bin_path = bin_path_exe
            else:
                return _sim_fail(
                    f"Binary '{binary}' not found in '{simulator_root}'.\n"
                    f"Tip: call compiler.list_lax_simulator_tools to see available binaries."
                )

        exec_path: Optional[Path] = None
        if executable_file is not None:
            p = Path(executable_file)
            if not p.is_absolute():
                p = base_dir / executable_file
            if not p.exists():
                return _sim_fail(f"Executable not found: {executable_file}")
            exec_path = p

        arg_list = _tokenize_args(args) if args else []
        cmd = [str(bin_path)] + arg_list
        if exec_path is not None:
            cmd.append(str(exec_path))
        cmd_str = subprocess.list2cmdline(cmd)

        info_file = work_dir / "lax_sim_info.txt"
        info_file.write_text(
            f"Time:       {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Binary:     {bin_path}\n"
            f"Executable: {exec_path if exec_path else '(none)'}\n"
            f"Args:       {args}\n"
            f"Command:    {cmd_str}\n",
            encoding="utf-8",
        )

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=work_dir, timeout=timeout_sec,
            )

            if save_output:
                log_file = work_dir / "lax_sim_output.log"
                log_file.write_text(
                    f"Exit Code: {result.returncode}\n"
                    f"Command:   {cmd_str}\n"
                    f"\n--- STDOUT ---\n{result.stdout}\n"
                    f"\n--- STDERR ---\n{result.stderr}\n",
                    encoding="utf-8",
                )

            return asdict(LaxSimulatorResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                command=cmd_str,
                saved_to=str(work_dir.relative_to(base_dir)),
            ))

        except subprocess.TimeoutExpired as exc:
            return asdict(LaxSimulatorResult(
                success=False,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\nTimeout after {timeout_sec}s running: {cmd_str}",
                exit_code=-1, command=cmd_str,
                saved_to=str(work_dir.relative_to(base_dir)),
            ))

        except FileNotFoundError:
            return asdict(LaxSimulatorResult(
                success=False, stdout="",
                stderr=f"Binary not found at runtime: {bin_path}",
                exit_code=-1, command=cmd_str,
                saved_to=str(work_dir.relative_to(base_dir)),
            ))

    except Exception as exc:
        return _sim_fail(f"Unexpected error: {exc}")


# ---------------------------------------------------------------------------
# LAX handlers
# ---------------------------------------------------------------------------

async def handle_list_lax_tools(
    params: dict,
    session_manager: Optional[CompilerInstallManager] = None,
) -> object:
    """Return a formatted string listing discovered LAX toolchain bin dirs and binaries."""
    install = session_manager.install if session_manager else None
    if install is None:
        return "ERROR: No compiler install available."

    lax_root = install.lax_toolchain
    version_glob = install.lax_version_glob
    bin_glob = install.lax_bin_glob

    if not lax_root.exists():
        return f"ERROR: LAX toolchain root not found: {lax_root}"

    output = "LAX Compiler Toolchains\n"
    output += "=" * 70 + "\n\n"
    output += f"Toolchain root:    {lax_root}\n"
    output += f"Version glob:      {version_glob}\n"
    output += f"Bin glob:          {bin_glob}\n\n"

    version_folders = sorted(lax_root.glob(version_glob))
    if not version_folders:
        return output + f"ERROR: No version folders matched '{version_glob}' under {lax_root}"

    for version_folder in version_folders:
        output += f"[{version_folder.name}]\n"
        output += f"   {'-' * 50}\n"
        bin_dirs = sorted(version_folder.glob(bin_glob))
        if not bin_dirs:
            output += f"   ERROR: No bin dirs matched '{bin_glob}'\n\n"
            continue
        for bin_dir in bin_dirs:
            output += f"   - {bin_dir.relative_to(lax_root)}\n"
            tools = sorted(bin_dir.iterdir()) if bin_dir.is_dir() else []
            for tool in tools:
                output += f"      * {tool.name}\n"
        output += "\n"

    return output


async def handle_lax_execute(
    params: dict,
    session_manager: Optional[CompilerInstallManager] = None,
) -> object:
    """Execute a LAX toolchain binary and return a LaxResult as a dict."""
    install = session_manager.install if session_manager else None
    if install is None:
        return asdict(LaxResult(
            success=False, stdout="", stderr="No compiler install available.",
            exit_code=-1, command="", output_file=None, artifact_path=None, saved_to=None,
        ))

    toolchain_bin_dir: str = params.get("toolchain_bin_dir", "")
    binary: str = params.get("binary", "")
    args: str = params.get("args", "")
    input_code: Optional[str] = params.get("input_code", None)
    input_language: str = params.get("input_language", "c")
    save_output: bool = params.get("save_output", True)
    timeout_sec: int = params.get("timeout_sec", 300)

    output_dir = install.compile_output_dir
    base_dir = install.base_dir

    work_dir = create_timestamped_dir(output_dir, binary.replace(".exe", ""))

    def _fail(stderr: str, command: str = "") -> dict:
        return asdict(LaxResult(
            success=False, stdout="", stderr=stderr, exit_code=-1,
            command=command, output_file=None, artifact_path=None,
            saved_to=str(work_dir.relative_to(base_dir)) if work_dir.exists() else None,
        ))

    try:
        bin_path = Path(toolchain_bin_dir) / binary
        if not bin_path.exists():
            bin_path_exe = Path(toolchain_bin_dir) / f"{binary}.exe"
            if bin_path_exe.exists():
                bin_path = bin_path_exe
            else:
                return _fail(
                    f"Binary '{binary}' not found in '{toolchain_bin_dir}'.\n"
                    "Tip: call compiler.list_lax_tools to see available binaries.",
                    command=str(bin_path),
                )

        arg_list = _tokenize_args(args)

        source_file: Optional[Path] = None
        if input_code is not None:
            ext_map = {"c": ".c", "c++": ".cpp", "asm": ".s"}
            ext = ext_map.get(input_language.lower(), ".c")
            source_file = work_dir / f"source{ext}"
            source_file.write_text(input_code, encoding="utf-8")
            arg_list = [str(source_file)] + arg_list

        cmd = [str(bin_path)] + arg_list
        cmd_str = subprocess.list2cmdline(cmd)

        info_file = work_dir / "lax_info.txt"
        info_file.write_text(
            f"Time:     {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Binary:   {bin_path}\n"
            f"Language: {input_language}\n"
            f"Args:     {args}\n"
            f"Command:  {cmd_str}\n"
            + (f"\n--- Source Code ---\n{input_code}\n" if input_code else ""),
            encoding="utf-8",
        )

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=work_dir, timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            return asdict(LaxResult(
                success=False,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\nTimeout after {timeout_sec}s running: {cmd_str}",
                exit_code=-1, command=cmd_str,
                output_file=None, artifact_path=None,
                saved_to=str(work_dir.relative_to(base_dir)),
            ))
        except FileNotFoundError:
            return asdict(LaxResult(
                success=False, stdout="",
                stderr=f"Binary not found at runtime: {bin_path}",
                exit_code=-1, command=cmd_str,
                output_file=None, artifact_path=None,
                saved_to=str(work_dir.relative_to(base_dir)),
            ))

        if save_output:
            log_file = work_dir / "lax_output.log"
            log_file.write_text(
                f"Exit Code: {result.returncode}\n"
                f"Command:   {cmd_str}\n"
                f"\n--- STDOUT ---\n{result.stdout}\n"
                f"\n--- STDERR ---\n{result.stderr}\n",
                encoding="utf-8",
            )

        output_file: Optional[str] = None
        artifact_path: Optional[str] = None
        if "-o" in arg_list:
            try:
                o_idx = arg_list.index("-o")
                candidate = work_dir / arg_list[o_idx + 1]
                if candidate.exists():
                    output_file = str(candidate.relative_to(base_dir))
                    artifact_path = str(candidate.resolve())
            except (ValueError, IndexError):
                pass

        return asdict(LaxResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            command=cmd_str,
            output_file=output_file,
            artifact_path=artifact_path,
            saved_to=str(work_dir.relative_to(base_dir)),
        ))

    except Exception as exc:
        return _fail(f"Unexpected error: {exc}")


# ---------------------------------------------------------------------------
# SPT handlers
# ---------------------------------------------------------------------------

async def handle_list_spt_tools(
    params: dict,
    session_manager: Optional[CompilerInstallManager] = None,
) -> object:
    """Return a formatted string listing discovered SPT3.8 toolchain bin dirs and binaries."""
    install = session_manager.install if session_manager else None
    if install is None:
        return "ERROR: No compiler install available."

    spt_root = install.spt_toolchain
    version_glob = install.spt_version_glob
    bin_glob = install.spt_bin_glob

    if not spt_root.exists():
        return f"ERROR: SPT toolchain root not found: {spt_root}"

    output = "SPT Compiler Toolchains\n"
    output += "=" * 70 + "\n\n"
    output += f"Toolchain root:    {spt_root}\n"
    output += f"Version glob:      {version_glob}\n"
    output += f"Bin glob:          {bin_glob}\n\n"

    version_folders = sorted(spt_root.glob(version_glob))
    if not version_folders:
        return output + f"ERROR: No version folders matched '{version_glob}' under {spt_root}"

    for version_folder in version_folders:
        output += f"[{version_folder.name}]\n"
        output += f"   {'-' * 50}\n"
        bin_dirs = sorted(version_folder.glob(bin_glob))
        if not bin_dirs:
            output += f"   ERROR: No bin dirs matched '{bin_glob}'\n\n"
            continue
        for bin_dir in bin_dirs:
            output += f"   - {bin_dir.relative_to(spt_root)}\n"
            tools = sorted(bin_dir.iterdir()) if bin_dir.is_dir() else []
            for tool in tools:
                output += f"      * {tool.name}\n"
        output += "\n"

    return output


async def handle_spt_execute(
    params: dict,
    session_manager: Optional[CompilerInstallManager] = None,
) -> object:
    """Execute an SPT3.8 toolchain binary and return an SptResult as a dict."""
    install = session_manager.install if session_manager else None
    if install is None:
        return asdict(SptResult(
            success=False, stdout="", stderr="No compiler install available.",
            exit_code=-1, command="", output_file=None, artifact_path=None, saved_to=None,
        ))

    toolchain_bin_dir: str = params.get("toolchain_bin_dir", "")
    binary: str = params.get("binary", "")
    args: str = params.get("args", "")
    input_code: Optional[str] = params.get("input_code", None)
    input_language: str = params.get("input_language", "c")
    save_output: bool = params.get("save_output", True)
    timeout_sec: int = params.get("timeout_sec", 120)

    output_dir = install.compile_output_dir
    base_dir = install.base_dir

    work_dir = create_timestamped_dir(output_dir, binary.replace(".exe", ""))

    def _fail(stderr: str, command: str = "") -> dict:
        return asdict(SptResult(
            success=False, stdout="", stderr=stderr, exit_code=-1,
            command=command, output_file=None, artifact_path=None,
            saved_to=str(work_dir.relative_to(base_dir)) if work_dir.exists() else None,
        ))

    try:
        bin_path = Path(toolchain_bin_dir) / binary
        if not bin_path.exists():
            bin_path_exe = Path(toolchain_bin_dir) / f"{binary}.exe"
            if bin_path_exe.exists():
                bin_path = bin_path_exe
            else:
                return _fail(
                    f"Binary '{binary}' not found in '{toolchain_bin_dir}'.\n"
                    "Tip: call compiler.list_spt_tools to see available binaries.",
                    command=str(bin_path),
                )

        # SPT3.8 uses shlex tokenization to handle paths with spaces.
        # posix=False preserves Windows-style quoting; _dequote strips the
        # outer quotes that shlex leaves on tokens when posix=False.
        try:
            raw_tokens = shlex.split(args, posix=False)
        except ValueError:
            raw_tokens = args.split()

        def _dequote(tok: str) -> str:
            if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ('"', "'"):
                return tok[1:-1]
            for prefix in ("-I", "-L", "-o"):
                if tok.startswith(prefix) and len(tok) > len(prefix) + 1:
                    val = tok[len(prefix):]
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                        return prefix + val[1:-1]
            return tok

        arg_list = [_dequote(t) for t in raw_tokens]

        source_file: Optional[Path] = None
        if input_code is not None:
            source_file = work_dir / "source.spt"
            source_file.write_text(input_code, encoding="utf-8")
            arg_list = [str(source_file)] + arg_list
            if "-o" not in arg_list:
                arg_list += ["-o", "a.out"]

        cmd = [str(bin_path)] + arg_list
        cmd_str = subprocess.list2cmdline(cmd)

        info_file = work_dir / "spt_info.txt"
        info_file.write_text(
            f"Time:     {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Binary:   {bin_path}\n"
            f"Language: {input_language}\n"
            f"Args:     {args}\n"
            f"Command:  {cmd_str}\n"
            + (f"\n--- Source Code ---\n{input_code}\n" if input_code else ""),
            encoding="utf-8",
        )

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=work_dir, timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            return asdict(SptResult(
                success=False,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\nTimeout after {timeout_sec}s running: {cmd_str}",
                exit_code=-1,
                command=cmd_str,
                output_file=None,
                artifact_path=None,
                saved_to=str(work_dir.relative_to(base_dir)),
            ))

        if save_output:
            log_file = work_dir / "spt_output.log"
            log_file.write_text(
                f"Exit Code: {result.returncode}\n"
                f"Command:   {cmd_str}\n"
                f"\n--- STDOUT ---\n{result.stdout}\n"
                f"\n--- STDERR ---\n{result.stderr}\n",
                encoding="utf-8",
            )

        output_file: Optional[str] = None
        artifact_path: Optional[str] = None
        if "-o" in arg_list:
            try:
                o_idx = arg_list.index("-o")
                candidate = work_dir / arg_list[o_idx + 1]
                if candidate.exists():
                    output_file = str(candidate.relative_to(base_dir))
                    artifact_path = str(candidate.resolve())
            except (ValueError, IndexError):
                pass

        if artifact_path is None:
            default_out = work_dir / "a.out"
            if default_out.exists():
                output_file = str(default_out.relative_to(base_dir))
                artifact_path = str(default_out.resolve())

        return asdict(SptResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            command=cmd_str,
            output_file=output_file,
            artifact_path=artifact_path,
            saved_to=str(work_dir.relative_to(base_dir)),
        ))

    except Exception as exc:
        return _fail(f"Unexpected error: {exc}")
