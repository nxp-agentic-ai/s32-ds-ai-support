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

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


@dataclass
class GdbClient:
    gdb_client_session_id: str
    gdb_variant: str
    config_file: Optional[str] = None

    role: Optional[str] = None
    core_name: Optional[str] = None
    core_id: Optional[int] = None
    cluster_id: Optional[str] = None
    lockstep: Optional[bool] = None

    process: object | None = None
    pid: Optional[int] = None
    interactive: bool = False
    mode: str = "background"
    connected: bool = False

    bridge_port: Optional[int] = None

    output_buffer: list[str] = field(default_factory=list)
    stdout_task: asyncio.Task | None = None
    stderr_task: asyncio.Task | None = None
    output_line_buffers: dict[str, str] = field(default_factory=dict)
    max_buffer_lines: int = 4000

    transcript_path: Optional[Path] = None
    transcript_file: object | None = None

    launch_context: dict = field(default_factory=dict)
    last_connect_error: dict | None = None

    created_at: Optional[str] = None
    last_error: Optional[str] = None

    @property
    def session_id(self) -> str:
        return self.gdb_client_session_id

    @session_id.setter
    def session_id(self, value: str) -> None:
        self.gdb_client_session_id = value

    def is_running(self, pid_checker: Callable[[Optional[int]], bool]) -> bool:
        if self.process is not None and getattr(self.process, "returncode", None) is None:
            return True
        return pid_checker(self.pid)

    def has_command_control(self) -> bool:
        return (
            self.process is not None
            and self.mode == "background"
            and getattr(self.process, "stdin", None) is not None
        )

    def append_output(
        self,
        text: str,
        source: str,
        *,
        strip_ansi: bool = False,
        ansi_stripper: Optional[Callable[[str], str]] = None,
    ) -> None:
        if not text:
            return

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        self.inspect_connect_error(normalized, source)
        cleaned = ansi_stripper(normalized) if strip_ansi and ansi_stripper else normalized

        pending = self.output_line_buffers.get(source, "") + cleaned
        while True:
            newline_index = pending.find("\n")
            if newline_index < 0:
                break
            line = pending[:newline_index]
            pending = pending[newline_index + 1 :]
            if line == "":
                continue
            entry = f"[{source}] {line}"
            self.output_buffer.append(entry)
            self.write_transcript(entry)

        self.output_line_buffers[source] = pending
        self.flush_prompt_like_output(source)

        if len(self.output_buffer) > self.max_buffer_lines:
            self.output_buffer = self.output_buffer[-self.max_buffer_lines :]

    def flush_prompt_like_output(self, source: str) -> None:
        pending = self.output_line_buffers.get(source, "")
        if not pending:
            return

        trimmed = pending.rstrip()
        if trimmed.endswith("(gdb)"):
            entry = f"[{source}] {pending}"
            self.output_buffer.append(entry)
            self.write_transcript(entry)
            self.output_line_buffers[source] = ""

            if len(self.output_buffer) > self.max_buffer_lines:
                self.output_buffer = self.output_buffer[-self.max_buffer_lines :]

    def flush_output_line_buffers(self, source: str | None = None) -> None:
        """Flush buffered partial output lines into the main output/transcript sinks."""
        sources = [source] if source is not None else list(self.output_line_buffers.keys())
        for src in sources:
            pending = self.output_line_buffers.get(src, "")
            if not pending:
                continue
            entry = f"[{src}] {pending}"
            self.output_buffer.append(entry)
            self.write_transcript(entry)
            self.output_line_buffers[src] = ""

        if len(self.output_buffer) > self.max_buffer_lines:
            self.output_buffer = self.output_buffer[-self.max_buffer_lines :]

    def open_transcript(self, path: Path) -> None:
        if self.transcript_file:
            return
        self.transcript_path = path
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        self.transcript_file = self.transcript_path.open("a", encoding="utf-8", buffering=1)

    def close_transcript(self) -> None:
        if self.transcript_file:
            try:
                self.transcript_file.flush()
                self.transcript_file.close()
            finally:
                self.transcript_file = None

    def write_transcript(self, line: str) -> None:
        try:
            if self.transcript_file is not None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                self.transcript_file.write(f"{timestamp} {line}\n")
        except Exception:
            pass

    def inspect_connect_error(self, text: str, source: str) -> None:
        lower = text.lower()
        if (
            "timed out" in lower
            or "timeout" in lower
            or "connection refused" in lower
            or "unable to connect" in lower
        ):
            self.last_connect_error = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "source": source,
                "message": text.strip(),
            }

    def set_launch_context(
        self,
        *,
        config_file: str | None,
        interactive: bool,
        mode: str,
        executable: str | None,
        cwd: str | None,
        extra: Optional[dict] = None,
    ) -> None:
        self.launch_context = {
            "config_file": config_file,
            "interactive": interactive,
            "mode": mode,
            "executable": executable,
            "cwd": cwd,
            "variant": self.gdb_variant,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        if extra:
            self.launch_context.update(extra)

    def add_gdb_output(self, text: str, source: str) -> None:
        self.append_output(text, source)

    def has_gdb_output(self) -> bool:
        return bool(self.output_buffer)

    def read_gdb_output(self) -> str:
        if not self.output_buffer:
            return ""
        output = "\n".join(self.output_buffer)
        self.output_buffer.clear()
        return output

    def clear_gdb_output(self) -> None:
        self.output_buffer.clear()
        self.output_line_buffers.clear()

    def clear_transcript_handles(self) -> None:
        self.transcript_file = None
        self.transcript_path = None

    def mark_last_error(self, message: Optional[str]) -> None:
        self.last_error = message

    def to_status_dict(self, pid_checker: Callable[[Optional[int]], bool]) -> dict:
        return {
            "gdb_client_session_id": self.session_id,
            "role": self.role,
            "core_name": self.core_name,
            "core_id": self.core_id,
            "cluster_id": self.cluster_id,
            "lockstep": self.lockstep,
            "gdb_variant": self.gdb_variant,
            "config_file": self.config_file,
            "pid": self.pid,
            "interactive": self.interactive,
            "mode": self.mode,
            "connected": self.connected,
            "bridge_port": self.bridge_port,
            "running": self.is_running(pid_checker),
            "created_at": self.created_at,
            "last_error": self.last_error,
            "transcript_path": str(self.transcript_path) if self.transcript_path else None,
        }

    def to_diagnostics_dict(self, pid_checker: Callable[[Optional[int]], bool]) -> dict:
        data = self.to_status_dict(pid_checker)
        data.update(
            {
                "launch_context": self.launch_context,
                "last_connect_error": self.last_connect_error,
                "has_command_control": self.has_command_control(),
                "has_buffered_output": self.has_gdb_output(),
            }
        )
        return data
