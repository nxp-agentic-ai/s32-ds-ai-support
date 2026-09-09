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

"""``inspect`` - unified read-only query surface for S32 Configuration Tools.

Folds two previously-separate tools into one ``kind``-discriminated dispatcher:

* ``kind="instances" | "clock_points" | "clock_outputs" | "clock_settings"
  | "xrefs" | "pins" | "summary"`` -- was ``inspect_mex``: structural queries
  over a ``.mex`` project (in-process XML parsing, no ``toolsc.exe``).
* ``kind="pin_signal" | "enum_values" | "list_arrays" | "list_drivers"`` --
  was ``resource_lookup``: package-specific allowed-value queries from the
  S32CT MCU data package (XML resource tables, no ``toolsc.exe``).

Why one tool: both surfaces are **read-only**, both parse XML in-process,
both are typically called in the same phase of work (discover what's possible
/ what's there). Folding them removes a tool slot from the system prompt
without changing semantics -- each ``kind`` value maps 1:1 to a former tool
mode.
"""
import logging
from typing import Literal, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.inspect_mex import (
    _clock_outputs,
    _clock_points,
    _clock_settings,
    _clocks_block,
    _instances,
    _pins,
    _read,
    _summary,
    _xrefs,
)
from nxp.mcp.s32ct.tools.launcher import S32CTContext
from nxp.mcp.s32ct.tools.resource_lookup import (
    _enum_values,
    _list_arrays,
    _list_drivers,
    _package_dir,
    _pin_signal,
)

_logger = logging.getLogger(MCP_SERVER_NAME)


# kinds that operate on a .mex file
_MEX_KINDS: frozenset[str] = frozenset({
    "instances",
    "clock_points",
    "clock_outputs",
    "clock_settings",
    "xrefs",
    "pins",
    "summary",
})

# kinds that operate on the MCU data package
_LOOKUP_KINDS: frozenset[str] = frozenset({
    "pin_signal",
    "enum_values",
    "list_arrays",
    "list_drivers",
})


def register_inspect_tool(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    @server.tool(
        name="inspect",
        description=(
            "Unified read-only inspector for S32 Configuration Tools. Folds "
            "the former `inspect_mex` and `resource_lookup` tools into one "
            "`kind`-routed surface. Never invokes toolsc.exe -- purely parses "
            "XML in-process so it's fast and side-effect-free.\n\n"
            "Project-level queries (require `project_path`):\n"
            "  - `instances` -- every <instance> block with name/type_id/mode"
            "/size.\n"
            "  - `clock_points` -- every McuClockReferencePoint_* and which "
            "clock output it selects.\n"
            "  - `clock_outputs` -- every <clock_output> with its computed "
            "frequency (optional `name_filter`).\n"
            "  - `clock_settings` -- every <setting> inside the Clocks tool "
            "(optional `name_filter`).\n"
            "  - `xrefs` -- cross-references `value=\"/Foo/...\"` (optional "
            "`root_filter` to constrain to one driver).\n"
            "  - `pins` -- every <pin> entry in the Pins tool.\n"
            "  - `summary` -- digest combining the above counts.\n\n"
            "Package-level queries (require `mcu` + `package`):\n"
            "  - `pin_signal` -- legal pins for a peripheral/signal pair from "
            "signal_configuration.xml. Requires `peripheral` + `signal`.\n"
            "  - `enum_values` -- legal values for a driver's dotted array "
            "path from resource_tables/<Driver>.xml. Requires `driver` + "
            "`array_path`.\n"
            "  - `list_arrays` -- every dotted array path for a driver "
            "(discovery). Requires `driver`.\n"
            "  - `list_drivers` -- every driver that has a resource table on "
            "this package.\n\n"
            "Use this BEFORE editing a .mex to confirm the current state or "
            "to find legal values, and AFTER a `configure` or splice to "
            "verify the new state."
        ),
    )
    def inspect(
        kind: Literal[
            # mex-level
            "instances",
            "clock_points",
            "clock_outputs",
            "clock_settings",
            "xrefs",
            "pins",
            "summary",
            # package-level
            "pin_signal",
            "enum_values",
            "list_arrays",
            "list_drivers",
        ] = "summary",
        # -- inspect_mex inputs --
        project_path: Optional[str] = None,
        name_filter: Optional[str] = None,
        root_filter: Optional[str] = None,
        # -- resource_lookup inputs --
        mcu: Optional[str] = None,
        package: Optional[str] = None,
        peripheral: Optional[str] = None,
        signal: Optional[str] = None,
        driver: Optional[str] = None,
        array_path: Optional[str] = None,
        platform_sdk: Optional[str] = None,
        mcu_data_root: Optional[str] = None,
    ) -> dict:
        # ------------------------------------------------------------------
        # Route to inspect_mex semantics
        # ------------------------------------------------------------------
        if kind in _MEX_KINDS:
            if not project_path:
                return {
                    "kind": kind,
                    "error": (
                        f"inspect(kind='{kind}') requires `project_path`."
                    ),
                }
            try:
                p, txt = _read(project_path)
            except FileNotFoundError as e:
                return {
                    "kind": kind,
                    "project_path": project_path,
                    "error": str(e),
                }

            try:
                if kind == "instances":
                    result = _instances(txt)
                elif kind == "clock_points":
                    result = _clock_points(txt)
                elif kind == "clock_outputs":
                    clk = _clocks_block(txt)
                    result = (
                        _clock_outputs(clk, name_filter) if clk else []
                    )
                elif kind == "clock_settings":
                    clk = _clocks_block(txt)
                    result = (
                        _clock_settings(clk, name_filter) if clk else []
                    )
                elif kind == "xrefs":
                    result = _xrefs(txt, root_filter)
                elif kind == "pins":
                    result = _pins(txt)
                else:  # kind == "summary"
                    result = _summary(p, txt)
            except Exception as e:
                _logger.exception("inspect(kind=%s) failed", kind)
                return {
                    "kind": kind,
                    "project_path": str(p),
                    "error": f"{type(e).__name__}: {e}",
                }

            return {
                "kind": kind,
                "project_path": str(p),
                "result": result,
            }

        # ------------------------------------------------------------------
        # Route to resource_lookup semantics
        # ------------------------------------------------------------------
        if kind in _LOOKUP_KINDS:
            if not mcu or not package:
                return {
                    "kind": kind,
                    "error": (
                        f"inspect(kind='{kind}') requires both `mcu` and "
                        f"`package`."
                    ),
                }
            try:
                pkg_dir = _package_dir(
                    ctx, mcu, package, platform_sdk, mcu_data_root,
                )
            except Exception as e:
                return {
                    "kind": kind, "mcu": mcu, "package": package,
                    "error": f"{type(e).__name__}: {e}",
                }

            try:
                if kind == "pin_signal":
                    if not peripheral or not signal:
                        return {
                            "kind": kind, "mcu": mcu, "package": package,
                            "error": (
                                "pin_signal requires both 'peripheral' and "
                                "'signal'"
                            ),
                        }
                    payload = _pin_signal(pkg_dir, peripheral, signal)
                    source = str(pkg_dir / "signal_configuration.xml")
                elif kind == "enum_values":
                    if not driver or not array_path:
                        return {
                            "kind": kind, "mcu": mcu, "package": package,
                            "error": (
                                "enum_values requires both 'driver' and "
                                "'array_path'"
                            ),
                        }
                    payload = _enum_values(pkg_dir, driver, array_path)
                    source = "; ".join(payload["sources"])
                elif kind == "list_arrays":
                    if not driver:
                        return {
                            "kind": kind, "mcu": mcu, "package": package,
                            "error": "list_arrays requires 'driver'",
                        }
                    payload = _list_arrays(pkg_dir, driver)
                    source = "; ".join(
                        set(
                            s
                            for a in payload["detail"].values()
                            for s in a["sources"]
                        )
                    )
                else:  # kind == "list_drivers"
                    payload = _list_drivers(pkg_dir)
                    source = str(pkg_dir / "resource_tables")
            except Exception as e:
                _logger.exception("inspect(kind=%s) failed", kind)
                return {
                    "kind": kind, "mcu": mcu, "package": package,
                    "error": f"{type(e).__name__}: {e}",
                }

            return {
                "kind": kind,
                "mcu": mcu,
                "package": package,
                "result": payload,
                "source": source,
            }

        return {
            "kind": kind,
            "error": f"Unknown inspect kind: {kind!r}",
        }
