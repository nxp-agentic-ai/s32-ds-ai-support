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

"""Register the public S32CT MCP surface.

The server exposes the shared two-tool action surface, ``search_actions`` and
``execute_action``, described in ``docs/action_protocol_implementation_guideline.md``.

This replaced five ``action`` / ``kind`` / ``query``-routed dispatchers
(configure, inspect, validate, sanitize, env). Every mode those dispatchers
supported is now a named action in the catalog assembled by
:mod:`nxp.mcp.s32ct.actions`:

* ``configure``      -> ``s32ct.configure_cli`` plus the eight per-subsystem
  ``s32ct.configure_*`` actions and ``s32ct.generate_code``
* ``configure`` (gtm) -> ``s32ct.gtm_edit`` / ``s32ct.gtm_list_usecases`` /
  ``s32ct.gtm_create_from_usecase``
* ``inspect``        -> the seven ``s32ct.inspect_*`` actions
* ``inspect`` (lookup) -> the four ``s32ct.lookup_*`` actions
* ``validate``       -> ``s32ct.validate``
* ``sanitize``       -> ``s32ct.sanitize``
* ``env``            -> ``s32ct.env_status`` / ``env_version`` / ``env_installs``

The helper modules under ``tools/`` (launcher.py, inspect_mex.py,
resource_lookup.py, validate.py, sanitize_mex.py) remain in the tree because
the action handlers delegate to them; they no longer register MCP tools of
their own.
"""

from nxp.mcp.s32ct.resources.info import register_info_resource
from nxp.mcp.s32ct.tools.s32ct_search_tools import register_s32ct_search_tools


def register_tools(server, config) -> None:
    """Register the S32CT action surface.

    Note there is no ``StandardizingServer`` wrapper here. The shared action
    dispatcher already returns ``ActionOutcome.to_response()``, which is the
    standard ``{success, result}`` / ``{success, error}`` envelope, so wrapping
    would double-wrap the payload. The component-local payload keys documented
    in the S32CT skills (``exit_code``, ``command``, ``stdout_tail``,
    ``stderr_tail``, ``values``, ``summary``) are preserved verbatim inside
    ``result``.
    """

    register_s32ct_search_tools(server, config)


def register_resources(server, config) -> None:
    register_info_resource(server, config)


def register_prompts(server, config) -> None:
    pass
