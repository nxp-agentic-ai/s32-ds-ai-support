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

"""
S32Trace configurator XML utilities.

Template XML schema (simplified):

    <SAELS>
      <Configuration>
        <Name>CC Platform Config</Name>
        <ConfigBlock>
          <Name>Data Streams</Name>
          <EnumAttribute><Name>TraceLocation</Name>...</EnumAttribute>
          <BoolAttribute><Name>Continuous Collection</Name>...</BoolAttribute>
          <ConfigBlock><Name>ETF 2</Name>...</ConfigBlock>
          <ConfigBlock><Name>DDR</Name>...</ConfigBlock>
        </ConfigBlock>
        <ConfigBlock>
          <Name>Timestamp Generator</Name>...
        </ConfigBlock>
        <ConfigBlock>
          <Name>Results</Name>
          <StringAttribute><Name>Output Folder</Name>...</StringAttribute>
        </ConfigBlock>
        <ConfigBlock>
          <Name>SoC Modules</Name>
          <ConfigBlock><Name>ARM Funnel 2</Name>...</ConfigBlock>
          ...
        </ConfigBlock>
        <ConfigBlock>
          <Name>Target Access</Name>...
        </ConfigBlock>
        <ConfigBlock>
          <Name>Trace Generators</Name>
          <ConfigBlock>
            <Name>CORE</Name>
            <ConfigBlock>
              <Name>Core 0</Name>
              <StringAttribute><Name>UI Name</Name><DefaultValue>M7_0</DefaultValue></StringAttribute>
              <BoolAttribute><Name>Enable Trace</Name>...</BoolAttribute>
              <StringAttribute><Name>Dependency</Name>...</StringAttribute>
              ...
            </ConfigBlock>
          </ConfigBlock>
        </ConfigBlock>
      </Configuration>
    </SAELS>

All attribute element types: BoolAttribute, StringAttribute, EnumAttribute,
Addr32Attribute, Addr64Attribute, UInt32Attribute, FileAttribute.
Each carries <Name> and <DefaultValue> children.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import xml.etree.ElementTree as ET

# Attribute tag names that carry <Name>/<DefaultValue>.
_ATTR_TAGS = {
    "BoolAttribute",
    "StringAttribute",
    "EnumAttribute",
    "Addr32Attribute",
    "Addr64Attribute",
    "UInt32Attribute",
    "FileAttribute",
}

_PLUGIN_GLOB = "com.nxp.s32ds.sa.data.common_*"
_TEMPLATE_SUBDIR = "target/data/fsl.configs.sa.ls.configurators"
_TEMPLATE_PREFIX = "TEMPLATEConfigFile"

# Pattern that recognises S32DS workspace runtime folders.
# Handles all observed naming styles:
#   runtime-New_configuration-ds3.6.9         (-ds<X>.<Y>.<Z>)
#   runtime-New_configuration-ds-3.6.5        (-ds-<X>.<Y>.<Z>)
#   runtime-New_configuration3.6.9            (no -ds prefix)
#   runtime-new-config-ds3.6                  (no patch component)
_WORKSPACE_PAT = re.compile(
    r"runtime-.+?[-_]?(?:ds-?)?(\d+)\.(\d+)(?:\.(\d+))?$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def find_configurator_dir(installation_path: str) -> Path:
    """Locate the configurators directory inside an S32DS installation root."""
    root = Path(installation_path)
    plugins_dir = root / "eclipse" / "plugins"
    if not plugins_dir.exists():
        raise FileNotFoundError(f"Eclipse plugins directory not found: {plugins_dir}")
    matches = sorted(plugins_dir.glob(_PLUGIN_GLOB))
    if not matches:
        raise FileNotFoundError(
            f"No plugin matching '{_PLUGIN_GLOB}' found under {plugins_dir}"
        )
    configurator_dir = matches[-1] / _TEMPLATE_SUBDIR
    if not configurator_dir.exists():
        raise FileNotFoundError(f"Configurator directory not found: {configurator_dir}")
    return configurator_dir


def list_templates(installation_path: str) -> list[dict]:
    """Return all TEMPLATE*.xml files with board name, path, description, and core names."""
    cfg_dir = find_configurator_dir(installation_path)
    results = []
    for xml_file in sorted(cfg_dir.glob(f"{_TEMPLATE_PREFIX}*.xml")):
        board = xml_file.stem.replace(_TEMPLATE_PREFIX, "")
        description = ""
        cores: list[str] = []
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            cfg = root.find("Configuration")
            if cfg is not None:
                comments_el = cfg.find("Comments")
                if comments_el is not None and comments_el.text:
                    description = comments_el.text.strip()
                for cb in _iter_config_blocks(cfg, ["Trace Generators", "CORE"]):
                    name_el = cb.find("Name")
                    if name_el is not None and name_el.text:
                        ui_attr = _find_attribute(cb, "UI Name")
                        core_label = (
                            (ui_attr.findtext("DefaultValue") or name_el.text.strip())
                            if ui_attr is not None
                            else name_el.text.strip()
                        )
                        cores.append(core_label)
        except ET.ParseError:
            pass
        results.append({
            "board": board,
            "file": str(xml_file),
            "description": description,
            "cores": cores,
        })
    return results


def default_output_dir(user_home: str | None = None) -> Path:
    """Return the platformConfig directory from the newest S32DS workspace.

    Scans ``<user_home>/runtime-*-ds<X>.<Y>.<Z>`` directories, sorts by the
    version tuple (newest first), and returns the ``platformConfig`` path
    inside that workspace's ``.metadata/.plugins/com.freescale.sa`` folder.
    Creates the path if it does not yet exist.

    Raises FileNotFoundError when no matching workspace is found.
    """
    home = Path(user_home) if user_home else Path.home()
    candidates: list[tuple[tuple[int, ...], Path]] = []
    for entry in home.iterdir():
        m = _WORKSPACE_PAT.match(entry.name)
        if m and entry.is_dir():
            patch = int(m.group(3)) if m.group(3) is not None else 0
            version = (int(m.group(1)), int(m.group(2)), patch)
            candidates.append((version, entry))

    if not candidates:
        raise FileNotFoundError(
            f"No S32DS workspace runtime folder found under {home}. "
            "Provide output_path explicitly."
        )

    candidates.sort(key=lambda x: x[0], reverse=True)
    workspace = candidates[0][1]
    platform_dir = workspace / ".metadata" / ".plugins" / "com.freescale.sa" / "platformConfig"
    platform_dir.mkdir(parents=True, exist_ok=True)
    return platform_dir


# ---------------------------------------------------------------------------
# Schema introspection
# ---------------------------------------------------------------------------

def inspect_template(template_path: str) -> dict:
    """Return a structured summary of all configurable attributes in a template."""
    tree = ET.parse(template_path)
    root = tree.getroot()
    cfg = root.find("Configuration")
    if cfg is None:
        raise ValueError(f"No <Configuration> element found in {template_path}")
    return _describe_element(cfg)


def _describe_element(el: ET.Element) -> dict:
    """Recursively build a description dict for an element."""
    attrs: dict[str, Any] = {}
    for child in el:
        if child.tag in _ATTR_TAGS:
            attr_name_el = child.find("Name")
            attr_name = (
                attr_name_el.text.strip()
                if (attr_name_el is not None and attr_name_el.text)
                else child.tag
            )
            default_el = child.find("DefaultValue")
            default = default_el.text if default_el is not None else ""
            entry: dict[str, Any] = {"type": child.tag, "default": default}
            enum_el = child.find("EnumValues")
            if enum_el is not None and enum_el.text:
                entry["allowed"] = [v.strip() for v in enum_el.text.split(",")]
            allow_multi = child.find("AllowMultiple")
            if allow_multi is not None and allow_multi.text:
                entry["allow_multiple"] = allow_multi.text.strip().lower() == "true"
            attrs[attr_name] = entry
        elif child.tag == "ConfigBlock":
            sub = _describe_element(child)
            sub_name_el = child.find("Name")
            sub_name = (
                sub_name_el.text.strip()
                if (sub_name_el is not None and sub_name_el.text)
                else "ConfigBlock"
            )
            attrs[sub_name] = sub
    return {"_attributes": attrs}


# ---------------------------------------------------------------------------
# Trace flow description
# ---------------------------------------------------------------------------

def describe_trace_flow(config_path: str) -> dict:
    """Parse a config (template or saved) XML and return the full trace pipeline.

    Returns a dict with:
        - ``cores``: list of cores, each with its pipeline path and sink name.
        - ``sinks``: list of data-sink (ETF/DDR) blocks with their key settings.
        - ``data_streams``: TraceLocation selection and continuous_collection flag.
        - ``timestamp_generator``: enabled flag and module base address.
        - ``soc_modules``: list of funnel/replicator modules with base address.
    """
    tree = ET.parse(config_path)
    root = tree.getroot()
    cfg = root.find("Configuration")
    if cfg is None:
        raise ValueError(f"No <Configuration> element in {config_path}")

    # ---- collect all named blocks into a flat lookup -----
    all_blocks: dict[str, ET.Element] = {}

    def _collect(el: ET.Element) -> None:
        for cb in el.findall("ConfigBlock"):
            name_el = cb.find("Name")
            if name_el is not None and name_el.text:
                all_blocks[name_el.text.strip()] = cb
            _collect(cb)

    _collect(cfg)

    # ---- cores ----
    cores_out: list[dict] = []
    tg = _find_config_block(cfg, "Trace Generators")
    if tg is not None:
        core_parent = _find_config_block(tg, "CORE")
        if core_parent is not None:
            for cb in core_parent.findall("ConfigBlock"):
                name_el = cb.find("Name")
                if name_el is None or not name_el.text:
                    continue
                ui_attr = _find_attribute(cb, "UI Name")
                ui_name = (
                    (ui_attr.findtext("DefaultValue") or name_el.text.strip())
                    if ui_attr is not None
                    else name_el.text.strip()
                )
                enabled_attr = _find_attribute(cb, "Enable Trace")
                enabled = (
                    (enabled_attr.findtext("DefaultValue") or "false").lower() == "true"
                    if enabled_attr is not None
                    else False
                )
                dep_attr = _find_attribute(cb, "Dependency")
                dep = dep_attr.findtext("DefaultValue") if dep_attr is not None else None

                # Walk the dependency chain to find the sink.
                flow = [ui_name]
                visited: set[str] = {ui_name}
                current = dep
                while current and current not in visited:
                    flow.append(current)
                    visited.add(current)
                    next_block = all_blocks.get(current)
                    if next_block is None:
                        break
                    next_dep_attr = _find_attribute(next_block, "Dependency")
                    current = (
                        next_dep_attr.findtext("DefaultValue")
                        if next_dep_attr is not None
                        else None
                    )

                sink = flow[-1] if len(flow) > 1 else None
                base_attr = _find_attribute(cb, "Module Base Address")
                mem_attr = _find_attribute(cb, "MemSpace")
                cores_out.append({
                    "name": ui_name,
                    "enabled": enabled,
                    "flow": flow,
                    "sink": sink,
                    "module_base_address": base_attr.findtext("DefaultValue") if base_attr else None,
                    "mem_space": mem_attr.findtext("DefaultValue") if mem_attr else None,
                })

    # ---- data streams / sinks ----
    ds_block = _find_config_block(cfg, "Data Streams")
    trace_location: list[str] = []
    continuous = False
    sinks_out: list[dict] = []
    if ds_block is not None:
        tl_attr = _find_attribute(ds_block, "TraceLocation")
        if tl_attr is not None:
            raw = tl_attr.findtext("DefaultValue") or ""
            trace_location = [v.strip() for v in raw.split(",") if v.strip()]
        cc_attr = _find_attribute(ds_block, "Continuous Collection")
        if cc_attr is not None:
            continuous = (cc_attr.findtext("DefaultValue") or "false").lower() == "true"

        for sink_cb in ds_block.findall("ConfigBlock"):
            sname_el = sink_cb.find("Name")
            if sname_el is None or not sname_el.text:
                continue
            sname = sname_el.text.strip()
            s: dict[str, Any] = {"name": sname}
            s["enabled_in_data_streams"] = sname in trace_location
            for aname, key in [
                ("Enable Buffer", "enable_buffer"),
                ("BufferMode", "buffer_mode"),
                ("Module Base Address", "module_base_address"),
                ("MemSpace", "mem_space"),
                ("Trace Buffer Size", "trace_buffer_size"),
                ("Trace Buffer Base Address", "trace_buffer_base_address"),
                ("TraceCollectionMode", "trace_collection_mode"),
                ("Upload Manually", "upload_manually"),
                ("Scatter-Gather", "scatter_gather"),
            ]:
                a = _find_attribute(sink_cb, aname)
                if a is not None:
                    s[key] = a.findtext("DefaultValue")
            sinks_out.append(s)

    # ---- timestamp generator ----
    ts_block = _find_config_block(cfg, "Timestamp Generator")
    ts_out: dict[str, Any] = {}
    if ts_block is not None:
        en_attr = _find_attribute(ts_block, "Enable Timestamp Generator")
        ts_out["enabled"] = (
            (en_attr.findtext("DefaultValue") or "false").lower() == "true"
            if en_attr is not None
            else False
        )
        base_attr = _find_attribute(ts_block, "Module Base Address")
        ts_out["module_base_address"] = base_attr.findtext("DefaultValue") if base_attr else None
        freq_attr = _find_attribute(ts_block, "Counter Base Frequency")
        ts_out["counter_base_frequency"] = freq_attr.findtext("DefaultValue") if freq_attr else None

    # ---- SoC modules ----
    soc_mods_out: list[dict] = []
    soc_block = _find_config_block(cfg, "SoC Modules")
    if soc_block is not None:
        for mod_cb in soc_block.findall("ConfigBlock"):
            mname_el = mod_cb.find("Name")
            if mname_el is None or not mname_el.text:
                continue
            m: dict[str, Any] = {"name": mname_el.text.strip()}
            for aname, key in [
                ("Enable Trace", "enabled"),
                ("Enable Port", "enabled"),
                ("Module Base Address", "module_base_address"),
                ("MemSpace", "mem_space"),
                ("Port Priority", "port_priority"),
                ("Dependency", "dependency"),
            ]:
                a = _find_attribute(mod_cb, aname)
                if a is not None:
                    val = a.findtext("DefaultValue")
                    if key == "enabled":
                        val = val.lower() == "true" if val else False
                    m[key] = val
            soc_mods_out.append(m)

    return {
        "cores": cores_out,
        "sinks": sinks_out,
        "data_streams": {
            "trace_location": trace_location,
            "continuous_collection": continuous,
        },
        "timestamp_generator": ts_out,
        "soc_modules": soc_mods_out,
    }


def _load_config(config_path: str) -> tuple["ET.ElementTree", "ET.Element"]:
    """Parse config_path and return (tree, <Configuration> element)."""
    tree = ET.parse(config_path)
    root = tree.getroot()
    cfg = root.find("Configuration")
    if cfg is None:
        raise ValueError(f"No <Configuration> element in {config_path}")
    return tree, cfg


def _save_config(tree: "ET.ElementTree", config_path: str) -> None:
    ET.indent(tree, space="\t")
    tree.write(config_path, encoding="utf-8", xml_declaration=True)


def create_from_template(
    template_path: str,
    output_path: str | None = None,
) -> dict:
    """Clone a template to a new config file without applying any edits.

    Returns ``{output_path, board, used_default_output_dir}``.
    """
    src = Path(template_path)
    if not src.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    board = src.stem.replace(_TEMPLATE_PREFIX, "")
    used_default = False
    if output_path is None:
        dest = default_output_dir() / f"{board}_config.xml"
        used_default = True
    else:
        dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {
        "output_path": str(dest),
        "board": board,
        "used_default_output_dir": used_default,
    }


def set_output_folder(config_path: str, output_folder: str) -> dict:
    """Set Results > Output Folder in an existing config file."""
    tree, cfg = _load_config(config_path)
    applied: list[str] = []
    _set_attr_in_path(cfg, ["Results"], "Output Folder", str(output_folder))
    applied.append("output_folder")
    _save_config(tree, config_path)
    return {"config_path": config_path, "applied": applied}


def set_target_access(config_path: str, settings: dict) -> dict:
    """Configure the Target Access block in an existing config file."""
    tree, cfg = _load_config(config_path)
    applied: list[str] = []
    _apply_target_access(cfg, settings, applied)
    _save_config(tree, config_path)
    return {"config_path": config_path, "applied": applied}


def set_timestamp_generator(
    config_path: str,
    enabled: bool,
    module_base_address: str | None = None,
    counter_base_frequency: str | None = None,
    halt_on_debug: bool | None = None,
    mem_space: str | None = None,
) -> dict:
    """Enable/disable and optionally tune the global timestamp counter."""
    tree, cfg = _load_config(config_path)
    applied: list[str] = []
    patch: dict[str, Any] = {"enabled": enabled}
    if module_base_address is not None:
        patch["module_base_address"] = module_base_address
    if counter_base_frequency is not None:
        patch["counter_base_frequency"] = counter_base_frequency
    if halt_on_debug is not None:
        patch["halt_on_debug"] = halt_on_debug
    if mem_space is not None:
        patch["mem_space"] = mem_space
    _apply_timestamp_generator(cfg, patch, applied)
    _save_config(tree, config_path)
    return {"config_path": config_path, "applied": applied}


def configure_data_streams(
    config_path: str,
    trace_location: list[str],
    continuous_collection: bool | None = None,
) -> dict:
    """Set the active trace sinks and optionally toggle continuous collection."""
    tree, cfg = _load_config(config_path)
    applied: list[str] = []
    patch: dict[str, Any] = {"trace_location": trace_location}
    if continuous_collection is not None:
        patch["continuous_collection"] = continuous_collection
    _apply_data_streams(cfg, patch, applied)
    _save_config(tree, config_path)
    return {"config_path": config_path, "applied": applied}


def configure_sink(config_path: str, sink_name: str, settings: dict) -> dict:
    """Apply overrides to one ETF or DDR sink block."""
    tree, cfg = _load_config(config_path)
    applied: list[str] = []
    _apply_sink_patches(cfg, {sink_name: settings}, applied)
    _save_config(tree, config_path)
    return {"config_path": config_path, "applied": applied}


def configure_core(config_path: str, core_name: str, settings: dict) -> dict:
    """Apply overrides to one trace generator (e.g. M7_0)."""
    tree, cfg = _load_config(config_path)
    applied: list[str] = []
    _apply_core_patches(cfg, {core_name: settings}, applied)
    _save_config(tree, config_path)
    return {"config_path": config_path, "applied": applied}


def configure_soc_module(config_path: str, module_name: str, settings: dict) -> dict:
    """Apply overrides to one SoC module (funnel, replicator, etc.)."""
    tree, cfg = _load_config(config_path)
    applied: list[str] = []
    _apply_soc_module_patches(cfg, {module_name: settings}, applied)
    _save_config(tree, config_path)
    return {"config_path": config_path, "applied": applied}


# ---------------------------------------------------------------------------
# Configuration creation
# ---------------------------------------------------------------------------

def create_configuration(
    template_path: str,
    output_path: str | None,
    patches: dict | None = None,
) -> dict:
    """Clone a template and apply the requested patches.

    Args:
        template_path:  Absolute path to a TEMPLATE*.xml file.
        output_path:    Destination file path.  When ``None`` the file is
                        written to the default S32DS workspace platformConfig
                        directory (newest ``runtime-*-ds<X>.<Y>.<Z>``
                        workspace under the user home).
        patches:        Optional dict of changes.  All keys are optional.

    PATCH KEYS
    ----------
    Top-level:

        ``output_folder`` (str)
            Results > Output Folder.

        ``timestamp_generator`` (bool | dict)
            ``True``/``False`` toggles ``Enable Timestamp Generator``.
            As a dict: ``{enabled, module_base_address, counter_base_frequency,
            halt_on_debug, mem_space}``.

        ``continuous_collection`` (bool)
            Data Streams > Continuous Collection.

        ``target_access`` (dict)
            Keys: ``server_address``, ``server_port``, ``launch_name``,
            ``target_access_method``, ``reset_before_config``,
            ``sync_server_port``, ``enable_user_code``, ``endianness``.

    ``cores`` (dict[str, dict])
        Per-core overrides keyed by UI name (e.g. ``"M7_0"``).
        Supported inner keys:
            ``enabled``, ``timestamp``, ``start_on_launch``,
            ``cycle_counting``, ``trace_scenario``, ``elf_images``,
            ``module_base_address``, ``mem_space``.

    ``sinks`` (dict[str, dict])
        Per-sink overrides keyed by sink name (``"ETF 2"``, ``"DDR"``).
        Supported inner keys:
            ``enable_buffer``, ``buffer_mode``, ``module_base_address``,
            ``mem_space``, ``trace_buffer_size``, ``trace_buffer_base_address``,
            ``trace_collection_mode``, ``scatter_gather``, ``upload_manually``,
            ``raw_trace_path``.

    ``data_streams`` (dict)
        ``trace_location`` (list[str] | str): overrides the TraceLocation enum.
        ``continuous_collection`` (bool): same as top-level key.

    ``soc_modules`` (dict[str, dict])
        Per-module overrides keyed by block name (``"ARM Funnel 2"``).
        Supported inner keys:
            ``enabled``, ``module_base_address``, ``mem_space``.

    ``raw`` (list[dict])
        Escape hatch.  Each entry: ``{path: [block_names], attribute: str,
        value: str}``.

    Returns
    -------
    Dict with ``output_path``, ``board``, ``applied_patches``, and
    ``used_default_output_dir`` (bool).
    """
    patches = patches or {}
    applied: list[str] = []
    used_default = False

    src = Path(template_path)
    if not src.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    board = src.stem.replace(_TEMPLATE_PREFIX, "")

    if output_path is None:
        dest = default_output_dir() / f"{board}_config.xml"
        used_default = True
    else:
        dest = Path(output_path)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    tree = ET.parse(dest)
    root = tree.getroot()
    cfg = root.find("Configuration")
    if cfg is None:
        raise ValueError(f"No <Configuration> element in template: {template_path}")

    # -- output_folder -------------------------------------------------------
    if "output_folder" in patches:
        _set_attr_in_path(cfg, ["Results"], "Output Folder", str(patches["output_folder"]))
        applied.append("output_folder")

    # -- continuous_collection (top-level shorthand) -------------------------
    if "continuous_collection" in patches:
        val = "true" if patches["continuous_collection"] else "false"
        _set_attr_in_path(cfg, ["Data Streams"], "Continuous Collection", val)
        applied.append("continuous_collection")

    # -- timestamp_generator -------------------------------------------------
    _apply_timestamp_generator(cfg, patches.get("timestamp_generator"), applied)

    # -- target_access -------------------------------------------------------
    if "target_access" in patches:
        _apply_target_access(cfg, patches["target_access"], applied)

    # -- data_streams (structured) -------------------------------------------
    if "data_streams" in patches:
        _apply_data_streams(cfg, patches["data_streams"], applied)

    # -- sinks ---------------------------------------------------------------
    if "sinks" in patches:
        _apply_sink_patches(cfg, patches["sinks"], applied)

    # -- soc_modules ---------------------------------------------------------
    if "soc_modules" in patches:
        _apply_soc_module_patches(cfg, patches["soc_modules"], applied)

    # -- core overrides ------------------------------------------------------
    if "cores" in patches:
        _apply_core_patches(cfg, patches["cores"], applied)

    # -- raw escape hatch ----------------------------------------------------
    if "raw" in patches:
        _apply_raw_patches(cfg, patches["raw"], applied)

    ET.indent(tree, space="\t")
    tree.write(dest, encoding="utf-8", xml_declaration=True)

    return {
        "output_path": str(dest),
        "board": board,
        "applied_patches": applied,
        "used_default_output_dir": used_default,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _iter_config_blocks(parent: ET.Element, path: list[str]) -> list[ET.Element]:
    """Follow a chain of ConfigBlock names and return leaf-level children."""
    current = [parent]
    for step in path:
        next_level: list[ET.Element] = []
        for el in current:
            for cb in el.findall("ConfigBlock"):
                name_el = cb.find("Name")
                if name_el is not None and name_el.text and name_el.text.strip() == step:
                    next_level.append(cb)
        current = next_level
    result: list[ET.Element] = []
    for el in current:
        result.extend(el.findall("ConfigBlock"))
    return result


def _find_config_block(parent: ET.Element, name: str) -> ET.Element | None:
    for cb in parent.findall("ConfigBlock"):
        name_el = cb.find("Name")
        if name_el is not None and name_el.text and name_el.text.strip() == name:
            return cb
    return None


def _find_attribute(parent: ET.Element, attr_name: str) -> ET.Element | None:
    for child in parent:
        if child.tag in _ATTR_TAGS:
            name_el = child.find("Name")
            if name_el is not None and name_el.text and name_el.text.strip() == attr_name:
                return child
    return None


def _set_default_value(attr_el: ET.Element, value: str) -> None:
    dv = attr_el.find("DefaultValue")
    if dv is None:
        dv = ET.SubElement(attr_el, "DefaultValue")
    dv.text = value


def _set_attr_in_path(
    cfg: ET.Element, block_path: list[str], attr_name: str, value: str
) -> bool:
    current = cfg
    for block_name in block_path:
        current = _find_config_block(current, block_name)
        if current is None:
            return False
    attr_el = _find_attribute(current, attr_name)
    if attr_el is None:
        return False
    _set_default_value(attr_el, value)
    return True


def _apply_timestamp_generator(
    cfg: ET.Element, patch: Any, applied: list[str]
) -> None:
    if patch is None:
        return
    ts_block = _find_config_block(cfg, "Timestamp Generator")
    if ts_block is None:
        return
    if isinstance(patch, bool):
        attr_el = _find_attribute(ts_block, "Enable Timestamp Generator")
        if attr_el is not None:
            _set_default_value(attr_el, "true" if patch else "false")
            applied.append("timestamp_generator")
        return
    if not isinstance(patch, dict):
        return
    mapping = {
        "enabled":               ("Enable Timestamp Generator", lambda v: "true" if v else "false"),
        "module_base_address":   ("Module Base Address", str),
        "counter_base_frequency": ("Counter Base Frequency", str),
        "halt_on_debug":         ("Halt on Debug", lambda v: "true" if v else "false"),
        "mem_space":             ("MemSpace", str),
    }
    for key, (xml_name, conv) in mapping.items():
        if key in patch:
            attr_el = _find_attribute(ts_block, xml_name)
            if attr_el is not None:
                _set_default_value(attr_el, conv(patch[key]))
                applied.append(f"timestamp_generator.{key}")


def _apply_target_access(
    cfg: ET.Element, ta_patches: dict, applied: list[str]
) -> None:
    ta_block = _find_config_block(cfg, "Target Access")
    if ta_block is None:
        return
    mapping = {
        "server_address":       ("ServerAddress", str),
        "server_port":          ("ServerPort", str),
        "launch_name":          ("LaunchName", str),
        "target_access_method": ("Target Access Method", str),
        "reset_before_config":  ("ResetBeforeConfig", lambda v: "true" if v else "false"),
        "sync_server_port":     ("SyncServerPort", lambda v: "true" if v else "false"),
        "enable_user_code":     ("EnableUserCode", lambda v: "true" if v else "false"),
        "endianness":           ("endianness", str),
    }
    for key, (xml_name, conv) in mapping.items():
        if key in ta_patches:
            attr_el = _find_attribute(ta_block, xml_name)
            if attr_el is not None:
                _set_default_value(attr_el, conv(ta_patches[key]))
                applied.append(f"target_access.{key}")


def _apply_data_streams(
    cfg: ET.Element, ds_patches: dict, applied: list[str]
) -> None:
    ds_block = _find_config_block(cfg, "Data Streams")
    if ds_block is None:
        return
    if "trace_location" in ds_patches:
        val = ds_patches["trace_location"]
        if isinstance(val, list):
            val = ",".join(val)
        attr_el = _find_attribute(ds_block, "TraceLocation")
        if attr_el is not None:
            _set_default_value(attr_el, str(val))
            applied.append("data_streams.trace_location")
    if "continuous_collection" in ds_patches:
        attr_el = _find_attribute(ds_block, "Continuous Collection")
        if attr_el is not None:
            _set_default_value(attr_el, "true" if ds_patches["continuous_collection"] else "false")
            applied.append("data_streams.continuous_collection")


def _apply_sink_patches(
    cfg: ET.Element, sinks: dict, applied: list[str]
) -> None:
    """Apply per-sink patches.  sinks is {sink_name: {setting: value}}."""
    ds_block = _find_config_block(cfg, "Data Streams")
    if ds_block is None:
        return
    for sink_name, overrides in sinks.items():
        sink_cb = _find_config_block(ds_block, sink_name)
        if sink_cb is None:
            continue
        bool_mapping = {
            "enable_buffer":    "Enable Buffer",
            "scatter_gather":   "Scatter-Gather",
            "upload_manually":  "Upload Manually",
        }
        str_mapping = {
            "buffer_mode":               "BufferMode",
            "module_base_address":       "Module Base Address",
            "mem_space":                 "MemSpace",
            "trace_buffer_size":         "Trace Buffer Size",
            "trace_buffer_base_address": "Trace Buffer Base Address",
            "trace_collection_mode":     "TraceCollectionMode",
            "raw_trace_path":            "Raw Trace path",
        }
        for key, xml_name in bool_mapping.items():
            if key in overrides:
                attr_el = _find_attribute(sink_cb, xml_name)
                if attr_el is not None:
                    _set_default_value(attr_el, "true" if overrides[key] else "false")
                    applied.append(f"sinks.{sink_name}.{key}")
        for key, xml_name in str_mapping.items():
            if key in overrides:
                attr_el = _find_attribute(sink_cb, xml_name)
                if attr_el is not None:
                    _set_default_value(attr_el, str(overrides[key]))
                    applied.append(f"sinks.{sink_name}.{key}")


# Different SoC module types use different enable-attribute names; try both in
# order and stop at the first match.  No real template block carries both.
_SOC_ENABLE_ATTRS = ("Enable Trace", "Enable Port")


def _apply_soc_module_patches(
    cfg: ET.Element, modules: dict, applied: list[str]
) -> None:
    """Apply per-SoC-module patches.  modules is {module_name: {setting: value}}."""
    soc_block = _find_config_block(cfg, "SoC Modules")
    if soc_block is None:
        return

    str_mapping = {
        "module_base_address": "Module Base Address",
        "mem_space":           "MemSpace",
    }

    for mod_name, overrides in modules.items():
        mod_cb = _find_config_block(soc_block, mod_name)
        if mod_cb is None:
            continue

        if "enabled" in overrides:
            val = "true" if overrides["enabled"] else "false"
            for xml_name in _SOC_ENABLE_ATTRS:
                attr_el = _find_attribute(mod_cb, xml_name)
                if attr_el is not None:
                    _set_default_value(attr_el, val)
                    applied.append(f"soc_modules.{mod_name}.enabled")
                    break

        for key, xml_name in str_mapping.items():
            if key in overrides:
                attr_el = _find_attribute(mod_cb, xml_name)
                if attr_el is not None:
                    _set_default_value(attr_el, str(overrides[key]))
                    applied.append(f"soc_modules.{mod_name}.{key}")


def _apply_core_patches(
    cfg: ET.Element, core_patches: dict, applied: list[str]
) -> None:
    tg_block = _find_config_block(cfg, "Trace Generators")
    if tg_block is None:
        return
    core_block = _find_config_block(tg_block, "CORE")
    if core_block is None:
        return

    core_map: dict[str, ET.Element] = {}
    for cb in core_block.findall("ConfigBlock"):
        ui_attr = _find_attribute(cb, "UI Name")
        if ui_attr is not None:
            dv = ui_attr.find("DefaultValue")
            if dv is not None and dv.text:
                core_map[dv.text.strip()] = cb
        name_el = cb.find("Name")
        if name_el is not None and name_el.text:
            core_map.setdefault(name_el.text.strip(), cb)

    bool_mapping = {
        "enabled":         "Enable Trace",
        "timestamp":       "Timestamp",
        "start_on_launch": "Start Trace On Launch",
        "cycle_counting":  "Cycle Counting",
    }

    for ui_name, overrides in core_patches.items():
        cb = core_map.get(ui_name)
        if cb is None:
            continue

        for key, xml_name in bool_mapping.items():
            if key in overrides:
                attr_el = _find_attribute(cb, xml_name)
                if attr_el is not None:
                    _set_default_value(attr_el, "true" if overrides[key] else "false")
                    applied.append(f"cores.{ui_name}.{key}")

        if "trace_scenario" in overrides:
            attr_el = _find_attribute(cb, "TraceScenario")
            if attr_el is not None:
                val = overrides["trace_scenario"]
                if isinstance(val, list):
                    val = ",".join(val)
                _set_default_value(attr_el, str(val))
                applied.append(f"cores.{ui_name}.trace_scenario")

        if "module_base_address" in overrides:
            attr_el = _find_attribute(cb, "Module Base Address")
            if attr_el is not None:
                _set_default_value(attr_el, str(overrides["module_base_address"]))
                applied.append(f"cores.{ui_name}.module_base_address")

        if "mem_space" in overrides:
            attr_el = _find_attribute(cb, "MemSpace")
            if attr_el is not None:
                _set_default_value(attr_el, str(overrides["mem_space"]))
                applied.append(f"cores.{ui_name}.mem_space")

        if "elf_images" in overrides:
            ti_block = _find_config_block(cb, "Target Images")
            if ti_block is not None:
                images = overrides["elf_images"]
                if not isinstance(images, list):
                    images = [images]
                for idx, img_path in enumerate(images):
                    attr_el = _find_attribute(ti_block, f"Image {idx}")
                    if attr_el is not None:
                        _set_default_value(attr_el, str(img_path))
                applied.append(f"cores.{ui_name}.elf_images")


def _apply_raw_patches(
    cfg: ET.Element, raw: list[dict], applied: list[str]
) -> None:
    """Apply escape-hatch patches.  Each entry: {path: [...], attribute: str, value: str}."""
    for entry in raw:
        block_path = entry.get("path", [])
        attr_name = entry.get("attribute", "")
        value = str(entry.get("value", ""))
        if not attr_name:
            continue
        ok = _set_attr_in_path(cfg, block_path, attr_name, value)
        if ok:
            label = ".".join(block_path + [attr_name])
            applied.append(f"raw:{label}")
