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

from dataclasses import dataclass, field

from nxp.mcp.shared.config.models import BaseMcpServerConfig


@dataclass(slots=True)
class S32CTSettings:
    """Settings consumed by the S32 Configuration Tools MCP server.

    Field conventions match the sibling servers ``mcp_s32debugger`` and
    ``mcp_s32ds`` (single flat ``installation_path``, no nested groups).

    Notes:
        - ``installation_path`` should point at the root of an installed
          S32 Configuration Tools instance,
          e.g. ``C:\\NXP\\S32ConfigTools.2026.R1.9``.

          The launcher (``toolsc.exe``) and ``tools.ini`` are derived from
          this path at call time. Use the per-call ``s32ct_launcher`` /
          ``launcher_ini`` tool arguments for one-off overrides.

        - ``mcu_data_root`` is the per-machine MCU data package, e.g.
          ``C:\\ProgramData\\NXP\\mcu_data_25.12``. Used to resolve the GTM
          use-case catalogue under
          ``<mcu_data_root>/processors/<MCU>/<PlatformSDK_*>/gtm/use_cases/use_cases_mexes/``.

        - ``documentation_path`` is the path to the S32 CT HTML help tree
          (typically ``<installation_path>/configuration/org.eclipse.osgi/<bundle_id>/0/.cp/resources/support/help/en``).
          This server does **not** itself ingest documentation. The path is
          surfaced through the ``status`` tool and the ``s32ct://info``
          resource so an integrator can wire the same value into
          one of ``mcp_knowledge``'s ``corpora[].dirs`` lists - see
          ``configs/knowledge.standalone.yaml``.

        - ``timeout_s`` is the default subprocess timeout in seconds applied
          when a per-call ``timeout_s`` argument is not provided.
    """

    installation_path: str = ""
    mcu_data_root: str = ""
    documentation_path: str = ""
    timeout_s: int = 600


@dataclass(slots=True)
class S32CTMcpServerConfig(BaseMcpServerConfig):
    """Full configuration for the S32 Configuration Tools MCP server."""

    settings: S32CTSettings = field(default_factory=S32CTSettings)
