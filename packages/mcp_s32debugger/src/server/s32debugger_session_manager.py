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

import re
import json
import tempfile
from datetime import datetime
from pathlib import Path
import os
import asyncio

import logging
import subprocess

from .gdb_client import GdbClient

from .process_utils import ProcessUtils
from .config_generator import S32DebuggerConfigGenerator
from .jsonrpc_socket import send_jsonrpc

from nxp.mcp.s32debugger.metadata.server import MCP_SERVER_NAME

logger = logging.getLogger(MCP_SERVER_NAME)


class S32DebuggerSessionManager:
    """Session manager for S32 Debugger GDB variants (ARM32, ARM64)"""

    # GDB executables are discovered dynamically by scanning the installation's
    # 'gdb/' folder for '*gdb-py[.exe]' binaries (see _scan_installed_gdbs).
    ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def __init__(self, configured_installation_path: str | Path | None = None):
        normalized_configured = self._normalize_installation_path(configured_installation_path)
        self.configured_installation_path: Path | None = normalized_configured
        self.runtime_installation_path: Path | None = None
        self.gta_process = None
        self.gta_pid = None

        self.ccs_pid = None
        self.ccs_path = None
        self.ccs_port = None
        self.config_file = None

        # Session / IO state for controlled GDB sessions
        self.gdb_clients: dict[str, GdbClient] = {}
        self.active_gdb_client_id: str | None = None
        self.config_generator = (
            S32DebuggerConfigGenerator(self.effective_installation_path)
            if self.effective_installation_path is not None else None
        )
        self.strip_ansi_output = True

        # Cache of discovered GDB executable paths; populated lazily.
        self._installed_gdbs_cache: list[str] | None = None
        self._refresh_installed_gdbs()

    @property
    def effective_installation_path(self) -> Path | None:
        return self.runtime_installation_path or self.configured_installation_path

    def _normalize_installation_path(self, value: str | Path | None) -> Path | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return Path(text).expanduser()

    def _refresh_config_generator(self) -> None:
        self.config_generator = (
            S32DebuggerConfigGenerator(self.effective_installation_path)
            if self.effective_installation_path is not None else None
        )

    def get_configured_installation_path(self) -> str | None:
        return str(self.configured_installation_path) if self.configured_installation_path else None

    def get_runtime_installation_path(self) -> str | None:
        return str(self.runtime_installation_path) if self.runtime_installation_path else None

    def get_installation_path(self) -> str | None:
        return str(self.effective_installation_path) if self.effective_installation_path else None

    def has_installation_path(self) -> bool:
        return self.effective_installation_path is not None

    def get_missing_installation_path_message(self) -> str:
        example = (
            "C:/NXP/S32DBG.3.6.10" if os.name == "nt"
            else "/home/user/NXP/S32DBG.3.6.10"
        )
        if self.configured_installation_path is None and self.runtime_installation_path is None:
            return (
                "Error: No S32Debugger installation path is configured.\n\n"
                "In the config YAML used for this MCP server, `settings.installation_path` is not set.\n"
                f"Set it in the server config YAML or call:\n"
                f"s32debugger(action=\"set_installation_path\", installation_path=\"{example}\")"
            )
        return (
            "Error: No active S32Debugger installation path is available.\n\n"
            f"Set a valid installation path with:\n"
            f"s32debugger(action=\"set_installation_path\", installation_path=\"{example}\")"
        )

    def require_installation_path(self) -> str | None:
        if self.effective_installation_path is None:
            return self.get_missing_installation_path_message()
        return None

    def describe_installation_state(self) -> dict:
        configured_path = self.get_configured_installation_path()
        runtime_path = self.get_runtime_installation_path()
        effective_path = self.get_installation_path()
        warning = None
        if not configured_path:
            warning = "In the config YAML used for this MCP server, `settings.installation_path` is not set."
        return {
            "configured_installation_path": configured_path,
            "runtime_installation_path": runtime_path,
            "effective_installation_path": effective_path,
            "installation_path_configured": bool(configured_path),
            "warning": warning,
        }

    @staticmethod
    def _exe(name: str) -> str:
        """Return the platform-appropriate executable name (appends .exe on Windows)."""
        return name + (".exe" if os.name == "nt" else "")

    def validate_installation_path(self, installation_path: str | Path | None) -> tuple[bool, list[str], Path | None]:
        normalized = self._normalize_installation_path(installation_path)
        if normalized is None:
            return False, ["'installation_path' is required"], None

        issues: list[str] = []
        gta_exe = normalized / "S32Debugger" / "Debugger" / "Server" / "gta" / self._exe("gta")
        ccs_dir = normalized / "S32Debugger" / "Debugger" / "Server" / "CCS"
        demo_utils = normalized / "S32Debugger" / "Debugger" / "scripts" / "utils" / "demo_utils.py"

        if not normalized.exists():
            issues.append(f"Path does not exist: {normalized}")
        if not gta_exe.exists():
            issues.append(f"Missing GTA executable: {gta_exe}")
        if not ccs_dir.exists():
            issues.append(f"Missing CCS directory: {ccs_dir}")
        if not demo_utils.exists():
            issues.append(f"Missing demo_utils.py: {demo_utils}")

        return len(issues) == 0, issues, normalized

    def set_installation_path(self, installation_path: str | Path | None, allow_active_session: bool = False) -> str:
        if self.is_active_session and not allow_active_session:
            return (
                "Error: Cannot change the S32Debugger installation path while a debug session is active. "
                "Stop the active session first."
            )

        ok, issues, normalized = self.validate_installation_path(installation_path)
        if not ok or normalized is None:
            return "Error: Invalid S32Debugger installation path:\n- " + "\n- ".join(issues)

        self.runtime_installation_path = normalized
        self._refresh_config_generator()
        self._refresh_installed_gdbs()
        return f"S32Debugger installation path set to: {normalized}"

    def _require_base_folder(self) -> Path:
        message = self.require_installation_path()
        if message:
            raise ValueError(message)
        effective_path = self.effective_installation_path
        assert effective_path is not None
        return effective_path

    @property
    def is_active_session(self) -> bool:
        has_active_gdb = any(
            client.is_running(ProcessUtils.is_pid_running)
            for client in self.gdb_clients.values()
        )
        if not has_active_gdb:
            return False
        if not ProcessUtils.is_pid_running(self.gta_pid):
            return False
        if not ProcessUtils.is_pid_running(self.ccs_pid):
            return False
        return True

    def reconcile_gdb_clients_state(self) -> bool:
        terminated_found = False

        for session_id, client in self.gdb_clients.items():
            if client.is_running(ProcessUtils.is_pid_running):
                continue

            terminated_found = True
            client.connected = False
            if not client.last_error:
                client.mark_last_error("GDB process terminated unexpectedly after startup")

            for task in (client.stdout_task, client.stderr_task):
                if task is not None and not task.done():
                    task.cancel()

            client.process = None
            client.stdout_task = None
            client.stderr_task = None

            if self.active_gdb_client_id == session_id:
                self.active_gdb_client_id = None

        return terminated_found

    def _get_gdb_client(self, gdb_client_id: str | None = None) -> GdbClient:
        if gdb_client_id:
            client = self.gdb_clients.get(gdb_client_id)
            if client is None:
                raise ValueError(f"Unknown gdb_client_id '{gdb_client_id}'")
            return client

        if self.active_gdb_client_id:
            client = self.gdb_clients.get(self.active_gdb_client_id)
            if client is not None:
                return client

        running_clients = [
            client for client in self.gdb_clients.values()
            if client.is_running(ProcessUtils.is_pid_running)
        ]
        if len(running_clients) == 1:
            return running_clients[0]
        if len(self.gdb_clients) == 1:
            return next(iter(self.gdb_clients.values()))
        if not self.gdb_clients:
            raise ValueError("No GDB clients available")
        raise ValueError("Multiple GDB clients are available; specify gdb_client_id")

    def _strip_ansi(self, text: str) -> str:
        return self.ANSI_ESCAPE_RE.sub("", text)

    def _scan_installed_gdbs(self) -> list[str]:
        """Scan the installation's 'gdb/' folder for GDB executables.

        Recursively globs for files whose name ends with 'gdb-py.exe' on
        Windows (or 'gdb-py' on other platforms), verifies each is a regular
        file, and returns a de-duplicated list of resolved executable paths.
        Only the raw path is reported; mapping a path to an architecture/variant
        is left to the caller (documented in the skill) so no architecture
        knowledge is hardcoded here.
        """
        try:
            base_folder = self._require_base_folder()
        except ValueError:
            return []

        gdb_root = base_folder / "gdb"
        if not gdb_root.is_dir():
            return []

        suffix = "gdb-py.exe" if os.name == "nt" else "gdb-py"
        discovered: list[str] = []
        seen: set[str] = set()
        for candidate in gdb_root.rglob("*"):
            try:
                if not candidate.is_file():
                    continue
            except OSError:
                continue
            if not candidate.name.lower().endswith(suffix):
                continue
            resolved = str(candidate.resolve())
            key = resolved.lower()
            if key in seen:
                continue
            seen.add(key)
            discovered.append(resolved)
        return discovered

    def _refresh_installed_gdbs(self) -> None:
        """Populate the installed-GDB cache when a valid installation exists."""
        if self.effective_installation_path is None:
            self._installed_gdbs_cache = None
            return
        self._installed_gdbs_cache = self._scan_installed_gdbs()

    def get_gta_path(self) -> Path:
        """Get the path to the GTA (GDB server) executable."""
        base_folder = self._require_base_folder()
        return base_folder / "S32Debugger" / "Debugger" / "Server" / "gta" / self._exe("gta")

    def get_ccs_path(self) -> Path:
        """Get the path to the CCS executable managed by GTA."""
        base_folder = self._require_base_folder()
        return base_folder / "S32Debugger" / "Debugger" / "Server" / "CCS" / "bin" / self._exe("ccs")

    def get_ccs_cfg_path(self) -> Path:
        """Get the path to the CCS configuration file."""
        base_folder = self._require_base_folder()
        return base_folder / "S32Debugger" / "Debugger" / "Server" / "CCS" / "bin" / "ccs.cfg"

    def read_expected_ccs_port(self) -> int | None:
        """Read the expected CCS TCP port from ccs.cfg if available."""
        try:
            cfg_path = self.get_ccs_cfg_path()
            if not cfg_path.exists():
                return None
            content = cfg_path.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"(?im)^\s*(?:config\s+)?port\s+(\d+)\s*$", content)
            if not match:
                return None
            port = int(match.group(1))
            self.ccs_port = port
            return port
        except Exception:
            return None

    def _extract_bridge_port_from_config(self, config_file: str) -> int | None:
        try:
            content = Path(config_file).read_text(encoding='utf-8', errors='replace')
            marker = 'start_bridge(port='
            idx = content.find(marker)
            if idx == -1:
                return None
            tail = content[idx + len(marker):]
            digits = ''
            for ch in tail:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            return int(digits) if digits else None
        except Exception:
            return None

    async def discover_debug_processes(self) -> dict:
        self._require_base_folder()

        # Build the set of expected GDB executable paths from the discovered GDBs.
        if self._installed_gdbs_cache is None:
            self._refresh_installed_gdbs()
        installed_gdbs = self._installed_gdbs_cache or []
        expected_gdb_paths = list(installed_gdbs)
        expected_gdb_paths_norm = {str(Path(p)).lower() for p in installed_gdbs}

        expected_gta = self.get_gta_path().resolve()
        expected_ccs = self.get_ccs_path().resolve()

        gta_pid = None
        ccs_pid = None
        gta_path = None
        ccs_path = None
        gdb_processes: list[dict] = []

        if os.name == "nt":
            script = rf"""
    $ErrorActionPreference = 'SilentlyContinue'
    $procs = Get-CimInstance Win32_Process | Select-Object ProcessId, Name, ExecutablePath, ParentProcessId
    $procs | ConvertTo-Json -Depth 3 -Compress
    """
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-Command", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout, _stderr = await proc.communicate()
            try:
                entries = json.loads(stdout.decode(errors="replace") or "[]")
                if isinstance(entries, dict):
                    entries = [entries]
            except Exception:
                entries = []

            expected_gta_n = self._norm(str(expected_gta))
            expected_ccs_n = self._norm(str(expected_ccs))

            for item in entries:
                exe = item.get("ExecutablePath")
                exe_n = self._norm(exe)

                if exe_n is not None and exe_n in expected_gdb_paths_norm:
                    gdb_processes.append(
                        {
                            "pid": item.get("ProcessId"),
                            "path": exe,
                            "parent_pid": item.get("ParentProcessId"),
                        }
                    )
                elif exe_n == expected_gta_n and gta_pid is None:
                    gta_pid = item.get("ProcessId")
                    gta_path = exe
                elif exe_n == expected_ccs_n and ccs_pid is None:
                    ccs_pid = item.get("ProcessId")
                    ccs_path = exe

        elif os.name == "posix":
            # Enumerate processes via /proc on Linux.
            expected_gta_n = self._norm(str(expected_gta))
            expected_ccs_n = self._norm(str(expected_ccs))

            proc_root = Path("/proc")
            for pid_dir in proc_root.iterdir():
                if not pid_dir.name.isdigit():
                    continue
                try:
                    exe_link = (pid_dir / "exe").resolve()
                    exe_str = str(exe_link)
                    exe_n = self._norm(exe_str)
                    stat_file = pid_dir / "stat"
                    ppid = None
                    try:
                        stat_text = stat_file.read_text(errors="replace")
                        # Format: pid (comm) state ppid ...
                        # The comm field may contain spaces/parentheses; find the last ')'.
                        last_paren = stat_text.rfind(")")
                        if last_paren != -1:
                            rest = stat_text[last_paren + 1:].split()
                            if len(rest) >= 2:
                                ppid = int(rest[1])
                    except Exception:
                        pass

                    pid_int = int(pid_dir.name)
                    if exe_n is not None and exe_n in expected_gdb_paths_norm:
                        gdb_processes.append(
                            {
                                "pid": pid_int,
                                "path": exe_str,
                                "parent_pid": ppid,
                            }
                        )
                    elif exe_n == expected_gta_n and gta_pid is None:
                        gta_pid = pid_int
                        gta_path = exe_str
                    elif exe_n == expected_ccs_n and ccs_pid is None:
                        ccs_pid = pid_int
                        ccs_path = exe_str
                except (OSError, ValueError):
                    # /proc/<pid>/exe may not be readable for processes owned by
                    # other users or that exited during enumeration.
                    continue

        return {
            "gdb_processes": gdb_processes,
            "gta_pid": gta_pid,
            "gta_path": gta_path,
            "ccs_pid": ccs_pid,
            "ccs_path": ccs_path,
            "expected_gdb_paths": expected_gdb_paths,
            "expected_gta_path": str(expected_gta),
            "expected_ccs_path": str(expected_ccs),
            "ccs_expected_port": self.read_expected_ccs_port(),
        }

    @staticmethod
    def _norm(p: str | None) -> str | None:
        if not p:
            return None
        return str(Path(p)).lower()

    async def _try_bridge_quit(self, client: GdbClient) -> str | None:
        port = client.bridge_port or (
            self._extract_bridge_port_from_config(client.config_file)
            if client.config_file else None
        )
        if not port:
            return (
                f"No JSON-RPC bridge port configured for GDB client {client.session_id}; "
                "no bridge server was started for this client, so 'quit' cannot be sent"
            )

        try:
            # asyncio.to_thread forwards the keyword-only 'timeout' directly.
            response = await asyncio.to_thread(
                send_jsonrpc, "127.0.0.1", int(port), "quit", {}, timeout=2.0
            )
            # Mirror _jsonrpc_call's error policy: a non-dict or 'error' response
            # is a failure.
            if not isinstance(response, dict):
                return (
                    f"JSON-RPC quit for GDB client {client.session_id} on port {port} "
                    f"returned unexpected response type: {type(response).__name__}"
                )
            if "error" in response:
                return (
                    f"JSON-RPC quit for GDB client {client.session_id} on port {port} "
                    f"returned error: {response['error']}"
                )
            # A response with neither 'error' nor 'result' is malformed.
            if "result" not in response:
                return (
                    f"JSON-RPC quit for GDB client {client.session_id} on port {port} "
                    f"returned malformed response (missing 'result')"
                )
            return None
        except Exception as e:
            return f"Failed to send JSON-RPC quit to GDB client {client.session_id} on port {port}: {e}"

    async def start_gta(self, interactive: bool = True) -> str:
        gta_path = self.get_gta_path()
        if not gta_path.exists():
            return f"Error: GTA executable not found at {gta_path}"

        if self.gta_process and self.gta_process.returncode is None:
            return f"GTA is already running (PID: {self.gta_pid})"
        if ProcessUtils.is_pid_running(self.gta_pid):
            return f"GTA is already running (PID: {self.gta_pid})"

        try:
            cwd = str(gta_path.parent)
            if interactive and os.name == 'nt':
                pid, msg = await ProcessUtils.start_windows_interactive_process(str(gta_path), [], cwd)
                if not pid:
                    return msg
                self.gta_process = None
                self.gta_pid = pid
                return f"Started GTA interactively (PID: {pid})"

            self.gta_process = await asyncio.create_subprocess_exec(
                str(gta_path),
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0),
            )
            self.gta_pid = self.gta_process.pid
            return f"Started GTA in background (PID: {self.gta_pid})"
        except Exception as e:
            return f"Error starting GTA: {e}"

    async def is_gta_running(self) -> bool:
        if self.gta_process and self.gta_process.returncode is None:
            return True
        return ProcessUtils.is_pid_running(self.gta_pid)

    async def _consume_stream(self, client: GdbClient, stream, source: str) -> None:
        """Consume async subprocess stream and append to the target client's output buffer."""
        try:
            while True:
                chunk = await stream.read(512)
                if not chunk:
                    break
                text = chunk.decode(errors="replace")
                client.append_output(
                    text,
                    source,
                    strip_ansi=self.strip_ansi_output,
                    ansi_stripper=self._strip_ansi,
                )
        except Exception as e:
            client.append_output(
                f"[{source} stream error] {e}\n",
                source,
                strip_ansi=self.strip_ansi_output,
                ansi_stripper=self._strip_ansi,
            )
        finally:
            client.flush_output_line_buffers(source)

    async def start_gdb_client(
        self,
        gdb_client_id: str,
        gdb_path: str,
        config_file: str,
    ) -> str:
        """Start an interactive, bridge-enabled GDB client.

        Ensures GTA (the GDB server) is running (auto-starting it if needed),
        validates the GDB executable and config file, launches GDB interactively
        with the config sourced via '-x', extracts the JSON-RPC bridge port baked into

        the config, and registers the client under the required gdb_client_id.
        """
        self.reconcile_gdb_clients_state()

        if not gdb_client_id:
            return "Error: gdb_client_id is required"
        if not gdb_path:
            return "Error: gdb_path is required"
        if not config_file:
            return "Error: config_file is required"

        if gdb_client_id in self.gdb_clients:
            return f"Error: GDB client '{gdb_client_id}' already exists"

        gdb_exe = Path(gdb_path)
        if not gdb_exe.exists():
            return f"Error: GDB executable not found at {gdb_path}"

        config_path = Path(config_file)
        if not config_path.exists():
            return f"Error: Config file not found at {config_file}"

        # Pre-flight: config generation defers the bridge-existence check (it may
        # run without the install tree), so verify it here at the point of use,
        # only when the config references the bridge.
        if self._extract_bridge_port_from_config(str(config_path)) is not None:
            if self.config_generator is not None:
                bridge_script_path = self.config_generator._get_bridge_script_path()
                try:
                    self.config_generator._validate_bridge_script_path(
                        bridge_script_path, require_exists=True
                    )
                except (FileNotFoundError, ValueError) as exc:
                    return f"Error: JSON-RPC bridge script pre-flight check failed: {exc}"

        # Ensure the GDB server (GTA) is running; auto-start it if needed.
        if not await self.is_gta_running():
            gta_message = await self.start_gta(interactive=True)
            if gta_message.startswith("Error"):
                return f"Error: Could not start GTA (GDB server): {gta_message}"

        self.config_file = str(config_path)
        args = ["-x", str(config_path)]
        cwd = str(gdb_exe.parent)

        # Label the client with the executable name; architecture mapping is
        # left to the skill.
        gdb_variant = gdb_exe.name

        client = GdbClient(
            gdb_client_session_id=gdb_client_id,
            gdb_variant=gdb_variant,
            config_file=self.config_file,
        )
        client.created_at = datetime.now().isoformat(timespec="seconds")
        client.interactive = True
        client.mode = "window"
        client.clear_gdb_output()
        client.last_connect_error = None
        client.set_launch_context(
            config_file=self.config_file,
            interactive=True,
            mode=client.mode,
            executable=str(gdb_exe),
            cwd=cwd,
            extra={
                "args": args,
                "gdb_variant": gdb_variant,
            },
        )

        try:
            if os.name == "nt":
                pid, msg = await ProcessUtils.start_windows_interactive_process(str(gdb_exe), args, cwd)
                if not pid:
                    return msg
                client.pid = pid
                client.bridge_port = self._extract_bridge_port_from_config(self.config_file)
                self.gdb_clients[client.session_id] = client
                self.active_gdb_client_id = client.session_id
                return (
                    f"Started interactive GDB client '{client.session_id}' (PID: {pid}), "
                    f"bridge_port={client.bridge_port}"
                )

            process = await asyncio.create_subprocess_exec(
                str(gdb_exe),
                *args,
                cwd=cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0),
            )
            client.process = process
            client.pid = process.pid
            client.bridge_port = self._extract_bridge_port_from_config(self.config_file)
            self.gdb_clients[client.session_id] = client
            self.active_gdb_client_id = client.session_id
            client.stdout_task = asyncio.create_task(self._consume_stream(client, process.stdout, "stdout"))
            client.stderr_task = asyncio.create_task(self._consume_stream(client, process.stderr, "stderr"))
            return (
                f"Started GDB client '{client.session_id}' (PID: {client.pid}), "
                f"bridge_port={client.bridge_port}"
            )
        except Exception as e:
            return f"Error starting GDB client: {e}"

    def get_gdb_client_status(self, gdb_client_id: str) -> dict:
        """Return the per-client status dictionary for a single GDB client."""
        client = self.gdb_clients.get(gdb_client_id)
        if client is None:
            return {
                "gdb_client_id": gdb_client_id,
                "found": False,
                "error": f"Unknown gdb_client_id '{gdb_client_id}'",
            }
        status = client.to_status_dict(ProcessUtils.is_pid_running)
        status["found"] = True
        return status

    async def get_gdb_server_status(self) -> dict:
        """Return the status of the GDB server (GTA)."""
        try:
            gta_path = str(self.get_gta_path())
        except Exception:
            gta_path = None
        running = await self.is_gta_running()
        return {
            "running": running,
            "pid": self.gta_pid,
            "path": gta_path,
        }

    def list_installed_gdbs(self) -> dict:
        """List the GDB executables discovered under the installation's 'gdb/' folder.

        Returns the cached scan results, performing a lazy (re)scan when the
        cache has not been populated yet.
        """
        message = self.require_installation_path()
        if message:
            return {"error": message, "gdbs": []}

        if self._installed_gdbs_cache is None:
            self._refresh_installed_gdbs()

        return {"gdbs": list(self._installed_gdbs_cache or [])}

    async def stop_gdb(self, gdb_client_id: str | None = None) -> str:
        try:
            client = self._get_gdb_client(gdb_client_id)
        except ValueError as e:
            return f"Error: {e}"

        self.active_gdb_client_id = client.session_id
        messages = []

        if client.process is not None:
            try:
                if client.process.returncode is None:
                    client.process.terminate()
                    try:
                        await asyncio.wait_for(client.process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        client.process.kill()
                        await client.process.wait()
                messages.append(f"Stopped managed GDB process for {client.session_id}")
            except Exception as e:
                messages.append(f"Error stopping managed GDB process for {client.session_id}: {e}")
        elif await asyncio.to_thread(ProcessUtils.is_pid_running, client.pid):
            if await asyncio.to_thread(ProcessUtils.taskkill_pid, client.pid):
                messages.append(f"Stopped external GDB process PID={client.pid} for {client.session_id}")
            else:
                messages.append(f"Failed to stop external GDB process PID={client.pid} for {client.session_id}")
        else:
            messages.append(f"No active GDB process for {client.session_id}")

        for task in (client.stdout_task, client.stderr_task):
            if task is not None and not task.done():
                task.cancel()

        client.close_transcript()
        client.process = None
        client.pid = None
        client.bridge_port = None
        client.stdout_task = None
        client.stderr_task = None
        client.connected = False

        self.gdb_clients.pop(client.session_id, None)

        if self.active_gdb_client_id == client.session_id:
            self.active_gdb_client_id = next(iter(self.gdb_clients.keys()), None)

        # When the last GDB client is removed, also stop the GDB server (GTA).
        if not self.gdb_clients:
            messages.append(await self.stop_gta())

        return "\n".join(messages)

    async def stop_gta(self) -> str:
        if self.gta_process is not None:
            try:
                if self.gta_process.returncode is None:
                    self.gta_process.terminate()
                    try:
                        await asyncio.wait_for(self.gta_process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        self.gta_process.kill()
                        await self.gta_process.wait()
                self.gta_process = None
                pid = self.gta_pid
                self.gta_pid = None
                return f"Stopped managed GTA process (PID: {pid})"
            except Exception as e:
                return f"Error stopping GTA: {e}"

        if ProcessUtils.is_pid_running(self.gta_pid):
            pid = self.gta_pid
            if await asyncio.to_thread(ProcessUtils.taskkill_pid, self.gta_pid):
                self.gta_pid = None
                return f"Stopped external GTA process (PID: {pid})"
            return f"Failed to stop external GTA process (PID: {pid})"

        self.gta_pid = None
        return "No active GTA process"

    # Hard cap for a single CCS TCL invocation. CCS scripts that talk to a
    # target normally finish in well under a second; anything past this bound
    # means the process is stuck (e.g. a GUI-subsystem ccs.exe that never
    # exits) and must be force-terminated so the action cannot block forever.
    CCS_TCL_TIMEOUT_S = 120.0

    async def run_ccs_tcl_script(self, tcl_script_path: str) -> str:
        """Run a TCL script through the CCS executable and capture its console output.

        Resolves the CCS executable relative to the effective installation path
        (via get_ccs_path, which selects 'ccs.exe' on Windows and 'ccs' on
        Linux). The invocation strategy is OS-specific because the CCS
        executable is built differently per platform:

        - Windows: ccs.exe is a GUI-subsystem binary. It does NOT inherit the
          parent's stdout/stderr pipes, so console output from 'puts'/'display'
          never reaches a captured stdout pipe (the original 'return_code 0 with
          empty stdout' symptom). Worse, the '-nogfx <file>' / stdin form hangs
          because the windowed event loop never terminates. The robust approach
          here is to run 'ccs.exe -script <wrapper>' where the wrapper redirects
          Tcl 'puts' (which is what 'display' and the CCS API ultimately use) to
          a temporary result file, sources the user's script, then exits. The
          captured file is read back as stdout.

        - POSIX (Linux): ccs is a console binary that DOES echo console output to
          stdout when the script is piped into 'ccs -nogfx'. That path is used
          as-is (with an appended 'exit' to guarantee prompt termination).

        Both paths are bounded by CCS_TCL_TIMEOUT_S; on timeout the process tree
        is force-terminated and an 'error' field is returned. Precondition
        failures are returned as plain strings prefixed with 'Error:' so the
        result normalizer surfaces them as ACTION_FAILED.
        """
        message = self.require_installation_path()
        if message:
            return message

        if not tcl_script_path:
            return "Error: tcl_script_path is required"

        script_path = Path(tcl_script_path)
        if not script_path.is_file():
            return f"Error: TCL script not found at {tcl_script_path}"

        try:
            ccs_path = self.get_ccs_path()
        except ValueError as exc:
            return f"Error: {exc}"

        if not ccs_path.exists():
            return f"Error: CCS executable not found at {ccs_path}"

        if os.name == "nt":
            return await self._run_ccs_tcl_windows(ccs_path, script_path)
        return await self._run_ccs_tcl_posix(ccs_path, script_path)

    @staticmethod
    def _tcl_path(path: str | Path) -> str:
        """Render a filesystem path for safe embedding in a TCL script.

        Uses forward slashes (accepted by Tcl on every OS) so the value can be
        wrapped in braces without backslash-escaping surprises on Windows.
        """
        return str(path).replace("\\", "/")

    def _build_ccs_capture_wrapper(self, script_path: Path, out_path: Path, err_path: Path) -> str:
        """Build the Windows wrapper TCL that captures console output to files.

        The wrapper redefines 'puts' so that unqualified output and writes to the
        'stdout' channel are redirected into out_path, while writes to the
        'stderr' channel are redirected into err_path (mirroring the Linux
        stdout/stderr split); writes to explicit file handles keep their original
        behavior. Both capture files are unbuffered so text survives even if the
        sourced script calls 'exit' early (CCS reroutes 'exit' through its own
        cleanup). Any error raised while sourcing the user's script is also
        appended to err_path.
        """
        user = self._tcl_path(script_path)
        out = self._tcl_path(out_path)
        err = self._tcl_path(err_path)
        return (
            f"set __ccs_out [open {{{out}}} w]\n"
            f"set __ccs_err [open {{{err}}} w]\n"
            "fconfigure $__ccs_out -translation lf -buffering none\n"
            "fconfigure $__ccs_err -translation lf -buffering none\n"
            "catch {rename puts __ccs_real_puts}\n"
            "proc puts {args} {\n"
            "    global __ccs_out __ccs_err\n"
            "    set nl 1\n"
            "    if {[lindex $args 0] eq \"-nonewline\"} { set nl 0; set args [lrange $args 1 end] }\n"
            "    set n [llength $args]\n"
            "    if {$n == 1} {\n"
            "        set s [lindex $args 0]\n"
            "        if {$nl} { __ccs_real_puts $__ccs_out $s } else { __ccs_real_puts -nonewline $__ccs_out $s }\n"
            "    } elseif {$n == 2} {\n"
            "        set ch [lindex $args 0]; set s [lindex $args 1]\n"
            "        if {$ch eq \"stdout\"} {\n"
            "            if {$nl} { __ccs_real_puts $__ccs_out $s } else { __ccs_real_puts -nonewline $__ccs_out $s }\n"
            "        } elseif {$ch eq \"stderr\"} {\n"
            "            if {$nl} { __ccs_real_puts $__ccs_err $s } else { __ccs_real_puts -nonewline $__ccs_err $s }\n"
            "        } else {\n"
            "            if {$nl} { __ccs_real_puts $ch $s } else { __ccs_real_puts -nonewline $ch $s }\n"
            "        }\n"
            "    } else {\n"
            "        eval __ccs_real_puts $args\n"
            "    }\n"
            "}\n"
            f"if {{[catch {{source {{{user}}}}} __ccs_src_err]}} {{\n"
            "    __ccs_real_puts $__ccs_err $__ccs_src_err\n"
            "    if {[info exists ::errorInfo]} { __ccs_real_puts $__ccs_err $::errorInfo }\n"
            "}\n"
            "catch {flush $__ccs_out}\n"
            "catch {close $__ccs_out}\n"
            "catch {flush $__ccs_err}\n"
            "catch {close $__ccs_err}\n"
            "exit\n"
        )

    async def _terminate_process_tree(self, process) -> None:
        """Force-terminate a subprocess and (on Windows) its whole child tree."""
        try:
            if process.returncode is not None:
                return
            if os.name == "nt" and process.pid:
                # ccs.exe spawns helper children; taskkill /T reaps the tree.
                await asyncio.to_thread(ProcessUtils.taskkill_pid, process.pid)
            else:
                process.kill()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
        except Exception:
            pass

    def _finalize_ccs_result(
        self,
        ccs_path: Path,
        script_path: Path,
        return_code,
        stdout_text: str,
        stderr_text: str,
        error: str | None = None,
    ) -> str:
        if self.strip_ansi_output:
            stdout_text = self._strip_ansi(stdout_text)
            stderr_text = self._strip_ansi(stderr_text)
        payload = {
            "ccs_path": str(ccs_path),
            "tcl_script_path": str(script_path),
            "return_code": return_code,
            "stdout": stdout_text,
            "stderr": stderr_text,
        }
        if error:
            payload["error"] = error
        return json.dumps(payload)

    async def _run_ccs_tcl_windows(self, ccs_path: Path, script_path: Path) -> str:
        """Windows path: '-script <wrapper>' with console output captured to a file.

        ccs.exe is a GUI-subsystem binary that neither echoes console output to
        an inherited stdout pipe nor terminates under '-nogfx <file>'. The
        wrapper redirects Tcl 'puts' to a temp file and forces an exit, so we get
        both real console output and prompt termination.
        """
        cwd = str(ccs_path.parent)
        tmp_dir = tempfile.mkdtemp(prefix="ccs_tcl_")
        wrapper_path = Path(tmp_dir) / "wrapper.tcl"
        out_path = Path(tmp_dir) / "stdout.txt"
        err_path = Path(tmp_dir) / "stderr.txt"

        try:
            wrapper_path.write_text(
                self._build_ccs_capture_wrapper(script_path, out_path, err_path),
                encoding="utf-8",
            )

            try:
                process = await asyncio.create_subprocess_exec(
                    str(ccs_path),
                    "-script",
                    str(wrapper_path),
                    cwd=cwd,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception as exc:
                return f"Error running CCS TCL script: {exc}"

            timed_out = False
            try:
                await asyncio.wait_for(process.communicate(), timeout=self.CCS_TCL_TIMEOUT_S)
            except asyncio.TimeoutError:
                timed_out = True
                await self._terminate_process_tree(process)

            stdout_text = ""
            stderr_text = ""
            try:
                if out_path.exists():
                    stdout_text = out_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
            try:
                if err_path.exists():
                    stderr_text = err_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

            if timed_out:
                return self._finalize_ccs_result(
                    ccs_path,
                    script_path,
                    None,
                    stdout_text,
                    stderr_text,
                    error=f"CCS TCL script timed out after {self.CCS_TCL_TIMEOUT_S:.0f}s and was terminated",
                )

            return self._finalize_ccs_result(
                ccs_path,
                script_path,
                process.returncode,
                stdout_text,
                stderr_text,
            )
        finally:
            for p in (wrapper_path, out_path, err_path):
                try:
                    p.unlink()
                except OSError:
                    pass
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass

    async def _run_ccs_tcl_posix(self, ccs_path: Path, script_path: Path) -> str:
        """POSIX path: pipe the script into 'ccs -nogfx' and capture stdout/stderr.

        On Linux the CCS binary is a console program that echoes 'puts'/'display'
        output to stdout when fed a script on stdin under '-nogfx'. An 'exit' is
        appended to guarantee prompt termination.
        """
        cwd = str(ccs_path.parent)
        try:
            script_text = script_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"Error reading TCL script: {exc}"
        stdin_data = (script_text + "\nexit\n").encode("utf-8")

        try:
            process = await asyncio.create_subprocess_exec(
                str(ccs_path),
                "-nogfx",
                cwd=cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as exc:
            return f"Error running CCS TCL script: {exc}"

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=stdin_data), timeout=self.CCS_TCL_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            await self._terminate_process_tree(process)
            return self._finalize_ccs_result(
                ccs_path,
                script_path,
                None,
                "",
                "",
                error=f"CCS TCL script timed out after {self.CCS_TCL_TIMEOUT_S:.0f}s and was terminated",
            )

        stdout_text = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
        stderr_text = stderr_bytes.decode(errors="replace") if stderr_bytes else ""
        return self._finalize_ccs_result(
            ccs_path,
            script_path,
            process.returncode,
            stdout_text,
            stderr_text,
        )

    # config file part
    async def generate_config_from_template(
        self,
        soc_family: str,
        script_type: str,
        template_name: str,
        output_name: str | None = None,
        **overrides,
    ) -> str:
        message = self.require_installation_path()
        if message:
            return message
        assert self.config_generator is not None
        return await self.config_generator.generate_config_from_template(
            soc_family=soc_family,
            script_type=script_type,
            template_name=template_name,
            output_name=output_name,
            **overrides,
        )
