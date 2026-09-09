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

import asyncio
import os
import signal
import socket
import subprocess
import time
from typing import Optional


class ProcessUtils:
    @staticmethod
    def ps_quote(value: str) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    @staticmethod
    def is_pid_running(pid: Optional[int]) -> bool:
        if pid is None or pid <= 0:
            return False
        if os.name == 'posix':
            try:
                os.kill(int(pid), 0)
                return True
            except ProcessLookupError:
                return False
            except PermissionError:
                # Process exists but is owned by another user.
                return True
            except Exception:
                return False
        # Windows path.
        try:
            proc = subprocess.run(
                ["cmd", "/c", "tasklist", "/FI", f"PID eq {int(pid)}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = (proc.stdout or "").lower()
            return str(int(pid)) in out and "no tasks are running" not in out
        except Exception:
            return False

    @staticmethod
    def taskkill_pid(pid: Optional[int]) -> bool:
        """Kill a process by PID.

        WARNING: The POSIX path uses blocking sleeps.
        Always call this via ``asyncio.to_thread`` from async contexts.
        """
        if pid is None or pid <= 0:
            return False
        if os.name == 'posix':
            try:
                os.kill(int(pid), signal.SIGTERM)
                # Give the process up to 3 seconds to exit gracefully.
                for _ in range(30):
                    time.sleep(0.1)
                    if not ProcessUtils.is_pid_running(pid):
                        return True
                # Force-kill if still alive.
                os.kill(int(pid), signal.SIGKILL)
                time.sleep(0.2)
                return not ProcessUtils.is_pid_running(pid)
            except ProcessLookupError:
                # Already gone.
                return True
            except Exception:
                return False
        # Windows path.
        try:
            proc = subprocess.run(
                ["cmd", "/c", "taskkill", "/PID", str(int(pid)), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return proc.returncode == 0 or not ProcessUtils.is_pid_running(pid)
        except Exception:
            return False

    @staticmethod
    async def start_windows_interactive_process(
        executable: str,
        arguments: list[str],
        cwd: str,
        env_updates: Optional[dict] = None,
    ) -> tuple[Optional[int], str]:
        try:
            env_updates = env_updates or {}
            env_lines = [f"$env:{k}={ProcessUtils.ps_quote(v)}" for k, v in env_updates.items()]

            if arguments:
                arg_items = ", ".join(ProcessUtils.ps_quote(arg) for arg in arguments)
                start_line = (
                    f"$proc = Start-Process -FilePath {ProcessUtils.ps_quote(executable)} "
                    f"-ArgumentList @({arg_items}) "
                    f"-WorkingDirectory {ProcessUtils.ps_quote(cwd)} -PassThru"
                )
            else:
                start_line = (
                    f"$proc = Start-Process -FilePath {ProcessUtils.ps_quote(executable)} "
                    f"-WorkingDirectory {ProcessUtils.ps_quote(cwd)} -PassThru"
                )

            script_lines = [
                "$ErrorActionPreference = 'Stop'",
                *env_lines,
                start_line,
                "$proc.Id",
            ]
            proc = await asyncio.create_subprocess_exec(
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "; ".join(script_lines),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode(errors="replace").strip() or stdout.decode(errors="replace").strip()
                return None, f"Error launching interactive process: {err or f'PowerShell exited with code {proc.returncode}'}"

            out = stdout.decode(errors="replace").strip().splitlines()
            pid = None
            for line in reversed(out):
                line = line.strip()
                if line.isdigit():
                    pid = int(line)
                    break
            if not pid:
                return None, "Error: interactive process launched but PID could not be determined"
            return pid, f"Started interactive process PID={pid}"
        except Exception as e:
            return None, f"Error launching interactive process: {e}"

    @staticmethod
    def is_local_tcp_port_open(host: str, port: Optional[int], timeout: float = 1.0) -> bool:
        if not port:
            return False
        try:
            with socket.create_connection((host, int(port)), timeout=timeout):
                return True
        except Exception:
            return False
