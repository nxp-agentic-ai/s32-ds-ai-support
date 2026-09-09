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
from typing import Any

from nxp.mcp.s32debugger.server.s32debugger_session_manager import S32DebuggerSessionManager
from nxp.mcp.s32debugger.server.jsonrpc_socket import (
    send_jsonrpc,
    MIN_BRIDGE_PORT,
    MAX_BRIDGE_PORT,
)
from nxp.mcp.s32debugger.metadata.server import MCP_SERVER_NAME, MCP_SERVER_VERSION
from nxp.mcp.shared.action import ActionExecutionError, errors

_HANDLER_ERROR_CODE = errors.FORWARD_ERROR

# Minimum S32Debugger / S32 Debug Probe release this MCP server instance is
# validated against. Bump this constant when the server is re-validated against
# a newer debugger release.
_MIN_COMPATIBLE_DEBUGGER_VERSION = "3.6.11"


# Validate the port at the handler boundary so the caller gets a specific
# INVALID_PORT error instead of a generic BRIDGE_REQUEST_FAILED. The range is
# imported from jsonrpc_socket (single source of truth).
_MIN_BRIDGE_PORT = MIN_BRIDGE_PORT

_MAX_BRIDGE_PORT = MAX_BRIDGE_PORT



def _validate_port(port: int, context: str = "") -> None:
    if not _MIN_BRIDGE_PORT <= port <= _MAX_BRIDGE_PORT:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "INVALID_PORT",
            error_details={
                "message": (
                    f"Bridge port {port} is out of valid range "
                    f"[{_MIN_BRIDGE_PORT}, {_MAX_BRIDGE_PORT}]"
                    f"{f': {context}' if context else ''}"
                ),
                "port": port,
            },
        )


def _require_session_manager(session_manager: S32DebuggerSessionManager | None) -> S32DebuggerSessionManager:
    if session_manager is None:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "MISSING_CONTEXT",
            error_details={"message": "Missing session manager."},
        )
    return session_manager


def _jsonrpc_call(
    port: int,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 10.0,
) -> Any:
    """Send a JSON-RPC request to the bridge and apply the handler error policy.

    Blocking; in async contexts wrap with asyncio.to_thread. Returns the
    JSON-RPC 'result' on success, raises ActionExecutionError
    (BRIDGE_REQUEST_FAILED) on transport failures or JSON-RPC errors.
    """
    try:
        response = send_jsonrpc("127.0.0.1", port, method, params, timeout=timeout)
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "BRIDGE_REQUEST_FAILED",
            error_details={
                "message": f"JSON-RPC bridge request failed: {exc}",
                "method": method,
                "port": port,
            },
        ) from exc

    if not isinstance(response, dict):
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "BRIDGE_REQUEST_FAILED",
            error_details={
                "message": f"Unexpected JSON-RPC response type {type(response).__name__}",
                "method": method,
                "port": port,
            },
        )

    if "error" in response:
        error = response["error"]
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "BRIDGE_REQUEST_FAILED",
            error_details={
                "message": f"JSON-RPC error: {error}",
                "method": method,
                "port": port,
                "jsonrpc_error": error,
            },
        )

    # A legitimate 'result': null differs from a response missing the key.
    if "result" not in response:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "BRIDGE_REQUEST_FAILED",
            error_details={
                "message": "JSON-RPC response missing 'result' field",
                "method": method,
                "port": port,
            },
        )

    result = response["result"]

    # The bridge returns a success envelope with ok=False when GDB could not run
    # the command (busy or target running). Surface it as a GDB_BUSY error.
    if isinstance(result, dict) and result.get("ok") is False:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "GDB_BUSY",
            error_details={
                "message": result.get("error") or "GDB did not execute the command (busy or target running)",
                "method": method,
                "port": port,
                "gdb_state": result.get("gdb_state"),
            },
        )

    return result



async def _resolve_bridge_port(
    session_manager: S32DebuggerSessionManager,
    gdb_client_id: str | None,
    port: int | None,
) -> int:
    if not gdb_client_id:
        if port is None:
            raise ActionExecutionError(
                _HANDLER_ERROR_CODE,
                "MISSING_REQUIRED_PARAM",
                error_details={
                    "message": "'gdb_client_id' is required for bridge interaction actions unless 'port' is provided explicitly",
                    "required_one_of": ["gdb_client_id", "port"],
                },
            )
        _validate_port(port, context="provided port")
        return port


    s32debugger = session_manager

    try:
        client = s32debugger._get_gdb_client(gdb_client_id)
    except ValueError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "NOT_FOUND",
            error_details={
                "message": str(exc),
                "gdb_client_id": gdb_client_id,
            },
        ) from exc

    s32debugger.active_gdb_client_id = client.session_id
    if not client.bridge_port:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={
                "message": f"No JSON-RPC bridge port is configured for GDB client {client.session_id}; no bridge server was started for this client",
                "gdb_client_id": client.session_id,
            },
        )

    if port is not None and client.bridge_port != port:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PORT_MISMATCH",
            error_details={
                "message": f"Bridge port mismatch for GDB client {client.session_id}: expected {client.bridge_port}, received {port}",
                "expected_port": client.bridge_port,
                "received_port": port,
                "gdb_client_id": client.session_id,
            },
        )

    _validate_port(client.bridge_port, context="bridge port from config")
    return client.bridge_port


def _require_ready_session_manager(session_manager: S32DebuggerSessionManager | None) -> S32DebuggerSessionManager:
    session_manager = _require_session_manager(session_manager)
    missing_path_message = session_manager.require_installation_path()
    if missing_path_message:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": missing_path_message},
        )
    return session_manager


async def _bridge_call(
    session_manager: S32DebuggerSessionManager | None,
    gdb_client_id: str,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Resolve the bridge port and dispatch a JSON-RPC call, returning the response envelope.

    Shared by the bridge-interaction control handlers so port resolution and
    the off-thread blocking call live in one place.
    """
    sm = _require_ready_session_manager(session_manager)
    port = await _resolve_bridge_port(sm, gdb_client_id, None)
    response = await asyncio.to_thread(_jsonrpc_call, port, method, params, timeout=timeout)
    return {"port": port, "response": response}



# ==========================================================================
# Active handlers (control)
# ==========================================================================

async def control_set_installation_path(params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    session_manager = _require_session_manager(session_manager)
    return session_manager.set_installation_path(params["installation_path"])


async def control_start_gdb(params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    s32debugger = _require_ready_session_manager(session_manager)
    return await s32debugger.start_gdb_client(
        gdb_client_id=params["gdb_client_id"],
        gdb_path=params["gdb_path"],
        config_file=params["config_file"],
    )


async def control_stop_gdb(params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    s32debugger = _require_ready_session_manager(session_manager)
    return await s32debugger.stop_gdb(params.get("gdb_client_id"))


async def control_command(params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    # Terminating commands must not go over the bridge: GDB would exit
    # mid-response and drop the socket (WinError 10054), surfacing as a spurious
    # BRIDGE_REQUEST_FAILED. Stop the process directly instead.
    exit_aliases = frozenset({"exit", "quit", "q"})
    if params["command"].strip().lower() in exit_aliases:
        sm = _require_ready_session_manager(session_manager)
        gdb_client_id = params["gdb_client_id"]
        message = await sm.stop_gdb(gdb_client_id)
        return {
            "stopped": True,
            "gdb_client_id": gdb_client_id,
            "message": message,
        }

    return await _bridge_call(
        session_manager,
        params["gdb_client_id"],
        "execute",
        {"command": params["command"]},
    )



async def control_interrupt(params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    return await _bridge_call(session_manager, params["gdb_client_id"], "interrupt")


async def control_transcript(params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    return await _bridge_call(session_manager, params["gdb_client_id"], "transcript")



async def control_run_ccs_tcl(params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    s32debugger = _require_ready_session_manager(session_manager)
    return await s32debugger.run_ccs_tcl_script(params["tcl_script_path"])


# ==========================================================================
# Active handlers (inspect)
# ==========================================================================

async def inspect_installation_path(_params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    session_manager = _require_session_manager(session_manager)
    return session_manager.describe_installation_state()


async def inspect_debug_processes(_params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    s32debugger = _require_ready_session_manager(session_manager)
    discovered = await s32debugger.discover_debug_processes()

    # Flag orphaned processes: found on the host but not tracked by any active
    # managed session, so the agent can adopt or stop them before starting one.
    has_running_processes = bool(
        (discovered.get("gdb_processes") or [])
        or discovered.get("gta_pid") is not None
        or discovered.get("ccs_pid") is not None
    )
    if has_running_processes and not s32debugger.is_active_session:
        gdb_count = len(discovered.get("gdb_processes") or [])
        discovered["orphaned_processes"] = True
        discovered["warning"] = (
            "Debug processes are already running on this host "
            f"(gdb_clients={gdb_count}, "
            f"gta_pid={discovered.get('gta_pid')}, "
            f"ccs_pid={discovered.get('ccs_pid')}), "
            "but this MCP server has no active managed debug session tracking them. "
            "These processes were likely started outside this session (e.g. a previous "
            "run or another agent). Review them and stop the stale processes before "
            "starting a new debug session to avoid conflicts."
        )
    else:
        discovered["orphaned_processes"] = False

    return discovered


async def inspect_gdb_client_status(params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    s32debugger = _require_ready_session_manager(session_manager)
    return s32debugger.get_gdb_client_status(params["gdb_client_id"])


async def inspect_gdb_server(_params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    s32debugger = _require_ready_session_manager(session_manager)
    return await s32debugger.get_gdb_server_status()


async def inspect_installed_gdbs(_params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    s32debugger = _require_ready_session_manager(session_manager)
    return s32debugger.list_installed_gdbs()


async def inspect_compatible_version(_params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    """Return static version/compatibility information for this MCP server.

    This handler intentionally performs no I/O and never fails: it reports the
    current MCP server identity/version together with the minimum S32Debugger
    release this MCP instance is validated against. The ``compatibility`` string
    is composed from the live constants so the machine-readable fields and the
    human-readable message can never drift apart.
    """
    return {
        "mcp_server_name": MCP_SERVER_NAME,
        "mcp_server_version": MCP_SERVER_VERSION,
        "min_compatible_debugger_version": _MIN_COMPATIBLE_DEBUGGER_VERSION,
        "compatibility": (
            f"This instance of the S32Debugger MCP server (version "
            f"{MCP_SERVER_VERSION}) is only guaranteed to work correctly with "
            f"S32Debugger "
            f"{_MIN_COMPATIBLE_DEBUGGER_VERSION} version or higher. Debugger releases "
            f"older than {_MIN_COMPATIBLE_DEBUGGER_VERSION} are not supported "
            f"and may fail or behave unexpectedly."
        ),
    }



# ==========================================================================
# Active handlers (generate)
# ==========================================================================

async def generate_gdb_config_file(params: dict[str, Any], session_manager: S32DebuggerSessionManager | None = None) -> Any:
    s32debugger = _require_ready_session_manager(session_manager)
    return await s32debugger.generate_config_from_template(
        soc_family=params["soc_family"],
        script_type=params["script_type"],
        template_name=params["template_name"],
        output_name=params.get("output_name"),
        bridge_port=params["port"],
        overwrite=params.get("overwrite", False),
        PROBE_IP=params.get("probe_ip"),
        SOC_NAME=params.get("soc_name"),
        CORE_NAME=params.get("core_name"),
        CORE_ID=params.get("core_id"),
        CLUSTER_ID=params.get("cluster_id"),
        LOCKSTEP=params.get("lockstep"),
        JTAG_SPEED=params.get("jtag_speed"),
        GDB_SERVER_PORT=params.get("gdb_server_port"),
        CCS_IP=params.get("ccs_ip"),
        CCS_PORT=params.get("ccs_port"),
        IS_LOGGING_ENABLED=params.get("is_logging_enabled"),
        FILE_DEBUG=params.get("file_debug"),
        INIT_SCRIPT=params.get("init_script"),
        SECURE_TYPE=params.get("secure_type"),
        SECURE_KEY=params.get("secure_key"),
        LIFECYCLE=params.get("lifecycle"),
        RESET_TYPE=params.get("reset_type"),
        RESET_DELAY=params.get("reset_delay"),
        REMOTE_TIMEOUT=params.get("remote_timeout"),
        GDB_TIMEOUT=params.get("gdb_timeout"),
        RESULTEXCEPTION=params.get("resultexception"),
        NON_STOP_MODE=params.get("non_stop_mode"),
    )
