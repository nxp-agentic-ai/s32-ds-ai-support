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

from nxp.mcp.shared.config.merge import merge_dicts


def resolve_mcp_server_config(gateway_config, server_name: str) -> dict:
    """Build the raw config dict passed to a server's ``build_mcp_server_config``.

    The ``disabled`` flag lives exclusively at the gateway level and is NOT
    forwarded to the server — servers have no concept of enable/disable.
    The caller (composer) is responsible for checking ``disabled`` before
    invoking this function.
    """
    server_override = gateway_config.servers.get(server_name, {})

    base = {
        "logging": {
            "level": gateway_config.logging.level,
            "timestamp_format": gateway_config.logging.timestamp_format,
            "format": gateway_config.logging.format,
            "file": gateway_config.logging.file
        },
        "settings": {},
    }
    # Strip gateway-only keys before forwarding to server
    server_data = {
        k: v for k, v in server_override.items() if k != "disabled"
    }
    resolved = merge_dicts(base, server_data)
    resolved.setdefault("settings", {})
    return resolved


def is_mcp_server_disabled(gateway_config, server_name: str) -> bool:
    """Return True if the server should be skipped (opt-out semantics).

    Servers are enabled by default; set ``disabled: true`` in the per-server
    block to exclude a server from mounting.
    """
    server_override = gateway_config.servers.get(server_name, {})
    return server_override.get("disabled", False)
