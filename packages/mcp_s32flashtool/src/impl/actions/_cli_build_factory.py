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

"""Shared factory for the cli_build_* action executables.

Every cli_build_<operation> action routes to the same handler
(``cli_build_command``) and shares an installation-folder parameter, but each
exposes the input schema that is specific to its S32FlashTool CLI operation.
The per-operation input properties mirror the ``*_cli.schema.json`` contracts
(which themselves reference ``common_properties.schema.json``); they are kept
here as a single shared property library so the individual action files stay
thin while still producing one explicit, distinctly-typed ``ActionExecutable``
per operation (the debugger-style direct pattern).
"""

from __future__ import annotations

from typing import Any

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter
from nxp.mcp.s32flashtool.impl.handlers import (
    cli_build_command_handler
)



# Shared property definitions mirroring common_properties.schema.json#/$defs.
# Kept minimal but faithful to the source so each operation's input schema is
# self-describing rather than an opaque object.
_PROPS: dict[str, dict[str, Any]] = {
    "target": {
        "type": "string",
        "description": "Path to target application binary (-t). Absolute path preferred.",
    },
    "secure_bootloader": {
        "type": "boolean",
        "default": False,
        "description": "Use secure serial bootloader image (-s).",
    },
    "xosc": {
        "type": "string",
        "description": "External oscillator frequency (-xosc), e.g. 20M, 40000K.",
    },
    "xoscmode": {
        "type": "string",
        "enum": ["extal_single", "extal_differential", "xtal_inv", "xtal"],
        "description": "Oscillator mode (-xoscmode).",
    },
    "interface": {
        "type": "string",
        "enum": ["uart", "can", "ethernet"],
        "description": "Communication interface (-i).",
    },
    "transport": {
        "oneOf": [
            {
                "type": "object",
                "description": "UART transport parameters.",
                "properties": {
                    "kind": {"const": "uart"},
                    "device": {
                        "type": "string",
                        "description": "COM35 or /dev/ttyUSB0",
                    },
                    "baudrate": {
                        "type": "integer",
                        "enum": [115200, 460800, 921600, 3686400, 1843200],
                    },
                    "driver": {"type": "string", "enum": ["ftdi"]},
                },
                "required": ["kind", "device"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "description": "CAN transport parameters.",
                "properties": {
                    "kind": {"const": "can"},
                    "adapter": {
                        "type": "string",
                        "enum": ["vector", "ixxat", "kvaser"],
                    },
                    "channel": {"type": ["integer", "string"]},
                    "serial": {"type": ["integer", "string"]},
                },
                "required": ["kind", "adapter"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "description": "Ethernet transport parameters.",
                "properties": {
                    "kind": {"const": "ethernet"},
                    "adapter": {
                        "type": "string",
                        "description": "Adapter name. May contain spaces, commas, and # characters.",
                    },
                    "local_ip": {"type": "string", "format": "ipv4"},
                    "dhcp_start": {"type": "string", "format": "ipv4"},
                    "dhcp_end": {"type": "string", "format": "ipv4"},
                    "enable_tftp": {"type": "boolean", "default": False},
                    "enable_dhcp": {"type": "boolean", "default": False},
                },
                "required": ["kind", "adapter", "local_ip", "dhcp_start", "dhcp_end"],
                "additionalProperties": False,
            },
        ],
        "description": "Transport object matching the selected interface (uart/can/ethernet).",
    },

    "log_comm": {
        "type": "boolean",
        "default": False,
        "description": "Enable communication logging (-l c).",
    },
    "waitboot": {
        "type": "string",
        "pattern": "^(0x[0-9A-Fa-f]+|[0-9]+)$",
        "description": "Wait time after sending target binary via serial boot (-waitboot).",
    },
    "boot_default_baudrate": {
        "type": "boolean",
        "default": False,
        "description": "Use default baud rate 115200 for UART-based serial boot (-boot_default_baudrate).",
    },
    "algorithm": {
        "type": "string",
        "description": "Flash algorithm path (-a). May include optional qspi/chip-select suffixes.",
    },
    "addr": {
        "type": "string",
        "pattern": "^(0x[0-9A-Fa-f]+|[0-9]+)$",
        "description": "Address value in decimal or hex (-addr).",
    },
    "size": {
        "type": "string",
        "pattern": "^(0x[0-9A-Fa-f]+|[0-9]+)$",
        "description": "Size value in decimal or hex (-size).",
    },
    "file": {
        "type": "string",
        "description": "File path used with -f, -boot, or -dcd depending on action.",
    },
    "hex_data": {
        "type": "string",
        "pattern": "^0x([0-9A-Fa-f]{2})+$",
        "description": "ASCII hex string for -x. Must start with 0x and have an even number of hex digits.",
    },
    "binary_output": {
        "type": "boolean",
        "default": False,
        "description": "Enable binary output (-b).",
    },
    "partition": {
        "type": "string",
        "enum": ["user", "boot_1", "boot_2"],
        "description": "eMMC partition (-partition).",
    },
    "entrypoint": {
        "type": "string",
        "pattern": "^(0x[0-9A-Fa-f]+|[0-9]+)$",
        "description": "Entrypoint address (-entrypoint).",
    },
    "frb": {
        "type": "array",
        "items": {"type": "string", "pattern": "^(0x[0-9A-Fa-f]+|[0-9]+)$"},
        "minItems": 3,
        "maxItems": 3,
        "description": "FRB thresholds for -frb as [frb0, frb1, frb2].",
    },
    "noverify": {
        "type": "boolean",
        "default": False,
        "description": "Disable verification during programming (-noverify).",
    },
}

# Common property set present on every operation.
_BASE_PROPS = (
    "target",
    "secure_bootloader",
    "xosc",
    "xoscmode",
    "interface",
    "transport",
    "log_comm",
    "waitboot",
    "boot_default_baudrate",
)


def _input_schema(
    properties: tuple[str, ...],
    required: tuple[str, ...],
    one_of: tuple[tuple[str, ...], ...] = (),
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {name: _PROPS[name] for name in properties},
        "required": list(required),
        "additionalProperties": False,
    }
    if one_of:
        schema["oneOf"] = [{"required": list(group)} for group in one_of]
    return schema


# Per-operation input specification: (description, extra_properties, required,
# one_of, related, extra_preconditions). extra_properties are appended to the
# common base set (in schema order). related lists extra action names appended
# to the base cli_execute related action for this specific operation.
# extra_preconditions lists per-operation preconditions appended to the two
# base preconditions (installation path + pinned operation/schema); they carry
# the safety and discovery context that a purely search_actions-driven agent
# would otherwise miss (destructive-flag + confirmation phrase for destructive
# ops, serial-boot-mode expectation, discovery hints for target/algorithm/port,
# and validation-followup guidance). Kept as plain strings so no change to
# ActionContract or its serializer is needed; both `preconditions` and
# `related_actions` are already emitted by to_contract_payload().

_OPERATIONS: dict[str, dict[str, Any]] = {
    "ping_cli": {
        "description": "Build the CLI command to check board connectivity.",
        "extra": (),
        "required": ("target", "interface", "transport"),
        "extra_preconditions": (
            "Board must be connected and in serial boot mode for S32FlashTool communication.",
            "Do not guess `target`, `interface`, or the transport endpoint (COM port / CAN adapter / Ethernet adapter); confirm with the user or via discovery (cli_build_list_interfaces + cli_execute).",
        ),
    },
    "mcuid_cli": {
        "description": "Build the CLI command to retrieve MCU information.",
        "extra": (),
        "required": ("target", "interface", "transport"),
        "related": ("list_platform_files",),
        "extra_preconditions": (
            "Board must be connected and in serial boot mode for S32FlashTool communication.",
            "Use this action to identify the processor when the target family is uncertain before running hardware-specific operations.",
            "Do not guess `target`, `interface`, or the transport endpoint; confirm with the user or via discovery.",
        ),
    },
    "fid_cli": {
        "description": "Build the CLI command to retrieve flash identification data.",
        "extra": ("algorithm",),
        "required": ("target", "interface", "transport", "algorithm"),
        "related": ("list_platform_files", "cli_build_mcuid",),
        "extra_preconditions": (
            "Board must be connected and in serial boot mode.",
            "`algorithm` must match the flash device physically on the board; do not guess it. Use list_platform_files (bin_type='flash') and list_platform_files (bin_type='supported') to pick a legal value.",
            "`target` must match the processor family; use cli_build_mcuid + cli_execute first if the family is uncertain.",
        ),
    },
    "fread_cli": {
        "description": "Build the CLI command to read flash memory.",
        "extra": ("algorithm", "addr", "size", "binary_output", "file", "partition"),
        "required": ("target", "interface", "transport", "algorithm", "addr", "size"),
        "related": ("cli_build_fid", "cli_build_fcrc"),
        "extra_preconditions": (
            "Board must be connected and in serial boot mode.",
            "`target` and `algorithm` must match the processor and flash device; do not guess them.",
            "`addr` and `size` must lie within the flash geometry of the device; consult supported_<platform>_devices.txt via list_platform_files (bin_type='supported').",
            "If `file` is provided, use an absolute path.",
        ),
    },
    "fwrite_cli": {
        "description": "Build the CLI command to write flash memory without erasing it first.",
        "extra": ("algorithm", "addr", "size", "file", "hex_data", "partition"),
        "required": ("target", "interface", "transport", "algorithm", "addr"),
        "one_of": (("file",), ("hex_data",)),
        "related": ("cli_build_ferase", "cli_build_fverify", "cli_build_fcrc", "cli_build_fread"),
        "extra_preconditions": (
            "This operation is DESTRUCTIVE. The caller MUST show the built command to the user and obtain explicit confirmation (recommended phrase: 'yes, write') BEFORE invoking cli_execute.",
            "This writes WITHOUT erasing first; on sector-based flash a stale sector will not be programmed cleanly. Prefer cli_build_fprogram unless you specifically need the write-only path.",
            "Board must be connected and in serial boot mode.",
            "`target` and `algorithm` must match the processor and flash device; do not guess them (use list_platform_files, and cli_build_mcuid + cli_execute if family is uncertain).",
            "`addr` (and effective `size` from `file`/`hex_data`) must lie within the flash geometry; sector-based flash may be affected beyond the exact requested range.",
            "After execution, verify with cli_build_fverify or cli_build_fcrc (compare against the source file).",
        ),
    },
    "ferase_cli": {
        "description": "Build the CLI command to erase a flash block or memory range.",
        "extra": ("algorithm", "addr", "size", "file"),
        "required": ("target", "interface", "transport", "algorithm", "addr"),
        "related": ("cli_build_fread", ),
        "extra_preconditions": (
            "This operation is DESTRUCTIVE. The caller MUST show the built command (including the exact erase range) to the user and obtain explicit confirmation (recommended phrase: 'yes, erase') BEFORE invoking cli_execute.",
            "Sector-based flash may erase a larger block than the requested byte range; report this to the user before confirmation.",
            "Board must be connected and in serial boot mode.",
            "`target` and `algorithm` must match the processor and flash device; do not guess them.",
            "After execution, verify with cli_build_fread (expect 0xFF) over the erased range.",
        ),
    },
    "fprogram_cli": {
        "description": "Build the CLI command to erase, program, and verify flash memory.",
        "extra": ("algorithm", "addr", "size", "file", "hex_data", "partition", "noverify"),
        "required": ("target", "interface", "transport", "algorithm", "addr"),
        "one_of": (("file",), ("hex_data",)),
        "related": ("cli_build_fverify", "cli_build_fcrc", "cli_build_fread", "cli_build_ferase"),
        "extra_preconditions": (
            "This operation is DESTRUCTIVE. The caller MUST show the built command to the user and obtain explicit confirmation (recommended phrase: 'yes, program') BEFORE invoking cli_execute.",
            "Sector-based flash may erase/program a larger block than the requested byte range; state this to the user before confirmation.",
            "Board must be connected and in serial boot mode. If a previous session used a different target/algorithm, the board must be reset back into serial boot before retrying.",
            "`target` must match the processor family; if uncertain, run cli_build_mcuid + cli_execute first. Do not guess.",
            "`algorithm` must match the flash device on the board; pick from list_platform_files (bin_type='flash') and confirm against list_platform_files (bin_type='supported'). Do not guess.",
            "`file` (when used) must be an absolute path to an existing binary that matches the target family.",
            "Do NOT claim 'verified' unless verify was actually enabled (i.e. `noverify` is not set) and the tool reported success. If `noverify` is set, follow up with cli_build_fverify or cli_build_fcrc.",
            "Recommended validation after execution: cli_build_fverify (byte-by-byte), or cli_build_fcrc (CRC32 of range vs. source file), or cli_build_fread (external inspection of the programmed range).",
        ),
    },
    "fverify_cli": {
        "description": "Build the CLI command to verify flash contents against a file or hex string.",
        "extra": ("algorithm", "addr", "size", "file", "hex_data", "partition"),
        "required": ("target", "interface", "transport", "algorithm", "addr"),
        "one_of": (("file",), ("hex_data",)),
        "related": ("cli_build_fprogram", "cli_build_fcrc", "cli_build_fread"),
        "extra_preconditions": (
            "Board must be connected and in serial boot mode.",
            "`target` and `algorithm` must match the processor and flash device; do not guess them.",
            "The `file` or `hex_data` provided must correspond to what was (or should have been) programmed at `addr`; a mismatch here is a verification failure, not a tool error.",
            "On a verify failure, do NOT auto-retry programming; inspect the mismatched range with cli_build_fread first.",
        ),
    },
    "boot_cli": {
        "description": "Build the CLI command to load an image using the BootROM protocol.",
        "extra": ("file", "addr", "entrypoint", "frb"),
        "required": ("target", "interface", "transport", "file", "addr"),
        "extra_preconditions": (
            "Loads an image into SRAM via BootROM; no persistent flash write, but the image will execute on the target immediately after transfer.",
            "Board must be connected and in serial boot mode.",
            "`target` must match the processor family and `file` must be a matching absolute-path binary; do not guess.",
            "`entrypoint` (when set) must be a valid address within the loaded image's mapped region; a bad entrypoint hangs the CPU.",
        ),
    },
    "dcd_cli": {
        "description": "Build the CLI command to load and execute a DCD image.",
        "extra": ("file",),
        "required": ("target", "interface", "transport", "file"),
        "extra_preconditions": (
            "Board must be connected and in serial boot mode.",
            "`target` must match the processor family and `file` must be a matching absolute-path DCD binary; do not guess.",
            "A DCD image runs device configuration commands on the target; a wrong DCD can leave the device in an unusable configuration until power-cycle.",
        ),
    },
    "fcrc_cli": {
        "description": "Build the CLI command to calculate a CRC32 checksum for a flash memory region.",
        "extra": ("algorithm", "addr", "size", "file"),
        "required": ("target", "interface", "transport", "algorithm", "addr", "size"),
        "related": ("cli_build_fprogram", "cli_build_fverify", "cli_build_fread"),
        "extra_preconditions": (
            "Read-only. Safe to run without confirmation.",
            "Board must be connected and in serial boot mode.",
            "`target` and `algorithm` must match the processor and flash device; do not guess them.",
            "When `file` is provided, the tool computes the CRC over the same range in the file and compares; treat a mismatch as a verification failure rather than a tool error.",
        ),
    },
    "list_interfaces_cli": {
        "description": "List available ports for the selected interface.",
        "extra": (),
        "required": ("interface",),
        "extra_preconditions": (
            "Read-only discovery. Safe to run without confirmation.",
            "Run this before any operation that requires a transport endpoint (COM port, CAN adapter, Ethernet adapter) when the endpoint is not already known.",
        ),
    },

}


def make_cli_build_action(operation: str) -> ActionExecutable:
    """Build a cli_build_<operation> ActionExecutable with its specific input schema.

    operation is the pinned S32FlashTool CLI operation, e.g. ``fprogram_cli``.
    """

    spec = _OPERATIONS[operation]
    properties = _BASE_PROPS + tuple(spec["extra"])
    input_schema = _input_schema(
        properties=properties,
        required=tuple(spec["required"]),
        one_of=tuple(spec.get("one_of", ())),
    )

    # Every cli_build action is followed by cli_execute. Individual operations
    # may declare extra related actions via the optional "related" spec key.
    related_actions = ("cli_execute",) + tuple(spec.get("related", ()))

    # Base preconditions apply to every cli_build_* action. Operations may
    # append per-operation safety / discovery / validation-followup context
    # via the optional "extra_preconditions" spec key. Kept as plain strings
    # so `search_actions` surfaces them via the existing ActionContract
    # serializer without any change to mcp_shared.
    preconditions = (
        "An effective installation path must be configured (params.sft_folder or the server runtime context).",
        f"cli_request.operation must be '{operation}' and cli_request.input must match its CLI input schema.",
    ) + tuple(spec.get("extra_preconditions", ()))


    return ActionExecutable(
        contract=ActionContract(
            name=f"cli_build_{operation.removesuffix('_cli')}",
            description=(
                f"Build an S32FlashTool CLI command string for the '{operation}' "
                f"operation ({spec['description']}) from a structured cli_request."
            ),
            params=(
                ActionParameter(
                    name="sft_folder",
                    required=False,
                    schema={
                        "type": "string",
                        "description": "Absolute path to the S32FlashTool folder. Falls back to the server runtime context when omitted.",
                    },
                ),
                ActionParameter(
                    name="cli_request",
                    required=True,
                    schema={
                        "type": "object",
                        "description": f"Structured CLI request for the {operation} operation.",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "const": operation,
                                "description": "Pinned CLI operation for this action.",
                            },
                            "input": input_schema,
                        },
                        "required": ["operation", "input"],
                        "additionalProperties": False,
                    },
                ),
            ),
            preconditions=preconditions,
            related_actions=related_actions,
            category="cli_build",

        ),
        handler=cli_build_command_handler,
    )




