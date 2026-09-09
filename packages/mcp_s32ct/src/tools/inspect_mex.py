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

"""``inspect_mex`` - read-only structural query on a ``.mex`` project.

Every ad-hoc inspection script we keep writing (``inventory.py``,
``find_peripherals.py``, ``xrefs.py``, ``compare_clocks.py``, ...) does the
same five jobs. This tool exposes them as one MCP entrypoint so callers
don't have to re-derive the regexes / XPath each time.

The tool is fully read-only and never invokes ``toolsc.exe`` - it parses the
``.mex`` directly with stdlib ``xml.etree`` plus a small set of regex
fallbacks (because S32CT's namespaced XML mixes well-formed XML with
order-sensitive string slots that ElementTree drops on re-serialisation,
and we want the byte-accurate view of the original file).

Returned shape (see ``query`` parameter for the per-mode contents)::

    {
      "query": "instances" | "clock_points" | ... | "summary",
      "project_path": "...",
      "result": <mode-specific payload>
    }

Or, on error::

    {"query": ..., "project_path": ..., "error": "..."}
"""
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Literal, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


# ---------------------------------------------------------------------------
# Small parsing helpers - every query mode shares these.
# ---------------------------------------------------------------------------


def _read(project_path: str) -> tuple[Path, str]:
    p = Path(project_path)
    if not p.exists() or p.suffix.lower() != ".mex":
        raise FileNotFoundError(
            f"project_path must be an existing .mex file. Got: {p}"
        )
    return p, p.read_text(encoding="utf-8")


def _instances(txt: str) -> list[dict]:
    """Enumerate every ``<instance ...>...</instance>`` block."""
    out: list[dict] = []
    # We match attrs by name so attribute order in source doesn't matter.
    for m in re.finditer(r'<instance\b([^>]*)>', txt):
        attrs = m.group(1)

        def attr(name: str) -> Optional[str]:
            am = re.search(rf'\b{name}="([^"]*)"', attrs)
            return am.group(1) if am else None

        name = attr("name") or ""
        ty = attr("type") or ""
        type_id = attr("type_id") or ""
        mode = attr("mode") or ""
        uuid = attr("uuid") or ""

        # Find matching </instance>
        end = txt.find("</instance>", m.end())
        if end < 0:
            continue
        body_size = end - m.start()
        out.append(
            {
                "name": name,
                "type": ty,
                "type_id": type_id,
                "mode": mode,
                "uuid": uuid,
                "body_size_bytes": body_size,
                "start_offset": m.start(),
            }
        )
    return out


def _clock_points(txt: str) -> list[dict]:
    """List every ``McuClockReferencePoint_*`` and what frequency it selects.

    Each point is a ``<struct name="0|1|...">`` whose first setting is
    ``<setting name="Name" value="McuClockReferencePoint_N"/>``. The
    interesting siblings are ``McuClockReferencePointFrequency`` (optional;
    some MCU schemas don't carry it) and ``McuClockFrequencySelect`` (the
    Clock-tool output id the point binds to).
    """
    points: list[dict] = []
    # Find each Name setting, then look ahead a small window for the two
    # optional siblings. We bound the window so a missing sibling doesn't
    # cause us to swallow a different struct's data.
    for m in re.finditer(
        r'<setting name="Name" value="(McuClockReferencePoint_\d+)"/>',
        txt,
    ):
        name = m.group(1)
        window = txt[m.end() : m.end() + 1200]
        # Stop the window at the next </struct> so we never read past the
        # current point's container.
        cut = window.find("</struct>")
        if cut >= 0:
            window = window[:cut]
        freq_m = re.search(
            r'<setting name="McuClockReferencePointFrequency" value="([^"]*)"/>',
            window,
        )
        sel_m = re.search(
            r'<setting name="McuClockFrequencySelect" value="([^"]*)"/>',
            window,
        )
        points.append(
            {
                "name": name,
                "frequency_value": freq_m.group(1) if freq_m else "",
                "selects": sel_m.group(1) if sel_m else "",
            }
        )
    return points


def _clocks_block(txt: str) -> Optional[str]:
    """Return the substring containing the entire ``<clocks ...>...</clocks>``
    element of the Clocks tool, or None if absent."""
    m = re.search(r'<clocks\b[^>]*>', txt)
    if not m:
        return None
    end = txt.find("</clocks>", m.end())
    if end < 0:
        return None
    return txt[m.start():end + len("</clocks>")]


def _clock_outputs(clk_block: str, name_filter: Optional[str] = None) -> list[dict]:
    """List every ``<clock_output id="..." value="...">`` entry."""
    out = []
    for m in re.finditer(r'<clock_output id="([^"]+)" value="([^"]+)"', clk_block):
        if name_filter and name_filter not in m.group(1):
            continue
        out.append({"id": m.group(1), "value": m.group(2)})
    return out


def _clock_settings(clk_block: str, name_filter: Optional[str] = None) -> list[dict]:
    """List every ``<setting id="..." value="...">`` entry inside the Clocks tool."""
    out = []
    for m in re.finditer(r'<setting id="([^"]+)" value="([^"]+)"', clk_block):
        if name_filter and name_filter not in m.group(1):
            continue
        out.append({"id": m.group(1), "value": m.group(2)})
    return out


def _xrefs(txt: str, root_filter: Optional[str] = None) -> dict:
    """Collect every cross-reference ``value="/Foo/..."``.

    Returns ``{ "by_root": Counter(/Foo/: N), "samples": list[str] }``.
    """
    paths = re.findall(r'value="(/[A-Za-z0-9_]+/[^"]+)"', txt)
    if root_filter:
        prefix = "/" + root_filter.strip("/") + "/"
        paths = [p for p in paths if p.startswith(prefix)]
    by_root = Counter(p.split("/", 2)[1] for p in paths if "/" in p[1:])
    return {
        "by_root_count": dict(by_root),
        "total": len(paths),
        "samples": sorted(set(paths))[:50],
    }


def _pins(txt: str) -> list[dict]:
    """List every ``<pin>`` entry from the Pins tool (in source order)."""
    out = []
    # Each pin: peripheral_signal_id, peripheral, signal, pin_num,
    #   pin_signal (pad name), and an optional <route><.../></route> body.
    for m in re.finditer(
        r'<pin\s+([^>]*?)/?>',
        txt,
    ):
        attrs = m.group(1)
        def a(name: str) -> Optional[str]:
            am = re.search(rf'\b{name}="([^"]*)"', attrs)
            return am.group(1) if am else None

        if not a("peripheral") and not a("pin_signal"):
            # Not a Pins-tool pin element (could be a nested helper)
            continue
        out.append(
            {
                "peripheral": a("peripheral"),
                "signal": a("signal"),
                "pin_num": a("pin_num"),
                "pin_signal": a("pin_signal"),
                "label": a("label") or "",
                "direction": a("direction") or "",
            }
        )
    return out


def _summary(p: Path, txt: str) -> dict:
    insts = _instances(txt)
    points = _clock_points(txt)
    clk = _clocks_block(txt)
    outs = _clock_outputs(clk) if clk else []
    xr = _xrefs(txt)
    pins = _pins(txt)
    return {
        "file": str(p),
        "size_bytes": len(txt),
        "instance_count": len(insts),
        "instance_type_ids": [i["type_id"] for i in insts],
        "clock_point_count": len(points),
        "clock_points": [pt["name"] for pt in points],
        "clock_output_count": len(outs),
        "pin_count": len(pins),
        "xref_total": xr["total"],
        "xref_roots": xr["by_root_count"],
    }


# ---------------------------------------------------------------------------
# Public tool registration
# ---------------------------------------------------------------------------


def register_inspect_mex_tool(server, config) -> None:
    @server.tool(
        name="inspect_mex",
        description=(
            "Read-only structural query on an S32 Configuration Tools `.mex` "
            "project. Supports six query modes via the `query` parameter: "
            "`instances` (lists every <instance> block with name/type_id/mode/"
            "size), `clock_points` (every McuClockReferencePoint_* and which "
            "clock output it selects), `clock_outputs` (every <clock_output> "
            "with its computed frequency), `clock_settings` (every <setting> "
            "inside the Clocks tool, optional `name_filter` substring), "
            "`xrefs` (cross-references `value=\"/Foo/...\"`, optional "
            "`root_filter` to constrain to one driver), `pins` (every <pin> "
            "entry in the Pins tool), and `summary` (digest combining the "
            "above counts). Use this before authoring any change to confirm "
            "the current state, after a splice to verify the new instances "
            "are visible, or to diff two .mex files by calling once per "
            "file. Does not invoke toolsc.exe - purely parses the XML "
            "in-process so it's fast and side-effect-free."
        ),
    )
    def inspect_mex(
        project_path: str,
        query: Literal[
            "instances",
            "clock_points",
            "clock_outputs",
            "clock_settings",
            "xrefs",
            "pins",
            "summary",
        ] = "summary",
        name_filter: Optional[str] = None,
        root_filter: Optional[str] = None,
    ) -> dict:
        try:
            p, txt = _read(project_path)
        except FileNotFoundError as e:
            return {
                "query": query,
                "project_path": project_path,
                "error": str(e),
            }

        try:
            if query == "instances":
                result = _instances(txt)
            elif query == "clock_points":
                result = _clock_points(txt)
            elif query == "clock_outputs":
                clk = _clocks_block(txt)
                result = _clock_outputs(clk, name_filter) if clk else []
            elif query == "clock_settings":
                clk = _clocks_block(txt)
                result = _clock_settings(clk, name_filter) if clk else []
            elif query == "xrefs":
                result = _xrefs(txt, root_filter)
            elif query == "pins":
                result = _pins(txt)
            elif query == "summary":
                result = _summary(p, txt)
            else:
                return {
                    "query": query,
                    "project_path": str(p),
                    "error": f"Unknown query mode: {query}",
                }
        except Exception as e:
            _logger.exception("inspect_mex %s failed", query)
            return {
                "query": query,
                "project_path": str(p),
                "error": f"{type(e).__name__}: {e}",
            }

        return {
            "query": query,
            "project_path": str(p),
            "result": result,
        }
