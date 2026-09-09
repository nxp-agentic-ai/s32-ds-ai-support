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

"""``resource_lookup`` - query the on-disk S32CT data model for legal values.

S32 Configuration Tools encodes its "what value is allowed where" knowledge in
two XML stores installed alongside the launcher:

  ``signal_configuration.xml``
      Pins-tool data model. For every (peripheral, signal) pair, lists the
      package pins that can carry it, with their physical pin number
      (``coords``) and direction. Lives at::

          <MCU_DATA_ROOT>/processors/<MCU>/<PlatformSDK_*>/<PACKAGE>/signal_configuration.xml

  ``resource_tables/*.xml``
      Peripherals-tool dynamic-enum store. One file per driver
      (``Spi.xml``, ``Can.xml``, ``RTD/Adc.xml``, ...). Each file holds one or
      more ``<array name="DOTTED.PATH">`` elements whose ``<setting>``
      children enumerate the legal values for that field on this MCU /
      package. Lives at::

          <MCU_DATA_ROOT>/processors/<MCU>/<PlatformSDK_*>/<PACKAGE>/resource_tables/[RTD/]<Driver>.xml

Both stores are read-only NXP data. This tool exposes a focused query
interface so callers don't have to redo the path resolution + XML walk every
time.

Returned shape (per `kind`)::

    {
      "kind": "pin_signal" | "enum_values" | "list_arrays" | "list_drivers",
      "mcu": "S32K312", "package": "S32K312_172HDQFP",
      "result": <kind-specific payload>,
      "source": "<absolute path of the XML actually consulted>"
    }
"""
import logging
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import S32CTContext

_logger = logging.getLogger(MCP_SERVER_NAME)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _package_dir(ctx: S32CTContext, mcu: str, package: str,
                 platform_sdk: Optional[str] = None,
                 mcu_data_root: Optional[str] = None) -> Path:
    """Resolve ``<MCU_DATA_ROOT>/processors/<MCU>/<PLATFORM_SDK>/<PACKAGE>/``.

    Mirrors ``_resolve_platform_sdk_dir`` from launcher.py: if
    ``platform_sdk`` isn't given and exactly one ``PlatformSDK_*`` exists
    under the MCU folder, use it.
    """
    root = Path(mcu_data_root) if mcu_data_root else ctx.mcu_data_root
    mcu_dir = root / "processors" / mcu
    if not mcu_dir.is_dir():
        available = sorted(p.name for p in (root / "processors").glob("*") if p.is_dir())
        raise FileNotFoundError(
            f"MCU folder not found: {mcu_dir}. "
            f"Available under processors/: {available[:25]}"
            f"{'...' if len(available) > 25 else ''}"
        )

    if platform_sdk:
        sdk_dir = mcu_dir / platform_sdk
    else:
        platform = sorted(p for p in mcu_dir.glob("PlatformSDK_*") if p.is_dir())
        if len(platform) == 1:
            sdk_dir = platform[0]
        elif not platform:
            raise FileNotFoundError(
                f"No PlatformSDK_* under {mcu_dir}. "
                "Pass platform_sdk explicitly."
            )
        else:
            names = ", ".join(p.name for p in platform)
            raise RuntimeError(
                f"Multiple PlatformSDK_* dirs under {mcu_dir}: {names}. "
                "Pass platform_sdk explicitly."
            )

    pkg_dir = sdk_dir / package
    if not pkg_dir.is_dir():
        available = sorted(p.name for p in sdk_dir.glob("*") if p.is_dir())
        raise FileNotFoundError(
            f"Package folder not found: {pkg_dir}. "
            f"Available under {sdk_dir.name}: {available[:25]}"
            f"{'...' if len(available) > 25 else ''}"
        )
    return pkg_dir


# ---------------------------------------------------------------------------
# MCU / SDK enumeration - the discovery layer above driver/array/enum lookups
# ---------------------------------------------------------------------------


def _processors_dir(root: Path) -> Path:
    """Resolve ``<MCU_DATA_ROOT>/processors`` or raise ``FileNotFoundError``.

    Every installed MCU lives as a direct subfolder of ``processors/``. When
    the folder is missing the install either has no MCU data package or the
    resolved ``mcu_data_root`` is wrong; both are surfaced as a not-found
    error carrying the path that was probed.
    """
    processors = root / "processors"
    if not processors.is_dir():
        raise FileNotFoundError(
            f"processors folder not found under mcu_data_root: {processors}. "
            f"Check that an MCU data package is installed and that "
            f"mcu_data_root points at the mcu_data folder."
        )
    return processors


def _list_mcus(root: Path) -> dict:
    """List every MCU that has a folder under ``<root>/processors/``.

    Read-only. This is the discovery step above ``list_drivers`` /
    ``list_arrays`` / ``enum_values``: it tells a caller which ``mcu`` names
    the installed data package actually supports before any of the
    package-scoped lookups are attempted.
    """
    processors = _processors_dir(root)
    mcus = sorted(p.name for p in processors.iterdir() if p.is_dir())
    return {
        "mcu_count": len(mcus),
        "mcus": mcus,
    }


def _list_sdks(root: Path, mcu: str) -> dict:
    """List the ``PlatformSDK_*`` folders installed for one *mcu*.

    Mirrors the ``PlatformSDK_*`` auto-detection used by ``_package_dir`` and
    the launcher, but instead of requiring exactly one it returns them all so
    a caller can pick the platform_sdk / sdk_version to bind a configuration
    to. Read-only.
    """
    processors = _processors_dir(root)
    mcu_dir = processors / mcu
    if not mcu_dir.is_dir():
        available = sorted(p.name for p in processors.iterdir() if p.is_dir())
        raise FileNotFoundError(
            f"MCU folder not found: {mcu_dir}. "
            f"Available under processors/: {available[:25]}"
            f"{'...' if len(available) > 25 else ''}"
        )
    sdks = sorted(
        p.name for p in mcu_dir.glob("PlatformSDK_*") if p.is_dir()
    )
    return {
        "mcu": mcu,
        "sdk_count": len(sdks),
        "sdks": sdks,
    }


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------



def _strip_ns(root: ET.Element) -> ET.Element:
    """Strip XML namespaces from every tag so we can use plain XPath."""
    for e in root.iter():
        if "}" in e.tag:
            e.tag = e.tag.split("}", 1)[1]
        # Also strip attribute namespaces
        for k in list(e.attrib):
            if "}" in k:
                v = e.attrib.pop(k)
                e.attrib[k.split("}", 1)[1]] = v
    return root


def _parse(xml_path: Path) -> ET.Element:
    tree = ET.parse(xml_path)
    return _strip_ns(tree.getroot())


# ---------------------------------------------------------------------------
# pin_signal - query Pins-tool data model
# ---------------------------------------------------------------------------


def _pin_signal(pkg_dir: Path, peripheral: str, signal: str) -> dict:
    """Return the legal pins for one (peripheral, signal) pair.

    The S32CT Pins data model encodes pin->signal allowability as
    ``<pin name="PTxN" coords="N">/<connections package_function="altK">/
    <connection><peripheral_signal_ref peripheral="X" signal="y"/></connection>``.

    We walk every pin's connections and collect those whose
    ``peripheral_signal_ref`` matches both the requested peripheral name and
    signal name (case-sensitive, since the data model itself is consistent).
    """
    xml = pkg_dir / "signal_configuration.xml"
    if not xml.exists():
        raise FileNotFoundError(f"signal_configuration.xml not found at {xml}")

    root = _parse(xml)
    pins_el = root.find("pins")
    if pins_el is None:
        return {"peripheral": peripheral, "signal": signal, "matches": [], "count": 0}

    matches: list[dict] = []
    for pin in pins_el.findall("pin"):
        pin_name = pin.get("name", "")
        coords = pin.get("coords", "")
        for conns in pin.findall("connections"):
            pkg_func = conns.get("package_function", "")
            for conn in conns.findall("connection"):
                for ref in conn.findall("peripheral_signal_ref"):
                    if ref.get("peripheral") == peripheral and ref.get("signal") == signal:
                        m = {
                            "pin": pin_name,
                            "pin_num": coords,
                            "package_function": pkg_func,
                        }
                        ch = ref.get("channel")
                        if ch is not None:
                            m["channel"] = ch
                        # direction hint: 'dependent_on_direction' attribute on conn
                        if conn.get("dependent_on_direction"):
                            m["dependent_on_direction"] = conn.get("dependent_on_direction")
                        matches.append(m)

    return {
        "peripheral": peripheral,
        "signal": signal,
        "matches": matches,
        "count": len(matches),
    }


# ---------------------------------------------------------------------------
# enum_values / list_arrays / list_drivers - query Peripherals-tool data model
# ---------------------------------------------------------------------------


def _driver_xml_candidates(pkg_dir: Path, driver: str) -> list[Path]:
    """A driver's resource table may live at either
    ``resource_tables/<Driver>.xml`` or ``resource_tables/RTD/<Driver>.xml``.
    """
    base = pkg_dir / "resource_tables"
    if not base.is_dir():
        return []
    cands: list[Path] = []
    for sub in ("", "RTD"):
        p = (base if not sub else base / sub) / f"{driver}.xml"
        if p.exists():
            cands.append(p)
    return cands


def _arrays_of(xml_path: Path) -> dict[str, list[str]]:
    """Return every ``<array name="X">`` and its enumerated values."""
    root = _parse(xml_path)
    out: dict[str, list[str]] = {}
    for a in root.iter("array"):
        n = a.get("name")
        if not n:
            continue
        vals = [s.get("value") for s in a.findall("setting") if s.get("value") is not None]
        out[n] = vals
    return out


def _enum_values(
    pkg_dir: Path, driver: str, array_path: str
) -> dict:
    cands = _driver_xml_candidates(pkg_dir, driver)
    if not cands:
        raise FileNotFoundError(
            f"No resource table for driver '{driver}' under "
            f"{pkg_dir / 'resource_tables'} (looked for {driver}.xml and RTD/{driver}.xml)"
        )

    # Merge values from all candidates so the caller gets a complete picture
    # if the driver shows up in both locations (rare, but harmless).
    merged: list[str] = []
    sources: list[str] = []
    seen_path: list[str] = []
    for xml in cands:
        arrs = _arrays_of(xml)
        if array_path in arrs:
            merged.extend(arrs[array_path])
            sources.append(str(xml))
        seen_path.append(str(xml))

    if not sources:
        # Provide useful diagnostics: what arrays do exist?
        all_arrays: set[str] = set()
        for xml in cands:
            all_arrays.update(_arrays_of(xml).keys())
        suggestions = sorted(
            a for a in all_arrays
            if array_path.split(".")[-1].lower() in a.lower()
        )[:10]
        raise KeyError(
            f"array '{array_path}' not found in {seen_path}. "
            f"Try `kind=list_arrays` for the full list. "
            f"Suggestions matching the leaf name: {suggestions}"
        )

    # De-dup while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for v in merged:
        if v not in seen:
            seen.add(v)
            uniq.append(v)

    return {
        "driver": driver,
        "array_path": array_path,
        "values": uniq,
        "count": len(uniq),
        "sources": sources,
    }


def _list_arrays(pkg_dir: Path, driver: str) -> dict:
    cands = _driver_xml_candidates(pkg_dir, driver)
    if not cands:
        raise FileNotFoundError(
            f"No resource table for driver '{driver}' under "
            f"{pkg_dir / 'resource_tables'}."
        )
    arrays: dict[str, dict] = {}
    for xml in cands:
        for n, vals in _arrays_of(xml).items():
            arrays.setdefault(
                n, {"value_count": len(vals), "sources": []}
            )["sources"].append(str(xml))
    return {
        "driver": driver,
        "array_count": len(arrays),
        "arrays": sorted(arrays.keys()),
        "detail": arrays,
    }


def _list_drivers(pkg_dir: Path) -> dict:
    base = pkg_dir / "resource_tables"
    if not base.is_dir():
        raise FileNotFoundError(f"resource_tables not found under {pkg_dir}")
    drivers: dict[str, list[str]] = {}
    for root, _dirs, files in os.walk(base):
        for f in files:
            if not f.endswith(".xml"):
                continue
            name = f[:-4]
            drivers.setdefault(name, []).append(str(Path(root) / f))
    return {
        "driver_count": len(drivers),
        "drivers": sorted(drivers.keys()),
        "detail": drivers,
    }


# ---------------------------------------------------------------------------
# Public tool registration
# ---------------------------------------------------------------------------


def register_resource_lookup_tool(server, config) -> None:
    ctx = S32CTContext.from_settings(config.settings)

    @server.tool(
        name="resource_lookup",
        description=(
            "Look up package-specific allowed values from the S32 "
            "Configuration Tools data model. Four query kinds: "
            "`pin_signal` (given peripheral+signal, returns the legal pins "
            "from signal_configuration.xml - e.g. `peripheral=CAN0, "
            "signal=can0_tx` -> `[{pin: PTA7, pin_num: 100, direction: OUTPUT}, "
            "...]`); `enum_values` (given a driver + dotted array path, "
            "returns the legal values from resource_tables/<Driver>.xml - "
            "e.g. `driver=Spi, array_path=SpiGeneral.SpiPhyUnit."
            "SpiPhyUnitMapping` -> `[LPSPI_0, LPSPI_1, ...]`); `list_arrays` "
            "(list every dotted array path for a driver, for discovery); "
            "`list_drivers` (list every driver that has a resource table on "
            "this package). Use this BEFORE editing a .mex setting to confirm "
            "the value you're about to write is legal on this MCU/package, "
            "and AFTER a validation 'value not available' error to find what "
            "would be legal instead. Read-only - never invokes toolsc.exe."
        ),
    )
    def resource_lookup(
        kind: Literal["pin_signal", "enum_values", "list_arrays", "list_drivers"],
        mcu: str,
        package: str,
        # pin_signal
        peripheral: Optional[str] = None,
        signal: Optional[str] = None,
        # enum_values / list_arrays
        driver: Optional[str] = None,
        array_path: Optional[str] = None,
        # path overrides
        platform_sdk: Optional[str] = None,
        mcu_data_root: Optional[str] = None,
    ) -> dict:
        try:
            pkg_dir = _package_dir(ctx, mcu, package, platform_sdk, mcu_data_root)
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
                        "error": "pin_signal requires both 'peripheral' and 'signal'",
                    }
                payload = _pin_signal(pkg_dir, peripheral, signal)
                source = str(pkg_dir / "signal_configuration.xml")
            elif kind == "enum_values":
                if not driver or not array_path:
                    return {
                        "kind": kind, "mcu": mcu, "package": package,
                        "error": "enum_values requires both 'driver' and 'array_path'",
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
                source = "; ".join(set(s for a in payload["detail"].values() for s in a["sources"]))
            elif kind == "list_drivers":
                payload = _list_drivers(pkg_dir)
                source = str(pkg_dir / "resource_tables")
            else:
                return {
                    "kind": kind, "mcu": mcu, "package": package,
                    "error": f"Unknown kind: {kind}",
                }
        except Exception as e:
            _logger.exception("resource_lookup %s failed", kind)
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
