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

import ast
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
import re


class S32DebuggerConfigGenerator:
    def __init__(self, base_folder: Path | str):
        self.base_folder = Path(base_folder)

    def _get_installed_bridge_script_path(self) -> Path:
        """Return the bridge path inside the S32Debugger install tree."""
        return (
            self.base_folder
            / "S32Debugger" / "Debugger" / "scripts"
            / "gdb_extensions" / "bridge" / "gdb_bridge.py"
        )

    def _get_bundled_bridge_script_path(self) -> Path:
        """Return the legacy bridge path bundled inside the MCP server (fallback)."""
        return Path(__file__).resolve().parent.parent / "gdb_bridge.py"

    def _get_bridge_script_path(self) -> Path:
        """Return the absolute path to the JSON-RPC bridge GDB extension.

        Prefer the installed location, fall back to the bundled copy. is_file()
        (not exists()) avoids selecting a stale directory with no importable module.
        """
        installed = self._get_installed_bridge_script_path()
        if installed.is_file():
            return installed
        return self._get_bundled_bridge_script_path()



    def _is_within(self, candidate: Path, root: Path) -> bool:
        """Return True if candidate is at or beneath root.

        relative_to() is safe against sibling-prefix bypasses and
        case-insensitive filesystem quirks.
        """
        try:
            candidate.relative_to(root.resolve())
            return True
        except ValueError:
            return False

    def _safe_join(self, base: Path, *parts: str) -> Path:

        """Join path parts onto base and verify the result stays within base.

        Guards against path traversal from caller-controlled inputs (soc_family,
        script_type, template_name). Raises ValueError if the candidate escapes base.
        """
        resolved_base = base.resolve()
        candidate = base.joinpath(*parts).resolve()
        try:
            candidate.relative_to(resolved_base)
        except ValueError:
            raise ValueError(f"Path traversal detected: '{candidate}' escapes '{resolved_base}'")
        return candidate


    def _safe_eval_template_expr(self, expr: str, variables: dict[str, object]) -> object:
        node = ast.parse(expr, mode="eval")

        def _eval(current):
            if isinstance(current, ast.Expression):
                return _eval(current.body)
            if isinstance(current, ast.Constant):
                return current.value
            if isinstance(current, ast.Name):
                if current.id in variables:
                    return variables[current.id]
                raise ValueError(f"Unknown template variable '{current.id}'")
            if isinstance(current, ast.UnaryOp) and isinstance(current.op, ast.USub):
                return -_eval(current.operand)
            if isinstance(current, ast.BinOp):
                left = _eval(current.left)
                right = _eval(current.right)
                if isinstance(current.op, ast.Add):
                    return left + right
                if isinstance(current.op, ast.Sub):
                    return left - right
                if isinstance(current.op, ast.Mult):
                    return left * right
                if isinstance(current.op, ast.Div):
                    return left / right
            raise ValueError("Unsupported template expression")

        return _eval(node)

    def _extract_template_defaults(self, template_path: Path) -> dict[str, object]:
        defaults: dict[str, object] = {}
        variables: dict[str, object] = {
            "S32DBG_PATH": str(self.base_folder).replace("\\", "/"),
        }
        pattern = re.compile(r"^(?P<name>[A-Za-z0-9_]+)\s*=\s*(?P<value>.+?)\s*$")
        with template_path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                match = pattern.match(line)
                if not match:
                    continue
                name = match.group("name")
                value_text = match.group("value")

                if name == "S32DBG_PATH":
                    value = str(self.base_folder).replace("\\", "/")
                else:
                    try:
                        value = ast.literal_eval(value_text)
                    except Exception:
                        try:
                            value = self._safe_eval_template_expr(value_text, variables)
                        except Exception:
                            continue

                variables[name] = value
                if name.startswith("_") or name.isupper():
                    defaults[name] = value
        return defaults

    def _compute_complete_core_name(
        self,
        soc_name: Optional[str],
        core_name: Optional[str],
        cluster_id: Optional[str],
        core_id: Optional[int],
        lockstep: Optional[bool],
        defaults: dict[str, object],
        script_type: str,
    ) -> str:
        complete = str(defaults.get("COMPLETECORESPEC") or defaults.get("COMPLETE_CORE_SPEC") or "")
        if complete:
            return complete
        if core_name:
            suffix = ""
            if core_id is not None:
                suffix += f"_{core_id}"
            if cluster_id:
                suffix += f"_{cluster_id}"
            if lockstep:
                suffix += "_lockstep"
            return f"{core_name}{suffix}"
        if script_type.lower() == "multicore" and soc_name:
            return f"{soc_name}_multicore"
        return soc_name or "core"

    def _normalize_template_overrides(
        self,
        overrides: dict[str, object],
        defaults: dict[str, object],
        script_type: str,
        template_text: str,
    ) -> dict[str, object]:
        normalized = {k.upper(): v for k, v in overrides.items() if v is not None}
        mapped: dict[str, object] = {}

        name_map = {
            "SOC_NAME": "_SOC_NAME",
            "PROBE_IP": "_PROBE_IP",
            "CORE_NAME": "_CORE_NAME",
            "CLUSTER_ID": "_CLUSTER_ID",
            "CORE_ID": "_CORE_ID",
            "LOCKSTEP": "_Core_LOCKSTEP",
            "JTAG_SPEED": "_JTAG_SPEED",
            "GDB_SERVER_PORT": "_GDB_SERVER_PORT",
            "CCS_IP": "_CCS_IP",
            "CCS_PORT": "_CCS_PORT",
            "IS_LOGGING_ENABLED": "_IS_LOGGING_ENABLED",
            "FILE_DEBUG": "_FILE_DEBUG",
            "INIT_SCRIPT": "_INIT_SCRIPT",
            "FILE_BIN": "_FILE_BIN",
            "FLASH_TYPE": "_FLASH_TYPE",
            "FLASH_NAME": "_FLASH_NAME",
            "S32DBG_PATH": "S32DBG_PATH",
            "SECURE_TYPE": "_SECURE_TYPE",
            "SECURE_KEY": "_SECURE_KEY",
            "LIFECYCLE": "_LIFECYCLE",
            "RESET_TYPE": "_RESET_TYPE",
            "RESET_DELAY": "_RESET_DELAY",
            "REMOTE_TIMEOUT": "_REMOTE_TIMEOUT",
            "GDB_TIMEOUT": "_GDB_TIMEOUT",
            "RESULTEXCEPTION": "_RESULTEXCEPTION",
        }

        for key, value in normalized.items():
            mapped[name_map.get(key, key)] = value

        complete_core = self._compute_complete_core_name(
            normalized.get("SOC_NAME") or defaults.get("_SOC_NAME") or defaults.get("SOC_NAME"),
            normalized.get("CORE_NAME") or defaults.get("_CORE_NAME") or defaults.get("CORE_NAME"),
            normalized.get("CLUSTER_ID") if "CLUSTER_ID" in normalized else defaults.get("_CLUSTER_ID") or defaults.get("CLUSTER_ID"),
            normalized.get("CORE_ID") if "CORE_ID" in normalized else defaults.get("_CORE_ID") or defaults.get("CORE_ID"),
            normalized.get("LOCKSTEP") if "LOCKSTEP" in normalized else defaults.get("_Core_LOCKSTEP") or defaults.get("CORE_LOCKSTEP") or defaults.get("LOCKSTEP"),
            defaults,
            script_type,
        )
        if "COMPLETECORESPEC" in template_text and "COMPLETECORESPEC" not in mapped:
            mapped["COMPLETECORESPEC"] = complete_core
        if "COMPLETE_CORE_SPEC" in template_text and "COMPLETE_CORE_SPEC" not in mapped:
            mapped["COMPLETE_CORE_SPEC"] = complete_core

        return mapped

    def _load_demo_utils_module(self):
        utils_path = self.base_folder / "S32Debugger" / "Debugger" / "scripts" / "utils" / "demo_utils.py"
        if not utils_path.exists():
            raise FileNotFoundError(f"demo_utils.py not found at {utils_path}")
        spec = importlib.util.spec_from_file_location("mcp_s32debugger_demo_utils", str(utils_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {utils_path}")
        module = importlib.util.module_from_spec(spec)
        scripts_root = str(utils_path.parent.parent).replace("\\", "/")
        old_sys_path = list(sys.path)
        if scripts_root not in sys.path:
            sys.path.insert(0, scripts_root)
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path = old_sys_path
        return module

    def _apply_demo_utils_tunables(self, demo_utils, values: dict[str, object]) -> None:
        tunables = {
            "_GDB_TIMEOUT": "_GDB_TIMEOUT",
            "_REMOTE_TIMEOUT": "_REMOTE_TIMEOUT",
            "_RESULTEXCEPTION": "_RESULTEXCEPTION",
            "_RESET_DELAY": "_RESET_DELAY",
            "_RESET_TYPE": "_RESET_TYPE",
            "_SECURE_TYPE": "_SECURE_TYPE",
            "_SECURE_KEY": "_SECURE_KEY",
            "_LIFECYCLE": "_LIFECYCLE",
            "_NON_STOP_MODE": "_NON_STOP_MODE",
        }

        for value_key, attr_name in tunables.items():
            if value_key in values:
                setattr(demo_utils, attr_name, values[value_key])

    def _format_gdb_py_value(self, value: object) -> str:
        if isinstance(value, bool):
            return "True" if value else "False"
        if value is None:
            return "None"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, Path):
            value = str(value)
        if isinstance(value, str):
            return json.dumps(value.replace("\\", "/"))
        return json.dumps(str(value))

    def _render_config_text(
        self,
        template_text: str,
        overrides: dict[str, object],
        script_type: str,
        template_name: str,
    ) -> str:
        rendered_lines: list[str] = []
        assign_pattern = re.compile(r"^(?P<indent>\s*)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.+?)\s*$")

        for raw_line in template_text.splitlines():
            stripped = raw_line.strip()
            if stripped in {"demo_utils.start_gta()", "demo_utils.start_gdb()"}:
                rendered_lines.append("# Removed: GDB/GTA startup (use MCP tools instead)")
                continue

            match = assign_pattern.match(raw_line)
            if not match:
                rendered_lines.append(raw_line)
                continue
            name = match.group("name")
            if name in overrides:
                rendered_value = self._format_gdb_py_value(overrides[name])
                rendered_lines.append(f"{match.group('indent')}{name} = {rendered_value}")
            else:
                rendered_lines.append(raw_line)

        header = [
            f"# Generated from template {template_name}",
            f"# Script type: {script_type}",
            f"# Generated at: {datetime.now().isoformat(timespec='seconds')}",
            "# Note: GDB/GTA startup removed - use MCP tools instead",
            "",
        ]
        return "\n".join(header + rendered_lines) + "\n"

    def _validate_bridge_script_path(self, bridge_script_path: Path, require_exists: bool = True) -> Path:
        """Validate the bridge script and return its canonical (resolved) path.

        Defence in depth: the generated config is executed by GDB's embedded
        interpreter, so the path is constrained to the allowed roots (the
        S32Debugger install tree and the MCP server package) and must be a real
        Python module. resolve() collapses symlinks/'..' so escapes are rejected.

        require_exists=False lets config generation run without the install tree
        (e.g. CI); existence is then verified at GDB start time.
        """
        resolved = bridge_script_path.resolve()
        # Allowed roots: the S32Debugger install tree and the MCP server
        # package directory (src/, the parent of this module's folder).
        allowed_roots = [
            self.base_folder.resolve(),
            Path(__file__).resolve().parent.parent,
        ]

        if not any(self._is_within(resolved, root) for root in allowed_roots):
            raise ValueError(
                f"Bridge script {bridge_script_path} resolves to {resolved}, "
                f"which is outside the allowed roots {[str(r) for r in allowed_roots]}"
            )


        # Verify the file actually exists before embedding its path in the
        # generated GDB config, unless the caller explicitly defers this to a
        # later pre-flight check (e.g. at GDB start time).
        if require_exists and not resolved.is_file():
            raise FileNotFoundError(f"Bridge script not found: {resolved}")

        if resolved.suffix != ".py":
            raise ValueError(f"Bridge script must be a .py file, got: {resolved}")


        module_name = resolved.stem
        if not module_name.isidentifier():
            raise ValueError(f"Bridge module name is not a valid Python identifier: {module_name!r}")

        return resolved

    def _prepend_bridge_block(self, path: Path, port: int, bridge_script_path: Optional[Path] = None) -> None:
        """Prepend a GDB-python block that starts the JSON-RPC bridge on the given port.

        The block must run before any blocking command (e.g. 'c'/'continue'),
        otherwise GDB blocks on the running target and the bridge never starts.
        """
        if bridge_script_path is None:
            # Pick the first candidate that is a real file so we never emit a
            # sys.path.insert() for a directory that does not exist here.
            candidates = [
                self._get_installed_bridge_script_path(),
                self._get_bundled_bridge_script_path(),
            ]
            existing = next((c for c in candidates if c.is_file()), None)
            if existing is None:
                # Fail loudly instead of baking a non-existent path into the
                # config (which later breaks GDB with "No module named 'gdb_bridge'").
                raise FileNotFoundError(
                    "JSON-RPC bridge script gdb_bridge.py was not found in any known "
                    f"location. Checked: {[str(c) for c in candidates]}. Verify the "
                    "S32Debugger installation path or the bundled MCP server bridge."
                )
            bridge_script_path = existing

        # Validate and canonicalize (symlink-safe, .py, valid identifier);
        # existence is deferred to GDB start time.
        resolved_script = self._validate_bridge_script_path(bridge_script_path, require_exists=False)
        safe_module = resolved_script.stem

        # Reference the bridge in place (single source of truth); do not copy it
        # next to the generated config.

        # Reject NUL/newline in the path before repr() so it cannot break out of
        # the generated Python line.
        script_dir_str = str(resolved_script.parent)

        if "\x00" in script_dir_str or "\n" in script_dir_str or "\r" in script_dir_str:
            raise ValueError(
                f"Bridge script path contains illegal characters: {script_dir_str!r}"
            )

        # repr() emits a correctly escaped Python string literal (quotes,
        # trailing backslashes on Windows).
        safe_dir = repr(script_dir_str)

        block = (
            "# Start the MCP GDB JSON-RPC bridge (added by S32Debugger config generator)\n"
            "python import sys\n"
            f"python sys.path.insert(0, {safe_dir})\n"
            f"python from {safe_module} import start_bridge\n"
            f"python start_bridge(port={int(port)})\n"
            "\n"
        )
        existing = path.read_text(encoding="utf-8", errors="replace")
        path.write_text(block + existing, encoding="utf-8")

    def _ensure_non_stop_mode(self, path: Path, value: object) -> None:
        """Ensure the generated config declares _NON_STOP_MODE.

        demo_utils does not emit it, so inject a 'py _NON_STOP_MODE = <val>' line
        if absent. The 'py ' prefix matches how demo_utils writes assignments so
        GDB evaluates it while sourcing the config.
        """
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?m)^\s*(?:py\s+)?_NON_STOP_MODE\s*=", text):
            return
        py_value = "True" if bool(value) else "False"
        line = f"py _NON_STOP_MODE = {py_value}\n"
        path.write_text(line + text, encoding="utf-8")

    async def generate_config_from_template(
        self,
        soc_family: str,
        script_type: str,
        template_name: str,
        output_name: Optional[str] = None,
        bridge_port: Optional[int] = None,
        overwrite: bool = False,
        **overrides,
    ) -> str:
        if not template_name or not str(template_name).strip():

            return "Error: template_name is required and must not be empty"
        if not soc_family or not str(soc_family).strip():
            return "Error: soc_family is required and must not be empty"
        if not script_type or not str(script_type).strip():
            return "Error: script_type is required and must not be empty"

        examples_root = self.base_folder / "S32Debugger" / "Examples"

        # Resolve the template path with a traversal guard so caller-controlled
        # soc_family/script_type/template_name cannot escape the examples root.
        try:
            template_path = self._safe_join(examples_root, soc_family, script_type, template_name)
        except ValueError as exc:
            return f"Error: {exc}"
        if not template_path.is_file():
            return f"Error: Template not found at {template_path}"

        try:
            template_text = template_path.read_text(encoding="utf-8", errors="replace")
            defaults = self._extract_template_defaults(template_path)
            values = dict(defaults)
            values["S32DBG_PATH"] = str(self.base_folder).replace("\\", "/")
            values.update(self._normalize_template_overrides(overrides, defaults, script_type, template_text))
            # Ensure NON_STOP_MODE is always present in the generated config
            # (default True) unless overridden by template or caller.
            values.setdefault("_NON_STOP_MODE", True)

            demo_utils = self._load_demo_utils_module()

            self._apply_demo_utils_tunables(demo_utils, values)
            if hasattr(demo_utils, "parameters_with_value"):
                demo_utils.parameters_with_value = {}
            if hasattr(demo_utils, "_FILE_CONFIGURATION"):
                demo_utils._FILE_CONFIGURATION = None
            if hasattr(demo_utils, "INSTALL_DIRECTORY"):
                demo_utils.INSTALL_DIRECTORY = None

            root_out_dir = self.base_folder / "generated_configs"
            root_out_dir.mkdir(parents=True, exist_ok=True)
            # Work in an isolated temp dir so partial artifacts never pollute
            # generated_configs/; only the final validated file lands there.
            work_dir = Path(tempfile.mkdtemp(prefix="mcp_cfg_"))
            try:
                return await self._generate_into_work_dir(
                    work_dir=work_dir,
                    values=values,
                    script_type=script_type,
                    output_name=output_name,
                    bridge_port=bridge_port,
                    demo_utils=demo_utils,
                    overwrite=overwrite,
                )
            finally:
                shutil.rmtree(work_dir, ignore_errors=True)

        except Exception as e:
            return f"Exception while generating config: {e}"

    async def _generate_into_work_dir(
        self,
        work_dir: Path,
        values: dict[str, object],
        script_type: str,
        output_name: Optional[str],
        bridge_port: Optional[int],
        demo_utils,
        overwrite: bool = False,
    ) -> str:
        current_directory = str(work_dir).replace("\\", "/")
        install_directory = str(self.base_folder).replace("\\", "/")
        init_script = str(values.get("_INIT_SCRIPT") or "")
        file_debug = values.get("_FILE_DEBUG")
        file_bin = values.get("_FILE_BIN")

        script_type_l = script_type.lower()
        if script_type_l == "flashprogrammer":
            demo_utils.initialize_FP_parameters_with_value(
                values.get("_SOC_NAME") or values.get("SOC_NAME") or "",
                values.get("_FLASH_TYPE") or "qspi",
                values.get("_FLASH_NAME") or "",
                values.get("_PROBE_IP") or "",
                values.get("_JTAG_SPEED") or 16000,
                values.get("_GDB_SERVER_PORT") or 45000,
                values.get("_CCS_IP") or "127.0.0.1",
                values.get("_CCS_PORT") or 41475,
                values.get("_IS_LOGGING_ENABLED") if values.get("_IS_LOGGING_ENABLED") is not None else True,
                values.get("_GDB_TIMEOUT", getattr(demo_utils, "_GDB_TIMEOUT", 7200)),
                values.get("_RESET_DELAY", getattr(demo_utils, "_RESET_DELAY", 2)),
                values.get("_RESET_TYPE", getattr(demo_utils, "_RESET_TYPE", "default")),
                values.get("_SECURE_TYPE"),
                values.get("_SECURE_KEY"),
                values.get("_LIFECYCLE"),
                values.get("_RESULTEXCEPTION", getattr(demo_utils, "_RESULTEXCEPTION", True)),
            )
            if values.get("_CORE_NAME"):
                demo_utils.initialize_FP_core_name(values.get("_CORE_NAME"))
            demo_utils.config_parameters_FP_SOC(
                current_directory,
                init_script,
                file_debug,
                file_bin,
                install_directory,
            )
        else:
            soc_name = values.get("_SOC_NAME") or values.get("SOC_NAME") or ""
            core_name = values.get("_CORE_NAME") or values.get("CORE_NAME") or ""
            probe_ip = values.get("_PROBE_IP") or ""
            jtag_speed = values.get("_JTAG_SPEED") or 16000
            gdb_server_port = values.get("_GDB_SERVER_PORT") or 45000
            ccs_ip = values.get("_CCS_IP") or "127.0.0.1"
            ccs_port = values.get("_CCS_PORT") or 41475
            is_logging_enabled = values.get("_IS_LOGGING_ENABLED") if values.get("_IS_LOGGING_ENABLED") is not None else True
            core_id = values.get("_CORE_ID", "")
            cluster_id = values.get("_CLUSTER_ID", "")
            lockstep = bool(values.get("_Core_LOCKSTEP", False))

            demo_utils.initialize_parameters_with_value(
                soc_name,
                core_name,
                probe_ip,
                jtag_speed,
                gdb_server_port,
                ccs_ip,
                ccs_port,
                is_logging_enabled,
                values.get("_SECURE_TYPE"),
                values.get("_SECURE_KEY"),
                values.get("_LIFECYCLE"),
            )
            demo_utils.create_complete_Core_Name(
                soc_name,
                core_name,
                core_id,
                cluster_id,
                lockstep,
            )
            demo_utils.config_parameters_SOC(
                current_directory,
                init_script,
                file_debug or "",
                install_directory,
            )

        generated_name = getattr(demo_utils, "_FILE_CONFIGURATION", None)
        if not generated_name:
            return "Error: demo_utils did not produce a configuration filename"
        generated_path = work_dir / str(generated_name)
        if not generated_path.exists():
            return f"Error: Expected generated config not found at {generated_path}"

        if output_name:
            final_name = output_name if output_name.lower().endswith(".txt") else output_name + ".txt"
        else:
            final_name = str(generated_name)

        final_path = self.base_folder / "generated_configs" / final_name
        # Collision policy: overwrite=True regenerates; an explicit colliding
        # output_name errors; an auto-generated name falls back to a timestamp.
        if final_path.exists():
            if overwrite:
                final_path.unlink()
            elif output_name:
                return (
                    f"Error: Config file already exists at {final_path}. "
                    "Provide a different output_name or pass overwrite=True."
                )
            else:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_path = final_path.parent / f"{final_path.stem}_{stamp}{final_path.suffix}"

        shutil.copyfile(str(generated_path), str(final_path))

        # demo_utils does not emit _NON_STOP_MODE, so inject it here.
        self._ensure_non_stop_mode(final_path, values.get("_NON_STOP_MODE", True))

        # Prepend the bridge block so it runs before any blocking command.
        if bridge_port is not None:
            self._prepend_bridge_block(final_path, int(bridge_port))


        return str(final_path)

    async def generate_script_from_template(
        self,
        soc_family: str,
        script_type: str,
        template_name: str,
        output_name: Optional[str] = None,
        **overrides,
    ) -> str:
        examples_root = self.base_folder / "S32Debugger" / "Examples"
        template_path = examples_root / soc_family / script_type / template_name
        if not template_path.exists():
            return f"Error: Template not found at {template_path}"

        try:
            template_text = template_path.read_text(encoding="utf-8", errors="replace")
            defaults = self._extract_template_defaults(template_path)
            mapped_overrides = self._normalize_template_overrides(overrides, defaults, script_type, template_text)
            rendered = self._render_config_text(template_text, mapped_overrides, script_type, template_name)
            out_dir = self.base_folder / "generated_scripts"
            out_dir.mkdir(parents=True, exist_ok=True)
            if output_name:
                if not output_name.lower().endswith(".py"):
                    output_name = output_name + ".py"
                out_path = out_dir / output_name
            else:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_path = out_dir / f"{template_path.stem}_{stamp}.py"
            out_path.write_text(rendered, encoding="utf-8")
            return str(out_path)
        except Exception as e:
            return f"Exception while generating script: {e}"

    async def prepare_config(self, script_path: str) -> str:
        script_file = Path(script_path)
        if not script_file.exists():
            return f"Error: Script file not found at {script_path}"
        out_dir = self.base_folder / "generated_configs"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{script_file.stem}.txt"
        shutil.copyfile(script_file, out_path)
        return str(out_path)

    async def generate_config_from_script(self, script_path: str) -> str:
        return await self.prepare_config(script_path)
