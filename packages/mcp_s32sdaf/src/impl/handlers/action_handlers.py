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

"""Component-local action handlers for the S32SDAF search-first surface.

Handlers follow the shared action mechanism from ``nxp.mcp.shared.action``:
each handler receives a validated ``params`` object and an optional component
``session_manager``, returns a plain result payload on success, and raises
``ActionExecutionError`` on any precondition / validation / execution failure.
The shared dispatcher maps those onto the uniform ``ActionOutcome`` envelope
(``{success, result}`` or ``{success, error:{code, message, details}}``), which
is the standardized request/response contract across the whole MCP.

Business logic (installation discovery, CLI execution, validation) lives in
``nxp.mcp.s32sdaf.impl.volkano_core``; this module only orchestrates it and
shapes results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError, errors
from nxp.mcp.s32sdaf.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32sdaf.impl import volkano_core as vc

logger = logging.getLogger(MCP_SERVER_NAME)

# Protocol-facing error codes, sourced from the shared error registry so a
# single numeric code has exactly one meaning across the whole MCP layer.
_INVALID_PARAMS_CODE = errors.INVALID_PARAMS       # bad / missing input parameters
_PRECONDITION_CODE = errors.FORWARD_ERROR          # environment / installation precondition failed
_EXECUTION_FAILED_CODE = errors.EXECUTION_FAILED   # volkano.exe ran but reported a failure
_BLOCKED_CODE = errors.CONFIRMATION_REQUIRED       # destructive op blocked pending confirmation



@dataclass(frozen=True)
class S32SdafSessionManager:
    """Optional runtime state for S32SDAF action handlers.

    Lets the server pre-configure the Volkano installation folder so agents do
    not have to repeat it on every call. Passed to handlers as the
    ``session_manager`` argument by the shared dispatcher.
    """

    volkano_folder: Optional[str] = None


# ---------------------------------------------------------------------------
# Shared handler helpers
# ---------------------------------------------------------------------------

def _invalid_params(message: str, *, required: Optional[list[str]] = None, **extra: Any) -> ActionExecutionError:
    details: dict[str, Any] = {"message": message}
    if required:
        details["required"] = required
    details.update(extra)
    return ActionExecutionError(_INVALID_PARAMS_CODE, "INVALID_PARAMS", error_details=details)


def _validate_file_path(path_str: str, param_name: str) -> Path:
    """Resolve a user-supplied file path and confirm it points at a real file.

    Normalizes ".." segments / symlinks via resolve() and requires the target
    to exist and be a regular file (not a directory). No allow-list of roots is
    enforced: this is a local operator tool, so the file is read with the
    operator's own privileges and confining paths to fixed roots would only
    break legitimate custom locations.
    """
    try:
        resolved = Path(path_str).resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise _invalid_params(f"{param_name} could not be resolved: {exc}")
    if not resolved.is_file():
        raise _invalid_params(f"{param_name} is not a regular file: {resolved}")
    return resolved


def _resolve_folder(

    params: dict[str, Any],
    session_manager: Optional[S32SdafSessionManager],
) -> str:
    """Resolve + validate the Volkano installation folder or raise."""
    explicit = params.get("volkano_folder")
    config_path = ""
    if session_manager is not None and isinstance(session_manager.volkano_folder, str):
        config_path = session_manager.volkano_folder or ""
    try:
        folder = vc.resolve_volkano_folder(explicit, config_path)
        vc.validate_volkano_installation(folder)
        return folder
    except (RuntimeError, FileNotFoundError) as exc:
        raise ActionExecutionError(
            _PRECONDITION_CODE,
            "PRECONDITION_FAILED",
            error_details={
                "message": str(exc),
                "hint": "Provide 'volkano_folder' or configure installation_path; run find_installation to locate it.",
            },
        ) from exc


def _run_volkano_result(result: dict, *, warning: Optional[str] = None) -> dict:
    """Map a VolkanoClient result dict onto a standardized success payload,
    or raise ActionExecutionError when volkano.exe reported a failure."""
    output = result.get("output", "")
    if result.get("status") == "error":
        raise ActionExecutionError(
            _EXECUTION_FAILED_CODE,
            "EXECUTION_FAILED",
            error_details={
                "message": output or "volkano.exe reported a failure.",
                "exit_code": result.get("exit_code", -1),
                "command": result.get("command"),
            },
        )
    payload: dict[str, Any] = {
        "output": output,
        "exit_code": result.get("exit_code", 0),
    }
    if result.get("command"):
        payload["command"] = result["command"]
    if warning:
        payload["warning"] = warning
    return payload


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def find_installation(
    params: dict[str, Any],
    session_manager: Optional[S32SdafSessionManager] = None,
) -> Any:
    """List Volkano installations under C:/NXP/S32DS*, C:/NXP/S32SDAF*, C:/NXP/SDAF*, and C:/NXP/S32DBG*."""

    found = vc.find_volkano_installations()
    installations = [
        {
            "volkano_folder": c["volkano_folder"],
            "install_root": c["install_root"],
            "version": c["version_label"],
        }
        for c in found
    ]
    return {
        "installations": installations,
        "recommended": installations[0]["volkano_folder"] if installations else None,
        "count": len(installations),
    }


async def discover(
    params: dict[str, Any],
    session_manager: Optional[S32SdafSessionManager] = None,
) -> Any:
    """Discover all UIDs and keys registered on the smart card."""
    folder = _resolve_folder(params, session_manager)
    client = vc.VolkanoClient(folder)
    result = await client.run_volkano(["-cmd", "discover"], params.get("password"))
    return _run_volkano_result(result)


async def register_key(
    params: dict[str, Any],
    session_manager: Optional[S32SdafSessionManager] = None,
) -> Any:
    """Register a key for a device UID using the appropriate Volkano command."""
    folder = _resolve_folder(params, session_manager)

    key_type = params.get("key_type")
    uid = params.get("uid")
    key = params.get("key")
    keybin = params.get("keybin")
    oid = params.get("oid")
    key_index = params.get("key_index")
    adk2_key_type = params.get("adk2_key_type")
    password = params.get("password")

    normalized_key_type = vc.normalize_register_key_type(key_type)
    if normalized_key_type is None:
        raise _invalid_params(
            f"Unsupported key_type '{key_type}'. Supported values: "
            f"{', '.join(sorted(vc.REGISTER_KEY_TYPES))}.",
            required=["key_type"],
        )

    command = vc.REGISTER_KEY_TYPES[normalized_key_type]
    uid_err = vc.validate_uid(uid or "")
    if uid_err:
        raise _invalid_params(uid_err, required=["uid"])

    args = ["-cmd", command, "-uid", uid]

    if normalized_key_type == "ADKP":
        if not key and not keybin:
            raise _invalid_params(
                "Provide 'key' (hex string) or 'keybin' (path to binary file).",
                required=["key", "keybin"],
            )
        if key and keybin:
            raise _invalid_params("Pass either 'key' or 'keybin' for ADKP, not both.")
        if key:
            key_err = vc.validate_hex_param("key", key)
            if key_err:
                raise _invalid_params(key_err)
            # uid is a hex string: 16 hex chars = 8-byte UID, 32 hex chars =
            # 16-byte UID. ADKP is twice the UID length in bytes, expressed as
            # hex chars: 8-byte UID -> 16-byte ADKP -> 32 hex chars;
            # 16-byte UID -> 32-byte ADKP -> 64 hex chars.
            expected_key_len = 32 if len(uid) == 16 else 64

            if len(key) != expected_key_len:
                raise _invalid_params(
                    f"Plain ADKP key must be {expected_key_len} hex characters "
                    f"for a {len(uid) // 2}-byte UID. For a wrapped ADKP, use keybin."
                )
            args += ["-key", key]
        if keybin:
            resolved_keybin = _validate_file_path(keybin, "keybin")
            args += ["-keybin", str(resolved_keybin)]


    elif normalized_key_type == "ODAK":
        uid16_err = vc.validate_uid_16_bytes(uid)
        if uid16_err:
            raise _invalid_params(uid16_err, required=["uid"])
        if not key:
            raise _invalid_params(
                "ODAK registration requires the wrapped key as a 512-hex-character string.",
                required=["key"],
            )
        if keybin:
            raise _invalid_params("keybin is not supported for ODAK registration.")
        wrapped_err = vc.validate_wrapped_key("key", key)
        if wrapped_err:
            raise _invalid_params(wrapped_err)
        args += ["-key", key]

    elif normalized_key_type == "ADK1":
        uid16_err = vc.validate_uid_16_bytes(uid)
        if uid16_err:
            raise _invalid_params(uid16_err, required=["uid"])
        if not oid:
            raise _invalid_params("ADK1 registration requires a 16-byte OID value.", required=["oid"])
        oid_err = vc.validate_oid_16_bytes(oid)
        if oid_err:
            raise _invalid_params(oid_err)
        if not key:
            raise _invalid_params(
                "ADK1 registration requires the wrapped key as a 512-hex-character string.",
                required=["key"],
            )
        if keybin:
            raise _invalid_params("keybin is not supported for ADK1 registration.")
        wrapped_err = vc.validate_wrapped_key("key", key)
        if wrapped_err:
            raise _invalid_params(wrapped_err)
        key_index_err = vc.validate_key_index(key_index)
        if key_index_err:
            raise _invalid_params(key_index_err, required=["key_index"])
        args += ["-oid", oid, "-key", key, "-key_index", str(key_index)]

    elif normalized_key_type == "ADK2":
        uid16_err = vc.validate_uid_16_bytes(uid)
        if uid16_err:
            raise _invalid_params(uid16_err, required=["uid"])
        if not oid:
            raise _invalid_params("ADK2 registration requires a 16-byte OID value.", required=["oid"])
        oid_err = vc.validate_oid_16_bytes(oid)
        if oid_err:
            raise _invalid_params(oid_err)
        if not key:
            raise _invalid_params(
                "ADK2 registration requires the wrapped key as a 512-hex-character string.",
                required=["key"],
            )
        if keybin:
            raise _invalid_params("keybin is not supported for ADK2 registration.")
        wrapped_err = vc.validate_wrapped_key("key", key)
        if wrapped_err:
            raise _invalid_params(wrapped_err)
        key_index_err = vc.validate_key_index(key_index)
        if key_index_err:
            raise _invalid_params(key_index_err, required=["key_index"])
        normalized_adk2_key_type = vc.normalize_adk2_key_type(adk2_key_type)
        if normalized_adk2_key_type is None:
            raise _invalid_params(
                "ADK2 registration requires adk2_key_type set to 'AES' or 'ECC'.",
                required=["adk2_key_type"],
            )
        args += ["-oid", oid, "-key", key, "-key_index", str(key_index), "-key_type", normalized_adk2_key_type]

    elif normalized_key_type in {"kUID", "kUID_RF", "kUID_PRE_FA"}:
        if not key:
            raise _invalid_params(
                f"{normalized_key_type} registration requires the wrapped key as a 512-hex-character string.",
                required=["key"],
            )
        if keybin:
            raise _invalid_params(f"keybin is not supported for {normalized_key_type} registration.")
        wrapped_err = vc.validate_wrapped_key("key", key)
        if wrapped_err:
            raise _invalid_params(wrapped_err)
        args += ["-key", key]

    client = vc.VolkanoClient(folder)
    result = await client.run_volkano(args, password)
    return _run_volkano_result(result, warning=vc.applet_warning(normalized_key_type))


async def delete_record(
    params: dict[str, Any],
    session_manager: Optional[S32SdafSessionManager] = None,
) -> Any:
    """Delete a UID record and all its associated keys (irreversible)."""
    folder = _resolve_folder(params, session_manager)
    uid = params.get("uid")
    uid_err = vc.validate_uid(uid or "")
    if uid_err:
        raise _invalid_params(uid_err, required=["uid"])

    if not params.get("confirmed_by_user", False):
        raise ActionExecutionError(
            _BLOCKED_CODE,
            "CONFIRMATION_REQUIRED",
            error_details={
                "message": (
                    f"Deletion of UID '{uid}' is blocked. This operation is irreversible. "
                    "Call again with confirmed_by_user=true after explicit user approval."
                ),
                "uid": uid,
            },
        )

    client = vc.VolkanoClient(folder)
    result = await client.run_volkano(["-cmd", "delete_record", "-uid", uid], params.get("password"))
    return _run_volkano_result(
        result,
        warning=(
            "This command requires a smart card with applet version 1.4+. "
            "If the card is older, Volkano may return unsupported-operation style errors."
        ),
    )


async def export_wrapkey(
    params: dict[str, Any],
    session_manager: Optional[S32SdafSessionManager] = None,
) -> Any:
    """Export the public wrapping key from the smart card."""
    folder = _resolve_folder(params, session_manager)
    client = vc.VolkanoClient(folder)
    result = await client.run_volkano(["-cmd", "export_wrapkey"], params.get("password"))
    return _run_volkano_result(result)


async def wrap_key(
    params: dict[str, Any],
    session_manager: Optional[S32SdafSessionManager] = None,
) -> Any:
    """Wrap a plain key using the smart card's public wrapping key."""
    folder = _resolve_folder(params, session_manager)

    utils_exe = Path(folder) / "volkano_utils.exe"
    if not utils_exe.exists():
        raise ActionExecutionError(
            _PRECONDITION_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": f"volkano_utils.exe not found at {utils_exe}."},
        )

    plain_key = params.get("plain_key")
    public_key = params.get("public_key")
    plain_err = vc.validate_hex_param("plain_key", plain_key or "")
    if plain_err:
        raise _invalid_params(plain_err, required=["plain_key"])
    public_err = vc.validate_hex_param("public_key", public_key or "")
    if public_err:
        raise _invalid_params(public_err, required=["public_key"])

    client = vc.VolkanoClient(folder)
    result = await client.wrap_key(plain_key, public_key)
    return _run_volkano_result(result)


async def update_pwd(
    params: dict[str, Any],
    session_manager: Optional[S32SdafSessionManager] = None,
) -> Any:
    """Set the first smart-card user password, or update an existing one.

    Uses ``volkano.exe -cmd update_pwd -new_pwd <new_password>``. For a
    first-password initialization on a newly initialized card, no current
    password is supplied. For an update of an already-provisioned card, the
    current password is mandatory and is passed as ``-pw <current_password>``.

    Note: VolkanoClient.run_volkano already prepends ``-pw <password>`` when a
    password argument is given, so the current password is forwarded through
    that argument rather than appended to args (this avoids a duplicate -pw).
    """
    folder = _resolve_folder(params, session_manager)

    new_password = params.get("new_password")
    current_password = params.get("current_password")

    new_err = vc.validate_password("new_password", new_password or "")
    if new_err:
        raise _invalid_params(new_err, required=["new_password"])

    if current_password is not None:
        current_err = vc.validate_password("current_password", current_password)
        if current_err:
            raise _invalid_params(current_err)

    args = ["-cmd", "update_pwd", "-new_pwd", new_password]

    client = vc.VolkanoClient(folder)
    result = await client.run_volkano(args, current_password)
    return _run_volkano_result(
        result,
        warning=(
            "The smart-card user password was changed. All future authenticated "
            "Volkano operations must use the new password."
        ),
    )


async def get_response(
    params: dict[str, Any],
    session_manager: Optional[S32SdafSessionManager] = None,
) -> Any:
    """Perform challenge-response authentication for a registered UID."""

    folder = _resolve_folder(params, session_manager)

    uid = params.get("uid")
    challenge = params.get("challenge")
    key = params.get("key")
    oid = params.get("oid")
    scheme_id = params.get("scheme_id")
    key_name = params.get("key_name")
    password = params.get("password")

    uid_err = vc.validate_uid(uid or "")
    if uid_err:
        raise _invalid_params(uid_err, required=["uid"])

    challenge_err = vc.validate_hex_param("challenge", challenge or "")
    if challenge_err:
        raise _invalid_params(
            f"Provide the hex challenge string from the target device. {challenge_err}",
            required=["challenge"],
        )

    if key is not None:
        key = str(key).strip()
        if not key:
            raise _invalid_params(
                "If provided, key must be a non-empty Volkano key selector or discover-returned "
                f"instance name. Symbolic selectors: {', '.join(sorted(vc.GET_RESPONSE_KEY_TYPES))}.",
            )
        key = vc.normalize_get_response_key_selector(key)
        key_err = vc.validate_get_response_key_name(key)
        if key_err:
            raise _invalid_params(key_err)
        if not vc.looks_like_known_get_response_key(key):
            raise _invalid_params(
                f"Unrecognized key selector '{key}'. Use a symbolic selector "
                f"({', '.join(sorted(vc.GET_RESPONSE_KEY_TYPES))}) or an exact instance "
                "name returned by discover (for example ADK1_1)."
            )

    if key is not None and key_name is not None:
        raise _invalid_params(
            "Pass either 'key' or 'key_name', not both; they are equivalent, so supply exactly one."
        )

    if key_name is not None:
        key_name_err = vc.validate_get_response_key_name(key_name)
        if key_name_err:
            raise _invalid_params(key_name_err)

    if oid is not None:
        oid_err = vc.validate_hex_param("oid", oid)
        if oid_err:
            raise _invalid_params(oid_err)

    if scheme_id is not None and scheme_id not in (1, 2, 3):
        raise _invalid_params("scheme_id must be one of 1, 2, or 3.")

    if key is not None:
        key_upper = key.upper()
        if (key_upper == "ADK1" or key_upper.startswith("ADK1_")) and not oid:
            raise _invalid_params(
                "ADK1-backed get_response requires an OID value. "
                "Use the concrete key name returned by discover (for example ADK1_1).",
                required=["oid"],
            )

    args = ["-cmd", "get_response", "-uid", uid, "-chlg", challenge]
    if key_name:
        args += ["-key", key_name]
    elif key:
        args += ["-key", key]
    if oid:
        args += ["-oid", oid]
    if scheme_id is not None:
        args += ["-scheme_id", str(scheme_id)]

    client = vc.VolkanoClient(folder)
    result = await client.run_volkano(args, password)

    if result.get("status") == "error":
        output = result.get("output", "") or ""
        hint = None
        if "Missing the challenge" in output and challenge:
            if not key and not key_name:
                hint = (
                    "The challenge passed local validation but this flow may require an explicit "
                    "key selector. Try key='ADKP', key='ADK1' (with oid), or a kUID selector."
                )
            else:
                hint = (
                    "The challenge passed local validation. This usually indicates a wrapper/CLI "
                    "argument mismatch rather than a malformed challenge."
                )
        elif "Missing key type" in output and not key and not key_name:
            hint = (
                "The installed volkano.exe requires a key selector for this flow. "
                "Try key='ADKP', key='ADK1' (with oid), or a kUID selector."
            )
        raise ActionExecutionError(
            _EXECUTION_FAILED_CODE,
            "EXECUTION_FAILED",
            error_details={
                "message": output or "volkano.exe reported a failure.",
                "exit_code": result.get("exit_code", -1),
                "command": result.get("command"),
                **({"diagnostic_hint": hint} if hint else {}),
            },
        )

    # The error case is already handled above (with diagnostic hints); at this
    # point the result is a success, so _run_volkano_result only formats the
    # success payload and will not raise.
    return _run_volkano_result(result)


