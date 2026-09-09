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

"""Component-local action handlers for the S32CT search-first surface.

Each handler corresponds to exactly one ``ActionExecutable`` declared under
``src/actions/``. Handlers are thin adapters: they unpack the validated
``params`` object and delegate to the untouched implementation helpers in
``nxp.mcp.s32ct.tools.launcher`` / ``inspect_mex`` / ``resource_lookup`` /
``validate`` / ``sanitize_mex``. No launcher plumbing lives here.

Handler signatures follow the shared dispatcher convention:

    async def handler(params: dict, session_manager: object | None = None)

The dispatcher inspects the handler arity and supplies ``session_manager``
(here an :class:`S32CTSessionManager`) when the handler accepts it. Parameter
validation against the contract-derived ``input_schema`` has already happened
by the time a handler runs, so handlers only implement the cross-field rules
that JSON Schema cannot express (for example the ``project_path`` /
``empty_config`` mutual exclusion enforced inside ``cli_impl``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from nxp.mcp.shared.action import ActionExecutionError, errors

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import (
    S32CTContext,
    _resolve_platform_sdk_dir,
    cli_impl,
    discover_installs,
    generate_code_impl,
    get_version_impl,
    gtm_create_from_usecase_impl,
)
from nxp.mcp.s32ct.tools.sanitize_mex import sanitize_mex_impl
from nxp.mcp.s32ct.tools.validate import validate_impl

logger = logging.getLogger(MCP_SERVER_NAME)

# Protocol-facing error code sourced from the shared registry so one numeric
# value keeps exactly one meaning across the whole MCP layer. Required-parameter
# violations never reach a handler - the shared dispatcher rejects them against
# the contract-derived input_schema before dispatching - so handlers only need
# the forward-error code for runtime/precondition failures.
_HANDLER_ERROR_CODE = errors.FORWARD_ERROR



@dataclass(frozen=True)
class S32CTSessionManager:
    """Runtime state shared by every S32CT action handler.

    Wraps the :class:`S32CTContext` built once at server startup, which already
    carries the selected install, launcher binary, launcher ``.ini``, MCU data
    root, distribution label and default timeout. Passing it through the shared
    dispatcher keeps handlers free of module-level globals and makes the
    resolved install trivially substitutable in tests.
    """

    ctx: S32CTContext

    @property
    def default_timeout_s(self) -> int:
        """Server-configured launcher timeout, in seconds."""

        return self.ctx.timeout_s


def _require_session(session_manager: Optional[S32CTSessionManager]) -> S32CTContext:
    """Return the active context or raise a structured precondition error."""

    if session_manager is None or session_manager.ctx is None:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={
                "message": (
                    "S32CT runtime is not initialized. The server builds it at "
                    "startup from s32ct.settings; check the YAML configuration."
                ),
            },
        )
    return session_manager.ctx


# ---------------------------------------------------------------------------

# configure family - headless CLI edits / exports
# ---------------------------------------------------------------------------
#
# Every parameter accepted by ``cli_impl`` beyond the leading ``ctx``. The
# per-subsystem configure actions expose subsets of this list, but they all
# funnel through the same call, so forwarding by name keeps the handler free of
# a 50-argument signature that would have to be updated in two places.
_CLI_PARAM_NAMES: tuple[str, ...] = (
    "project_path", "empty_config", "mcu", "sdk_version", "config_name",
    "tool_name", "enable_tool",
    "apply_use_case", "set_values", "get_values",
    "import_c", "import_project", "sdk_path",
    "overwrite_with_sdk_sources",
    "migrate_to_toolchain_version", "migrate_to_highest_version",
    "custom_copyright", "output_path_overrides",
    "import_bin", "import_blob", "import_ab", "import_ddrc",
    "auto_align", "custom_pointers_addrs",
    "start_pointer_addr", "entry_pointer_addr",
    "raw_binary", "clock_config_data", "mini_paco_structure",
    "pre_defined_data", "boot_device_id", "ivt_start_addr",
    "update_filepaths", "ivt_filter", "include_marker",
    "include_serial_boot_header",
    "import_arxml", "import_json", "file_type", "default_containers",
    "validate",
    "export_kind", "output_dir",
    "data_dir", "extra_args",
    "s32ct_launcher", "launcher_ini", "timeout_s",
)


def _cli_kwargs(params: dict[str, Any]) -> dict[str, Any]:
    """Project ``params`` onto the keyword arguments ``cli_impl`` understands.

    Only keys the caller actually supplied are forwarded so ``cli_impl`` keeps
    applying its own defaults for everything else.
    """

    return {name: params[name] for name in _CLI_PARAM_NAMES if name in params}


async def configure_cli(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Run the generic headless CLI across any of the 9 S32CT tools."""

    ctx = _require_session(session_manager)
    return cli_impl(ctx, **_cli_kwargs(params))


def _make_tool_scoped_cli_handler(tool_name: str):
    """Build a handler that pre-fills ``tool_name`` for one S32CT subsystem.

    The per-subsystem configure actions (pins, clocks, peripherals, dcd, ivt,
    efuse, quadspi, ffc) are identical to the generic cli action except that
    the tool is implied by the action name. An explicit ``tool_name`` in params
    still wins so an agent can deliberately cross-target if it needs to.
    """

    async def handler(
        params: dict[str, Any],
        session_manager: Optional[S32CTSessionManager] = None,
    ) -> Any:
        ctx = _require_session(session_manager)
        kwargs = _cli_kwargs(params)
        kwargs.setdefault("tool_name", tool_name)
        return cli_impl(ctx, **kwargs)

    handler.__name__ = f"configure_{tool_name.lower()}"
    handler.__doc__ = (
        f"Run the headless CLI scoped to the S32CT {tool_name} tool."
    )
    return handler


configure_pins = _make_tool_scoped_cli_handler("Pins")
configure_clocks = _make_tool_scoped_cli_handler("Clocks")
configure_peripherals = _make_tool_scoped_cli_handler("Peripherals")
configure_dcd = _make_tool_scoped_cli_handler("DCD")
configure_ivt = _make_tool_scoped_cli_handler("IVT")
configure_efuse = _make_tool_scoped_cli_handler("eFUSE")
configure_quadspi = _make_tool_scoped_cli_handler("QuadSPI")
configure_ffc = _make_tool_scoped_cli_handler("FFC")


async def generate_code(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Generate driver sources for one tool from an existing ``.mex``."""

    ctx = _require_session(session_manager)
    return generate_code_impl(
        ctx,
        project_path=params["project_path"],
        tool_name=params["tool_name"],
        output_dir=params["output_dir"],
        export_kind=params.get("export_kind", "ExportAll"),
        enable_if_disabled=params.get("enable_if_disabled", True),
        sdk_version=params.get("sdk_version"),
        s32ct_launcher=params.get("s32ct_launcher"),
        launcher_ini=params.get("launcher_ini"),
        timeout_s=params.get("timeout_s"),
    )


# ---------------------------------------------------------------------------
# GTM family
# ---------------------------------------------------------------------------


async def gtm_edit(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Edit an existing GTM configuration through the headless CLI."""

    ctx = _require_session(session_manager)
    kwargs = _cli_kwargs(params)
    kwargs["tool_name"] = "GTM"
    return cli_impl(ctx, **kwargs)


async def gtm_list_usecases(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """List the predefined GTM use-case templates available for an MCU.

    Read-only: resolves the MCU data package on disk and returns the bare
    use-case stems, matching the pre-action behavior. An MCU that has no
    use-case folder yields an empty list rather than an error, because "this
    MCU ships no GTM templates" is a valid answer.
    """

    ctx = _require_session(session_manager)
    mcu = params["mcu"]

    root = (
        Path(params["mcu_data_root"])
        if params.get("mcu_data_root")
        else ctx.mcu_data_root
    )
    mcu_dir = root / "processors" / mcu
    if not mcu_dir.exists():
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "NOT_FOUND",
            error_details={
                "message": f"MCU '{mcu}' not found under {root / 'processors'}.",
                "mcu": mcu,
                "searched": str(root / "processors"),
            },
        )

    sdk_dir = _resolve_platform_sdk_dir(mcu_dir, params.get("platform_sdk_dir"))
    usecase_dir = sdk_dir / "gtm" / "use_cases" / "use_cases_mexes"
    if not usecase_dir.exists():
        return []
    return sorted(p.stem for p in usecase_dir.glob("*.mex"))


async def gtm_create_from_usecase(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Bootstrap a new GTM configuration from a predefined use-case template."""

    ctx = _require_session(session_manager)
    return gtm_create_from_usecase_impl(
        ctx,
        mcu=params["mcu"],
        sdk_version=params["sdk_version"],
        usecase=params["usecase"],
        output_dir=params["output_dir"],
        mcu_data_root=params.get("mcu_data_root"),
        platform_sdk_dir=params.get("platform_sdk_dir"),
        usecase_mex_path=params.get("usecase_mex_path"),
        export_kind=params.get("export_kind", "ExportAll"),
        gtm_codegen=params.get("gtm_codegen", True),
        config_name=params.get("config_name"),
        s32ct_launcher=params.get("s32ct_launcher"),
        launcher_ini=params.get("launcher_ini"),
        timeout_s=params.get("timeout_s"),
    )


# ---------------------------------------------------------------------------
# inspect family - read-only .mex structural queries
# ---------------------------------------------------------------------------
#
# These never invoke the launcher; they parse the .mex in-process. Imported
# lazily inside the handlers so a syntax problem in the parsing helpers cannot
# prevent the action catalog from being built at import time.


def _read_project(project_path: str):
    """Load a ``.mex`` and surface a missing/incorrect path as NOT_FOUND."""

    from nxp.mcp.s32ct.tools.inspect_mex import _read

    try:
        return _read(project_path)
    except FileNotFoundError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "NOT_FOUND",
            error_details={
                "message": str(exc),
                "project_path": project_path,
            },
        ) from exc


def _inspect_envelope(kind: str, project_path: Path, result: Any) -> dict:
    """Wrap one inspect result in the historical response shape."""

    return {
        "kind": kind,
        "project_path": str(project_path),
        "result": result,
    }


async def inspect_summary(params: dict[str, Any]) -> Any:
    """Digest of instance / pin / clock counts for a ``.mex``."""

    from nxp.mcp.s32ct.tools.inspect_mex import _summary

    path, text = _read_project(params["project_path"])
    return _inspect_envelope("summary", path, _summary(path, text))


async def inspect_instances(params: dict[str, Any]) -> Any:
    """Every ``<instance>`` block with its name / type_id / mode / size."""

    from nxp.mcp.s32ct.tools.inspect_mex import _instances

    path, text = _read_project(params["project_path"])
    return _inspect_envelope("instances", path, _instances(text))


async def inspect_pins(params: dict[str, Any]) -> Any:
    """Every ``<pin>`` entry configured in the Pins tool."""

    from nxp.mcp.s32ct.tools.inspect_mex import _pins

    path, text = _read_project(params["project_path"])
    return _inspect_envelope("pins", path, _pins(text))


async def inspect_clock_points(params: dict[str, Any]) -> Any:
    """Every ``McuClockReferencePoint_*`` and the clock output it selects."""

    from nxp.mcp.s32ct.tools.inspect_mex import _clock_points

    path, text = _read_project(params["project_path"])
    return _inspect_envelope("clock_points", path, _clock_points(text))


async def inspect_clock_outputs(params: dict[str, Any]) -> Any:
    """Every ``<clock_output>`` with its computed frequency."""

    from nxp.mcp.s32ct.tools.inspect_mex import _clock_outputs, _clocks_block

    path, text = _read_project(params["project_path"])
    clocks = _clocks_block(text)
    result = _clock_outputs(clocks, params.get("name_filter")) if clocks else []
    return _inspect_envelope("clock_outputs", path, result)


async def inspect_clock_settings(params: dict[str, Any]) -> Any:
    """Every ``<setting>`` inside the Clocks tool block."""

    from nxp.mcp.s32ct.tools.inspect_mex import _clock_settings, _clocks_block

    path, text = _read_project(params["project_path"])
    clocks = _clocks_block(text)
    result = _clock_settings(clocks, params.get("name_filter")) if clocks else []
    return _inspect_envelope("clock_settings", path, result)


async def inspect_xrefs(params: dict[str, Any]) -> Any:
    """Cross-references of the form ``value="/Driver/..."`` in a ``.mex``."""

    from nxp.mcp.s32ct.tools.inspect_mex import _xrefs

    path, text = _read_project(params["project_path"])
    result = _xrefs(text, params.get("root_filter"))
    return _inspect_envelope("xrefs", path, result)


# ---------------------------------------------------------------------------
# lookup family - MCU-data-package allowed-value queries
# ---------------------------------------------------------------------------


def _resolve_mcu_data_root(
    ctx: S32CTContext, params: dict[str, Any]
) -> Path:
    """Return the caller-overridden or install-selected MCU data root.

    The two enumeration actions (lookup_mcus / lookup_sdks) work one level
    above a package, so they resolve the root directly instead of going
    through ``_resolve_package_dir`` (which also needs a ``package``).
    """

    override = params.get("mcu_data_root")
    return Path(override) if override else ctx.mcu_data_root


def _resolve_package_dir(
    ctx: S32CTContext, params: dict[str, Any]
) -> Path:
    """Resolve the per-package MCU data directory for a lookup action."""


    from nxp.mcp.s32ct.tools.resource_lookup import _package_dir

    try:
        return _package_dir(
            ctx,
            params["mcu"],
            params["package"],
            params.get("platform_sdk"),
            params.get("mcu_data_root"),
        )
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "NOT_FOUND",
            error_details={
                "message": f"{type(exc).__name__}: {exc}",
                "mcu": params.get("mcu"),
                "package": params.get("package"),
            },
        ) from exc


def _lookup_envelope(kind: str, params: dict[str, Any], payload: Any, source: str) -> dict:
    """Wrap one lookup result in the historical response shape."""

    return {
        "kind": kind,
        "mcu": params.get("mcu"),
        "package": params.get("package"),
        "result": payload,
        "source": source,
    }


async def lookup_pin_signal(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Legal pins for one peripheral / signal pair on a given package."""

    from nxp.mcp.s32ct.tools.resource_lookup import _pin_signal

    ctx = _require_session(session_manager)
    pkg_dir = _resolve_package_dir(ctx, params)
    payload = _pin_signal(pkg_dir, params["peripheral"], params["signal"])
    return _lookup_envelope(
        "pin_signal", params, payload,
        str(pkg_dir / "signal_configuration.xml"),
    )


async def lookup_enum_values(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Legal values for a driver's dotted array path."""

    from nxp.mcp.s32ct.tools.resource_lookup import _enum_values

    ctx = _require_session(session_manager)
    pkg_dir = _resolve_package_dir(ctx, params)
    payload = _enum_values(pkg_dir, params["driver"], params["array_path"])
    return _lookup_envelope(
        "enum_values", params, payload, "; ".join(payload["sources"]),
    )


async def lookup_arrays(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Every dotted array path a driver exposes (discovery)."""

    from nxp.mcp.s32ct.tools.resource_lookup import _list_arrays

    ctx = _require_session(session_manager)
    pkg_dir = _resolve_package_dir(ctx, params)
    payload = _list_arrays(pkg_dir, params["driver"])
    source = "; ".join(
        {s for a in payload["detail"].values() for s in a["sources"]}
    )
    return _lookup_envelope("list_arrays", params, payload, source)


async def lookup_drivers(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Every driver that has a resource table on this package."""

    from nxp.mcp.s32ct.tools.resource_lookup import _list_drivers

    ctx = _require_session(session_manager)
    pkg_dir = _resolve_package_dir(ctx, params)
    payload = _list_drivers(pkg_dir)
    return _lookup_envelope(
        "list_drivers", params, payload, str(pkg_dir / "resource_tables"),
    )


async def lookup_mcus(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Every MCU that has a folder in the installed MCU data package.

    Discovery entry point above lookup_sdks / lookup_drivers: answers "which
    mcu values does this install support?" so the mcu argument required by the
    configure / gtm / lookup actions is discoverable rather than guessed.
    """

    from nxp.mcp.s32ct.tools.resource_lookup import _list_mcus

    ctx = _require_session(session_manager)
    root = _resolve_mcu_data_root(ctx, params)
    try:
        payload = _list_mcus(root)
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "NOT_FOUND",
            error_details={
                "message": f"{type(exc).__name__}: {exc}",
                "mcu_data_root": str(root),
            },
        ) from exc
    return {
        "kind": "list_mcus",
        "result": payload,
        "source": str(root / "processors"),
    }


async def lookup_sdks(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Every ``PlatformSDK_*`` folder installed for one MCU.

    Follows lookup_mcus in the discovery chain: given an mcu, lists the
    platform SDK folders present so a caller can pick the platform_sdk /
    sdk_version to bind a new configuration to.
    """

    from nxp.mcp.s32ct.tools.resource_lookup import _list_sdks

    ctx = _require_session(session_manager)
    root = _resolve_mcu_data_root(ctx, params)
    mcu = params["mcu"]
    try:
        payload = _list_sdks(root, mcu)
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "NOT_FOUND",
            error_details={
                "message": f"{type(exc).__name__}: {exc}",
                "mcu": mcu,
                "mcu_data_root": str(root),
            },
        ) from exc
    return {
        "kind": "list_sdks",
        "mcu": mcu,
        "result": payload,
        "source": str(root / "processors" / mcu),
    }


# ---------------------------------------------------------------------------
# validate / sanitize
# ---------------------------------------------------------------------------



async def validate(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Validate a ``.mex`` against the S32CT Problems View."""

    ctx = _require_session(session_manager)
    return validate_impl(
        ctx,
        project_path=params["project_path"],
        tool_name=params.get("tool_name"),
        sdk_version=params.get("sdk_version"),
        s32ct_launcher=params.get("s32ct_launcher"),
        launcher_ini=params.get("launcher_ini"),
        timeout_s=params.get("timeout_s"),
        stop_on_first_failure=params.get("stop_on_first_failure", False),
        explain=params.get("explain", False),
        diff_against=params.get("diff_against"),
        chain=params.get("chain", True),
        include_unsupported_tool_problems=params.get(
            "include_unsupported_tool_problems", False
        ),
    )


async def sanitize(params: dict[str, Any]) -> Any:
    """Sanitize dangling cross-references in a freshly-spliced ``.mex``."""

    return sanitize_mex_impl(
        project_path=params["project_path"],
        output_path=params.get("output_path"),
        canonical_clockref=params.get("canonical_clockref"),
        overwrite=params.get("overwrite", False),
    )


# ---------------------------------------------------------------------------
# env family - read-only environment / installation probes
# ---------------------------------------------------------------------------


async def env_status(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Snapshot of the active S32CT configuration, with existence flags."""

    ctx = _require_session(session_manager)
    return {
        "mcp_server": "s32ct",
        "distribution": ctx.distribution,
        "version": ctx.version_label,
        "selection_reason": ctx.selection_reason,
        "discovered_install_count": len(ctx.discovered_installs),
        "installation_path": str(ctx.install) if ctx.is_selected else "",
        "installation_path_exists": ctx.is_selected and ctx.install.exists(),
        "launcher": str(ctx.launcher) if ctx.is_selected else "",
        "launcher_exists": ctx.is_selected and ctx.launcher.exists(),
        "tools_ini": str(ctx.tools_ini) if ctx.is_selected else "",
        "tools_ini_exists": ctx.is_selected and ctx.tools_ini.exists(),
        "mcu_data_root": (
            str(ctx.mcu_data_root) if ctx.mcu_data_root.parts else ""
        ),
        "mcu_data_root_exists": (
            bool(ctx.mcu_data_root.parts) and ctx.mcu_data_root.exists()
        ),
        "documentation_path": (
            str(ctx.documentation_path) if str(ctx.documentation_path) else ""
        ),
        "documentation_path_exists": (
            ctx.documentation_path.exists()
            if str(ctx.documentation_path)
            else False
        ),
        "timeout_s": ctx.timeout_s,
    }


async def env_version(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Installed S32CT product name and version string."""

    ctx = _require_session(session_manager)
    return get_version_impl(
        ctx,
        params.get("installation_path"),
        params.get("s32ct_launcher"),
    )


async def env_installs(
    params: dict[str, Any],
    session_manager: Optional[S32CTSessionManager] = None,
) -> Any:
    """Every S32CT install discovered on this host, plus the selected one.

    Rescans the filesystem on every call so the answer reflects what is
    installed *now*. The selected install still comes from startup state -
    changing it requires a server restart.
    """

    ctx = _require_session(session_manager)
    discovered = discover_installs()
    return {
        "selected": {
            "distribution": ctx.distribution,
            "version": ctx.version_label,
            "path": str(ctx.install),
            "launcher": str(ctx.launcher),
            "reason": ctx.selection_reason,
        },
        "discovered": [
            {
                "distribution": i.distribution,
                "version": i.version_label,
                "path": str(i.path),
                "launcher": str(i.launcher),
                "launcher_ini": str(i.launcher_ini),
                "mcu_data_root": str(i.mcu_data_root),
                "mcu_data_root_exists": i.mcu_data_root.exists(),
            }
            for i in discovered
        ],
    }



