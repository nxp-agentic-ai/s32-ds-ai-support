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

from nxp.mcp.gateway.config.resolver import is_mcp_server_disabled, resolve_mcp_server_config
from nxp.mcp.gateway.mounting.loader import load_mcp_server_module
from nxp.mcp.gateway.registry.servers import MCP_SERVER_REGISTRY


def mount_mcp_servers(gateway_server, gateway_config, registry=None) -> list[str]:
    """Mount all non-disabled MCP servers onto *gateway_server*.

    Args:
        gateway_server: The root :class:`~fastmcp.FastMCP` gateway instance.
        gateway_config: Fully-resolved :class:`~nxp.mcp.gateway.config.models.GatewayConfig`.
        registry:       Optional mapping of ``{server_name: McpServerRegistryEntry}``.
                        Defaults to the global :data:`MCP_SERVER_REGISTRY`.
                        Pass a custom registry in tests to avoid mutating global state.

    Each server's relative path fields are resolved against
    ``gateway_config.base_dir`` (the directory of the gateway config file), so
    servers behave the same whether launched standalone or via the gateway.
    """
    if registry is None:
        registry = MCP_SERVER_REGISTRY
    mounted = []
    for server_name, entry in registry.items():
        if is_mcp_server_disabled(gateway_config, server_name):
            continue

        raw_config = resolve_mcp_server_config(gateway_config, server_name)
        try:
            module = load_mcp_server_module(entry.module_path)
            typed_config = module.build_mcp_server_config(
                raw_config, base_dir=gateway_config.base_dir
            )
            mcp_server = module.create_mcp_server(typed_config)
            gateway_server.mount(mcp_server)
            mounted.append(server_name)
        except Exception:
            if gateway_config.gateway.strict_startup:
                raise
    return mounted
