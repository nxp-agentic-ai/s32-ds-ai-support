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

# In-process GDB bridge exposing GDB control over a local TCP socket via
# JSON-RPC 2.0, LSP-style framed (Content-Length header + blank line + JSON).
# Sourced by GDB through a generated config; the start_bridge/stop_bridge API
# is stable so the 'start_bridge(port=...)' config marker keeps working.


import json
import queue
import threading
import socketserver


import gdb

_bridge_state = {
    "server": None,
    "thread": None,
    "port": None,
    "transcript": [],
    "queue": None,
}

# JSON-RPC 2.0 standard error codes
_PARSE_ERROR = -32700
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_INTERNAL_ERROR = -32603


def _log(line):
    _bridge_state["transcript"].append(line)
    if len(_bridge_state["transcript"]) > 2000:
        _bridge_state["transcript"] = _bridge_state["transcript"][-2000:]


def _execute_on_gdb_thread(command, timeout=10.0):
    result_q = queue.Queue(maxsize=1)

    def _runner():
        try:
            gdb.write("[bridge] >>> {}\n".format(command))
            out = gdb.execute(command, to_string=True)
            if out:
                gdb.write(out)
                if not out.endswith("\n"):
                    gdb.write("\n")
            gdb.flush()
            result_q.put({"ok": True, "command": command, "output": out})
            _log(">>> {}\n{}".format(command, out))
        except Exception as e:
            result_q.put({"ok": False, "command": command, "error": str(e)})
            _log(">>> {}\nERROR: {}".format(command, e))

    gdb.post_event(_runner)
    return result_q.get(timeout=timeout)


def _interrupt_on_gdb_thread(timeout=10.0):
    result_q = queue.Queue(maxsize=1)

    def _runner():
        try:
            try:
                gdb.write("[bridge] >>> interrupt\n")
                out = gdb.execute("interrupt", to_string=True)
                _log(">>> interrupt\n{}".format(out))
                result_q.put({"ok": True, "method": "interrupt", "output": out})
                return
            except Exception:
                pass

            out = gdb.execute("monitor halt", to_string=True)
            _log(">>> monitor halt\n{}".format(out))
            result_q.put({"ok": True, "method": "monitor halt", "output": out})
        except Exception as e:
            result_q.put({"ok": False, "error": str(e)})
            _log(">>> <INTERRUPT>\nERROR: {}".format(e))

    gdb.post_event(_runner)
    return result_q.get(timeout=timeout)


def _status_on_gdb_thread(timeout=10.0):
    result_q = queue.Queue(maxsize=1)

    def _runner():
        try:
            frame = gdb.selected_frame()
            sal = frame.find_sal() if frame else None
            pc = hex(frame.pc()) if frame else None
            result_q.put({
                "ok": True,
                "pc": pc,
                "filename": sal.symtab.filename if sal and sal.symtab else None,
                "line": sal.line if sal else None,
            })
        except Exception as e:
            result_q.put({"ok": False, "error": str(e)})

    gdb.post_event(_runner)
    return result_q.get(timeout=timeout)


def _transcript_result():
    return {"ok": True, "transcript": "\n".join(_bridge_state["transcript"])}


# ---------------------------------------------------------------------------
# JSON-RPC method dispatch
# ---------------------------------------------------------------------------

def _dispatch(method, params):
    """Execute a single JSON-RPC method and return the result payload.

    Raises _RpcError for method-not-found or invalid-params.
    """
    params = params or {}
    if method == "execute":
        command = params.get("command", "")
        if not command:
            raise _RpcError(_INVALID_PARAMS, "Missing required param 'command'")
        return _execute_on_gdb_thread(command)
    if method == "interrupt":
        return _interrupt_on_gdb_thread()
    if method == "status":
        return _status_on_gdb_thread()
    if method == "transcript":
        return _transcript_result()
    if method == "quit":
        # Schedule bridge shutdown after replying to the caller.
        threading.Thread(target=stop_bridge, daemon=True).start()
        return {"ok": True, "message": "bridge shutting down"}
    raise _RpcError(_METHOD_NOT_FOUND, "Method not found: {}".format(method))


class _RpcError(Exception):
    def __init__(self, code, message):
        super(_RpcError, self).__init__(message)
        self.code = code
        self.message = message


def _handle_request(request):
    """Handle a decoded JSON-RPC request object and return a response object."""
    req_id = request.get("id") if isinstance(request, dict) else None

    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        return {
            "jsonrpc": "2.0",
            "error": {"code": _INVALID_REQUEST, "message": "Invalid JSON-RPC 2.0 request"},
            "id": req_id,
        }

    method = request.get("method")
    params = request.get("params")

    try:
        result = _dispatch(method, params)
        return {"jsonrpc": "2.0", "result": result, "id": req_id}
    except _RpcError as e:
        return {"jsonrpc": "2.0", "error": {"code": e.code, "message": e.message}, "id": req_id}
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": _INTERNAL_ERROR, "message": str(e)},
            "id": req_id,
        }


# ---------------------------------------------------------------------------
# LSP-style framing over a raw TCP stream
# ---------------------------------------------------------------------------

def _read_message(rfile):
    """Read one framed JSON message; return the decoded object or None if closed."""
    content_length = None
    while True:
        line = rfile.readline()
        if not line:
            return None
        line = line.strip()
        if line == b"":
            break
        if b":" in line:
            name, _, value = line.partition(b":")
            if name.strip().lower() == b"content-length":
                try:
                    content_length = int(value.strip())
                except ValueError:
                    content_length = None

    if content_length is None:
        raise _RpcError(_PARSE_ERROR, "Missing Content-Length header")

    body = rfile.read(content_length)
    if body is None or len(body) < content_length:
        raise _RpcError(_PARSE_ERROR, "Truncated message body")
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as e:
        raise _RpcError(_PARSE_ERROR, "Invalid JSON body: {}".format(e))


def _write_message(wfile, obj):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    header = "Content-Length: {}\r\n\r\n".format(len(body)).encode("ascii")
    wfile.write(header)
    wfile.write(body)
    wfile.flush()


class _RpcHandler(socketserver.StreamRequestHandler):
    def handle(self):
        peer = getattr(self, "client_address", None)
        while True:
            try:
                request = _read_message(self.rfile)
            except _RpcError as e:
                # Parse error: reply with a null-id error and keep serving.
                try:
                    _write_message(
                        self.wfile,
                        {"jsonrpc": "2.0", "error": {"code": e.code, "message": e.message}, "id": None},
                    )
                except (OSError, ValueError) as write_err:
                    _log("Failed to send parse-error reply to {}: {}".format(peer, write_err))
                    return
                continue
            except (OSError, ValueError) as read_err:
                # Transport failure (closed/reset socket, decode error); log and close.
                _log("Read error from {}, closing connection: {}".format(peer, read_err))
                return

            if request is None:
                return

            response = _handle_request(request)
            try:
                _write_message(self.wfile, response)
            except (OSError, ValueError) as write_err:
                _log("Write error to {}, closing connection: {}".format(peer, write_err))
                return



class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_bridge(host="127.0.0.1", port=8766):
    if _bridge_state["server"] is not None:
        gdb.write("GDB bridge already running on {}\n".format(_bridge_state["port"]))
        return

    server = _ThreadingTCPServer((host, port), _RpcHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _bridge_state["server"] = server
    _bridge_state["thread"] = thread
    _bridge_state["port"] = port
    _log("Bridge started on tcp://{}:{}".format(host, port))
    gdb.write("GDB JSON-RPC bridge started on tcp://{}:{}\n".format(host, port))


def stop_bridge():
    server = _bridge_state["server"]
    if server is None:
        gdb.write("GDB bridge is not running\n")
        return
    server.shutdown()
    server.server_close()
    _bridge_state["server"] = None
    _bridge_state["thread"] = None
    _bridge_state["port"] = None
    _log("Bridge stopped")
    gdb.write("GDB bridge stopped\n")
