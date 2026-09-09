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

"""Shared JSON-RPC 2.0 over TCP client for the GDB bridge.

Messages are LSP-style framed: 'Content-Length: <N>\r\n\r\n' followed by N
bytes of UTF-8 JSON. send_jsonrpc is transport-only and returns the raw
response object; callers apply their own error policy.
"""


import json
import socket
import uuid
from typing import Any, TypeAlias

# JSON value type produced/consumed by the transport.
JsonValue: TypeAlias = (

    dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None
)

# Only send_jsonrpc and the port-range constants are public; the private
# helpers remain importable by name for unit tests.
__all__ = ["send_jsonrpc", "MIN_BRIDGE_PORT", "MAX_BRIDGE_PORT"]


# Anti-OOM bounds against a bridge that never terminates the header or
# advertises an absurd body length. 4 MB is generous for GDB output.
_MAX_HEADER_SIZE = 8 * 1024
_MAX_BODY_SIZE = 4 * 1024 * 1024

# Reject privileged ports (1-1023). Single source of truth, re-exported so
# callers do not duplicate the range and drift out of sync.
MIN_BRIDGE_PORT = 1024
MAX_BRIDGE_PORT = 65535

# Backwards-compatible private aliases for existing callers and unit tests.
_MIN_BRIDGE_PORT = MIN_BRIDGE_PORT
_MAX_BRIDGE_PORT = MAX_BRIDGE_PORT

# Loopback-only, to avoid turning the transport into an SSRF vector.
_ALLOWED_BRIDGE_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

# LSP-style frame separator between the header block and the JSON body.
_SEPARATOR = b"\r\n\r\n"



def _next_request_id() -> str:
    """Return a fresh UUID request id (thread-safe, no shared counter)."""
    return str(uuid.uuid4())


def _parse_content_length(header_bytes: bytes) -> int:
    """Extract and validate Content-Length from the header block.

    Raises ValueError if it is missing, malformed, negative, or exceeds
    _MAX_BODY_SIZE.
    """

    for line in header_bytes.split(b"\r\n"):

        if line.lower().startswith(b"content-length:"):
            try:
                value = int(line.split(b":", 1)[1].strip())
            except ValueError:
                raise ValueError(f"Malformed Content-Length header: {line!r}")
            if value < 0:
                raise ValueError(f"Negative Content-Length: {value}")
            if value > _MAX_BODY_SIZE:
                raise ValueError(f"Content-Length {value} exceeds maximum {_MAX_BODY_SIZE}")
            return value
    raise ValueError("Missing Content-Length header in bridge response")


def _read_framed_message(sock: socket.socket) -> bytearray:
    """Read one LSP-style framed message and return the body as a bytearray.

    Raises ConnectionError if the peer closes early, ValueError on malformed
    or oversized headers/bodies.
    """
    header_buf = bytearray()
    sep_idx = -1
    while sep_idx == -1:
        # Cap the read at _MAX_HEADER_SIZE, reserving room for a separator that
        # straddles the chunk boundary.
        max_read = _MAX_HEADER_SIZE - len(header_buf) + len(_SEPARATOR)
        if max_read <= 0:
            raise ValueError(f"Response header exceeds {_MAX_HEADER_SIZE} bytes - possible protocol error")
        chunk = sock.recv(min(256, max_read))
        if not chunk:
            raise ConnectionError("Bridge closed connection before sending response header")
        # Only re-scan the tail so the separator search stays near O(1) per read.
        search_start = max(0, len(header_buf) - len(_SEPARATOR) + 1)
        header_buf += chunk
        if len(header_buf) > _MAX_HEADER_SIZE:
            raise ValueError(f"Response header exceeds {_MAX_HEADER_SIZE} bytes - possible protocol error")
        sep_idx = header_buf.find(_SEPARATOR, search_start)

    # Split on the separator so body bytes arriving in the same TCP segment as
    # the header terminator are preserved.
    header_bytes = bytes(header_buf[:sep_idx])
    already_read = bytearray(header_buf[sep_idx + len(_SEPARATOR):])

    content_length = _parse_content_length(header_bytes)

    # Pre-allocate and fill in place with recv_into to avoid repeated
    # reallocations for large bodies.
    body_buf = bytearray(content_length)
    view = memoryview(body_buf)

    # Copy in body bytes that arrived with the header terminator; content_length
    # caps them defensively.
    offset = min(len(already_read), content_length)
    view[:offset] = already_read[:offset]

    while offset < content_length:
        n = sock.recv_into(view[offset:], min(content_length - offset, 65536))
        if not n:
            raise ConnectionError(
                f"Bridge closed connection after {offset}/{content_length} body bytes"
            )
        offset += n

    # Runtime check (not assert, which is stripped under 'python -O') on data
    # read from the wire.
    if offset != content_length:

        raise ConnectionError(
            f"Body read incomplete: expected {content_length}, got {offset} bytes"
        )
    return body_buf



def send_jsonrpc(
    host: str,
    port: int,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 10.0,
    request_id: str | None = None,
) -> Any:
    """Send a single JSON-RPC 2.0 request and return the raw response object.

    Transport-only: does not interpret 'result'/'error'. Transport failures
    propagate as the underlying exception (OSError, ValueError, JSONDecodeError).
    """

    if host not in _ALLOWED_BRIDGE_HOSTS:
        raise ValueError(
            f"Bridge host {host!r} is not a permitted loopback address. "
            f"Allowed: {sorted(_ALLOWED_BRIDGE_HOSTS)}"
        )
    if not _MIN_BRIDGE_PORT <= port <= _MAX_BRIDGE_PORT:
        raise ValueError(
            f"Invalid bridge port {port}: must be in range "
            f"[{_MIN_BRIDGE_PORT}, {_MAX_BRIDGE_PORT}]"
        )
    if not method:

        raise ValueError("method must be a non-empty string")

    if timeout <= 0:
        raise ValueError(f"timeout must be positive, got {timeout}")

    req_id = request_id if request_id is not None else _next_request_id()
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params if params is not None else {},
        "id": req_id,
    }
    body = json.dumps(request).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(header + body)
        payload = _read_framed_message(sock)

    # json.loads accepts a bytearray directly and handles UTF-8 decoding, so no
    # separate .decode() copy is needed.
    response = json.loads(payload)


    if isinstance(response, dict) and response.get("id") != req_id:
        raise ValueError(
            f"JSON-RPC response id mismatch: sent {req_id!r}, got {response.get('id')!r}"
        )

    return response
