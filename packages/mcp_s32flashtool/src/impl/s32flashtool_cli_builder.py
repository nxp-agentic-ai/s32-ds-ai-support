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

"""S32FlashTool CLI command string builder.

Converts a structured action/cli_request payload into an S32FlashTool CLI executable
command line. This module is intentionally self-contained: input validation is
performed by the action layer (per-operation JSON schemas declared on each
ActionExecutable), so this builder only maps validated fields onto CLI flags.

The public entry points mirror the historical API:

* build_s32flashtool_cli_args     -> list[str] of CLI arguments (no executable)
* build_s32flashtool_command      -> list[str] including the executable path
* build_s32flashtool_command_string -> single command-line string (display only)
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Optional

# The default executable name is shared via the dependency-free constants
# module so the builder does not couple to the CLI client implementation (which
# would risk a circular import). The value is resolved once at import time from
# ``os.name``.
from nxp.mcp.s32flashtool.impl.constants import CLI_EXE_NAME

_DEFAULT_EXECUTABLE = CLI_EXE_NAME


__all__ = [
    "S32FlashToolCliBuilderError",
    "build_s32flashtool_cli_args",
    "build_s32flashtool_command",
    "build_s32flashtool_command_argv",
    "build_s32flashtool_command_string",
]


class S32FlashToolCliBuilderError(ValueError):
    """Raised when an action object cannot be converted into CLI args."""


# Builder-level re-validation of hex_data. The action-layer JSON schema already
# constrains hex_data with the same pattern; the builder re-checks ONLY hex_data
# here as a targeted extra guard against a malformed byte string reaching the -x
# flag. NOTE: this is not a blanket guarantee for every value-bearing field -
# other free-form values (addr, size, entrypoint, waitboot) are NOT re-validated
# by the builder and rely on the action-layer JSON schema; a caller invoking the
# builder outside the validated dispatch path must validate those itself.
_HEX_DATA_RE = re.compile(r"^0x([0-9A-Fa-f]{2})+$")


def _validate_hex_data(value: str) -> str:
    if not isinstance(value, str) or not _HEX_DATA_RE.match(value):
        raise S32FlashToolCliBuilderError(f"Invalid hex_data format: {value!r}")
    return value



_ACTION_TO_FLAG = {
    "ping_cli": "-ping",
    "mcuid_cli": "-mcuid",
    "fid_cli": "-fid",
    "fread_cli": "-fread",
    "fwrite_cli": "-fwrite",
    "ferase_cli": "-ferase",
    "fprogram_cli": "-fprogram",
    "fverify_cli": "-fverify",
    "boot_cli": "-boot",
    "dcd_cli": "-dcd",
    "fcrc_cli": "-fcrc",
    "ethernet_prepare": None,
    "list_interfaces_cli": None,
}

_OPERATION_TO_ACTION = {
    "ping_cli": "ping_cli",
    "mcuid_cli": "mcuid_cli",
    "fid_cli": "fid_cli",
    "fread_cli": "fread_cli",
    "fwrite_cli": "fwrite_cli",
    "ferase_cli": "ferase_cli",
    "fprogram_cli": "fprogram_cli",
    "fverify_cli": "fverify_cli",
    "boot_cli": "boot_cli",
    "dcd_cli": "dcd_cli",
    "fcrc_cli": "fcrc_cli",
    "list_interfaces_cli": "list_interfaces_cli",
}


def _append_if_present(args: list[str], flag: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        if value:
            args.append(flag)
        return
    args.extend([flag, str(value)])


def _require(input_obj: dict[str, Any], key: str) -> Any:
    if key not in input_obj or input_obj[key] in (None, ""):
        raise S32FlashToolCliBuilderError(f"Missing required input field: {key}")
    return input_obj[key]


def _normalize_path(value: str) -> str:
    return str(Path(value))


def _validate_file_xor_hex(input_obj: dict[str, Any], action: str) -> None:
    has_file = bool(input_obj.get("file"))
    has_hex = bool(input_obj.get("hex_data"))
    if action in {"fwrite_cli", "fprogram_cli", "fverify_cli"} and has_file == has_hex:
        raise S32FlashToolCliBuilderError(
            f"Action '{action}' requires exactly one of 'file' or 'hex_data'."
        )


def _serialize_transport(port_obj: dict[str, Any]) -> str:
    if not isinstance(port_obj, dict):
        raise S32FlashToolCliBuilderError("input.transport must be a structured object")

    kind = port_obj.get("kind")
    if kind == "uart":
        parts = [str(port_obj["device"])]
        if port_obj.get("baudrate") is not None:
            parts.append(str(port_obj["baudrate"]))
        if port_obj.get("driver") is not None:
            parts.append(str(port_obj["driver"]))
        return ",".join(parts)

    if kind == "can":
        # The CAN endpoint is a positional CSV: adapter,channel,serial.
        # 'serial' is the third positional field, so it can only be expressed
        # once 'channel' (the second field) is present. Emitting an empty
        # channel slot (adapter,,serial) is an undocumented convention that the
        # CLI grammar does not define; if the CLI does not accept an empty slot
        # the command would silently target the wrong adapter configuration.
        # Reject the ambiguous combination explicitly instead.
        channel = port_obj.get("channel")
        serial = port_obj.get("serial")
        if serial is not None and channel is None:
            raise S32FlashToolCliBuilderError(
                "CAN transport 'serial' requires 'channel' to be set as well; "
                "the CLI endpoint is a positional CSV (adapter,channel,serial) "
                "and does not accept an empty channel slot."
            )
        parts = [str(port_obj["adapter"])]
        if channel is not None:
            parts.append(str(channel))
        if serial is not None:
            parts.append(str(serial))
        return ",".join(parts)

    if kind == "ethernet":
        base = (
            f'"{port_obj["adapter"]},{port_obj["local_ip"]},'
            f'{port_obj["dhcp_start"]},{port_obj["dhcp_end"]}"'
        )
        suffixes: list[str] = []
        if port_obj.get("enable_tftp"):
            suffixes.append("t")
        if port_obj.get("enable_dhcp"):
            suffixes.append("d")
        return ",".join([base, *suffixes]) if suffixes else base

    raise S32FlashToolCliBuilderError(f"Unsupported port kind: {kind}")


def _normalize_cli_request_to_action_payload(cli_request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(cli_request, dict):
        raise S32FlashToolCliBuilderError("cli_request must be a dictionary")

    operation = cli_request.get("operation")
    if operation not in _OPERATION_TO_ACTION:
        raise S32FlashToolCliBuilderError(f"Unsupported cli_request.operation: {operation}")

    input_payload = cli_request.get("input")
    if not isinstance(input_payload, dict):
        raise S32FlashToolCliBuilderError("cli_request.input must be a dictionary")

    return {
        "action": _OPERATION_TO_ACTION[operation],
        "msg_id": cli_request.get("msg_id", "1"),
        "input": input_payload,
    }


def build_s32flashtool_cli_args(action_obj: dict[str, Any]) -> list[str]:
    if not isinstance(action_obj, dict):
        raise S32FlashToolCliBuilderError("action_obj must be a dictionary")

    if action_obj.get("action") == "cli_build_command":
        outer_input = action_obj.get("input")
        if not isinstance(outer_input, dict):
            raise S32FlashToolCliBuilderError("cli_build_command input must be a dictionary")
        cli_request = outer_input.get("cli_request")
        normalized_action_obj = _normalize_cli_request_to_action_payload(cli_request)
        return build_s32flashtool_cli_args(normalized_action_obj)

    action = action_obj.get("action")
    if action not in _ACTION_TO_FLAG:
        raise S32FlashToolCliBuilderError(f"Unsupported action: {action}")

    input_obj = action_obj.get("input")
    if not isinstance(input_obj, dict):
        raise S32FlashToolCliBuilderError("action_obj['input'] must be a dictionary")

    args: list[str] = []

    if input_obj.get("xosc") is not None:
        args.extend(["-xosc", str(input_obj["xosc"])])
    if input_obj.get("xoscmode") is not None:
        args.extend(["-xoscmode", str(input_obj["xoscmode"])])
    if input_obj.get("target") is not None:
        args.extend(["-t", _normalize_path(input_obj["target"])])
    if input_obj.get("secure_bootloader"):
        args.append("-s")
    if input_obj.get("algorithm") is not None:
        args.extend(["-a", str(input_obj["algorithm"])])
    if input_obj.get("interface") is not None:
        args.extend(["-i", str(input_obj["interface"])])
    if input_obj.get("transport") is not None:
        args.extend(["-p", _serialize_transport(input_obj["transport"])])
    if input_obj.get("folder") is not None:
        args.extend(["-d", _normalize_path(input_obj["folder"])])

    action_flag = _ACTION_TO_FLAG[action]

    if action == "ethernet_prepare":
        if input_obj.get("interface") != "ethernet":
            raise S32FlashToolCliBuilderError(
                "Action 'ethernet_prepare' requires input.interface == 'ethernet'."
            )
        if input_obj.get("log_comm"):
            args.extend(["-l", "c"])
        return args

    if action == "list_interfaces_cli":
        args.extend(["-p", "?"])
        return args

    if action_flag is None:
        raise S32FlashToolCliBuilderError(f"No CLI flag mapping defined for action: {action}")

    if action == "boot_cli":
        boot_file = _require(input_obj, "file")
        args.extend([action_flag, _normalize_path(boot_file)])
    elif action == "dcd_cli":
        dcd_file = _require(input_obj, "file")
        args.extend([action_flag, _normalize_path(dcd_file)])
    else:
        args.append(action_flag)

    if action in {"fread_cli", "fwrite_cli", "ferase_cli", "fprogram_cli", "fverify_cli", "boot_cli", "fcrc_cli"}:
        _append_if_present(args, "-addr", input_obj.get("addr"))

    if action in {"fread_cli", "fcrc_cli"}:
        _require(input_obj, "size")

    if action in {"fread_cli", "fwrite_cli", "ferase_cli", "fprogram_cli", "fverify_cli", "fcrc_cli"}:
        _append_if_present(args, "-size", input_obj.get("size"))

    if action == "fread_cli":
        if input_obj.get("binary_output"):
            args.append("-b")
        if input_obj.get("file") is not None:
            args.extend(["-f", _normalize_path(input_obj["file"])])

    if action in {"fwrite_cli", "fprogram_cli", "fverify_cli"}:
        _validate_file_xor_hex(input_obj, action)
        if input_obj.get("file") is not None:
            args.extend(["-f", _normalize_path(input_obj["file"])])
        if input_obj.get("hex_data") is not None:
            args.extend(["-x", _validate_hex_data(str(input_obj["hex_data"]))])


    if action == "ferase_cli" and input_obj.get("file") is not None:
        args.extend(["-f", _normalize_path(input_obj["file"])])

    if action == "fcrc_cli" and input_obj.get("file") is not None:
        args.extend(["-f", _normalize_path(input_obj["file"])])

    if action == "boot_cli":
        _append_if_present(args, "-entrypoint", input_obj.get("entrypoint"))
        if input_obj.get("frb") is not None:
            frb = input_obj["frb"]
            if not isinstance(frb, list) or len(frb) != 3:
                raise S32FlashToolCliBuilderError("'frb' must be a list of exactly 3 values")
            args.extend(["-frb", ",".join(str(x) for x in frb)])

    if input_obj.get("partition") is not None:
        args.extend(["-partition", str(input_obj["partition"])])

    if action == "fprogram_cli" and input_obj.get("noverify"):
        args.append("-noverify")

    if input_obj.get("log_comm"):
        args.extend(["-l", "c"])

    if input_obj.get("waitboot") is not None:
        args.extend(["-waitboot", str(input_obj["waitboot"])])

    if input_obj.get("boot_default_baudrate"):
        args.append("-boot_default_baudrate")

    return args


def build_s32flashtool_command(
    action_obj: dict[str, Any],
    executable: Optional[str] = None,
) -> list[str]:
    """Return the argv list (executable + args). Safe for subprocess.exec* calls.

    ``executable`` defaults to the platform-appropriate binary name
    (``S32FlashTool.exe`` on Windows, ``S32FlashTool`` elsewhere), resolved from
    the module-level ``_DEFAULT_EXECUTABLE`` constant. Using ``None`` as the
    signature default (instead of the constant directly) lets callers pass
    ``None`` explicitly to request the default. When the payload is a
    ``cli_build_command`` carrying an ``sft_folder``, the executable is resolved
    to that installation's ``bin`` directory.
    """

    if executable is None:
        executable = _DEFAULT_EXECUTABLE
    if action_obj.get("action") == "cli_build_command":
        outer_input = action_obj.get("input", {})
        sft_folder = outer_input.get("sft_folder")
        if sft_folder:
            executable = str(Path(sft_folder) / "bin" / _DEFAULT_EXECUTABLE)
    return [executable, *build_s32flashtool_cli_args(action_obj)]


# Backwards-compatible alias documenting that this returns an argv list.
build_s32flashtool_command_argv = build_s32flashtool_command


def build_s32flashtool_command_string(
    action_obj: dict[str, Any],
    executable: Optional[str] = None,
) -> str:
    """Return a single command-line string for DISPLAY purposes only.

    Do not pass the returned string to ``shell=True`` or re-split it and feed it
    to a subprocess; use :func:`build_s32flashtool_command` (argv list) for
    execution. Quoting is done with :func:`shlex.join` on POSIX systems and
    :func:`subprocess.list2cmdline` on Windows so the string is faithful to the
    host platform instead of always using the Windows-only quoting rules.
    """
    argv = build_s32flashtool_command(action_obj, executable=executable)
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


