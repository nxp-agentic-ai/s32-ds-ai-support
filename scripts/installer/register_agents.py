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
Auto-register the S32DS MCP gateway into AI agents after installation.
Also copies bundled skills into the correct per-agent skills directory.

Strategies (the single discriminator the engine switches on):

    "deeplink"  -> fastmcp builds the URL (format + the agent does the merge);
                   we only open it. Opens the agent's install dialog.
    "config"    -> we merge a minimal, clean JSON entry ourselves
                   ({command, args} only). Neighbouring server entries are
                   left byte-for-byte untouched.

    "config_yaml" -> we merge a native YAML config entry ourselves, reusing
                   fastmcp's _slugify (id) + StdioMCPServer (command/args);
                   used for Goose, whose compiled command allowlist rejects an
                   arbitrary-launcher deeplink but accepts a config entry.
    "cli"       -> the agent's own CLI performs the merge (e.g. `code --add-mcp`);
                   we only supply the argv builder and the probe binary.
"""

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path

from typing import Any
from fastmcp.mcp_config import StdioMCPServer

from fastmcp.cli.install.claude_desktop import get_claude_config_path
from fastmcp.cli.install.cursor import generate_cursor_deeplink
from fastmcp.cli.install.goose import _slugify
from fastmcp.cli.install.shared import open_deeplink


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write `data` as pretty JSON to `path` atomically via a temp file."""

    content = json.dumps(data, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".mcp_tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _merge_config_clean(
    path: Path,
    name: str,
    server: StdioMCPServer,
) -> None:
    """Merge a minimal server entry (command/args only) into an MCP JSON
    config, leaving all other server entries untouched. Raises RuntimeError
    if the existing file is not valid JSON or not a JSON object.
    """

    _ensure_config_seed(path)
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except OSError as exc:
        raise RuntimeError(f"Cannot read MCP config at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"MCP config at {path} contains invalid JSON (line {exc.lineno}). "
            "Please fix or remove it before re-running the installer."
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            f"MCP config at {path} must be a JSON object, "
            f"got {type(data).__name__}."
        )
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers

    # Derive the entry from the model; drop defaults ({} env, "stdio"
    # transport) and None optionals so only caller-set fields remain.
    servers[name] = server.model_dump(
        mode="json",
        exclude_none=True,
        exclude_defaults=True,
    )

    _atomic_write_json(path, data)


def _ensure_config_seed(path: Path) -> None:
    """Seed `path` with a `{"mcpServers": {}}` skeleton when it is absent or
    empty; leave any existing file untouched.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = path.read_text(encoding="utf-8").strip()
    except OSError:
        existing = ""
    if existing:
        return  # a file is already present; never overwrite it here
    _atomic_write_json(path, {"mcpServers": {}})


# fastmcp exposes a public locator ONLY for Claude Desktop. For every other

# config-file agent we provide a minimal well-known locator. Each returns the
# config-file Path, or None if the agent does not appear to be installed (its
# parent directory is missing) so the engine can skip it cleanly.
def _user_app_config_root() -> Path:
    """Per-user application config root for the current platform."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _claude_desktop_config() -> Path | None:
    """Claude Desktop config file, via fastmcp's own directory locator."""
    config_dir = get_claude_config_path()
    if config_dir is None:
        return None
    return config_dir / "claude_desktop_config.json"


def _vero_settings() -> Path | None:
    """Vero (VS Code extension) per-user MCP settings file.

    This is the ONLY agent that genuinely has no upstream locator anywhere
    (not in fastmcp, not a public CLI) - so we resolve it by well-known path.
    """
    base = (
        _user_app_config_root()
        / "Code"
        / "User"
        / "globalStorage"
        / "ace-dma.vero-dev"
        / "settings"
    )
    if not base.parent.exists():
        return None
    return base / "vero_mcp_settings.json"


def _cursor_link(name: str, server: StdioMCPServer) -> tuple[str, str]:
    return generate_cursor_deeplink(name, server), "cursor"


def _goose_config_yaml() -> Path | None:

    """Goose user config file (config.yaml).

    Goose's accepted-command allowlist is compiled into the Goose binary, so a
    deeplink for an arbitrary launcher (run-mcp.bat) is rejected. Writing the
    extension straight into config.yaml under `extensions:` bypasses that
    allowlist (this is the documented "config entry" install path). Returns
    None if Goose does not appear to be installed.
    """
    if sys.platform == "win32":
        base = _user_app_config_root() / "Block" / "goose" / "config"
    else:
        base = Path.home() / ".config" / "goose"
    if not base.parent.exists():
        return None
    return base / "config.yaml"


def _goose_write(path: Path, name: str, server: StdioMCPServer) -> None:
    """Merge an stdio extension entry for `server` into Goose's config.yaml.

    Reuses fastmcp's _slugify for the extension id and StdioMCPServer for the
    command/args, but writes the Goose-native `extensions:` schema (which
    fastmcp has no writer for - it only offers a deeplink). Preserves every
    other key in the file and is idempotent on the extension id.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, yaml.YAMLError):
            data = {}

    extensions = data.get("extensions")
    if not isinstance(extensions, dict):
        extensions = {}
        data["extensions"] = extensions
    ext_id = _slugify(name)
    extensions[ext_id] = {
        "enabled": True,
        "type": "stdio",
        "name": name,
        "cmd": server.command,
        "args": list(server.args),
        "timeout": 300,
    }

    path.write_text(
        yaml.safe_dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _vscode_add_mcp_argv(name: str, server: StdioMCPServer) -> list[str]:

    """Argv for VS Code's official `code --add-mcp <json>` command.

    VS Code performs the (non-destructive) merge into the user MCP config
    itself, so we never edit a VS Code file by hand.
    """
    payload = {
        "name": name,
        "command": server.command,
        "args": server.args,
    }
    return ["code", "--add-mcp", json.dumps(payload)]


def _claude_skills_dir() -> Path | None:
    """Skills directory for Claude Desktop."""
    return Path.home() / ".claude" / "skills"


def _vero_skills_dir() -> Path | None:
    """Skills directory for Vero."""
    return Path.home() / ".vero" / "skills"


def _vscode_skills_dir() -> Path | None:
    """Skills directory for VS Code (shared ~/.agents/skills)."""
    return Path.home() / ".agents" / "skills"


def _cursor_skills_dir() -> Path | None:
    """Skills directory for Cursor."""
    return Path.home() / ".cursor" / "skills"


def _goose_skills_dir() -> Path | None:
    """Skills directory for Goose (shared ~/.agents/skills)."""
    return Path.home() / ".agents" / "skills"


# Recognised keys:
#   key       : stable identifier used by --register / reporting
#   label     : human-readable name
#   strategy  : "deeplink" | "config" | "cli"  (the only engine discriminator)
#   link      : (deeplink)  (name, server) -> (url, scheme)
#   locate    : (config)    () -> Path | None   (config file; None = not installed)
#   probe     : (cli)       binary name checked with shutil.which()
#   argv      : (cli)       (name, server) -> list[str]
#   skills_dir: () -> Path  skills destination for this agent (always returns a path)

AGENTS: list[dict[str, Any]] = [
    {
        "key": "claude-desktop",
        "label": "Claude Desktop",
        "strategy": "config",
        "locate": _claude_desktop_config,
        "skills_dir": _claude_skills_dir,
    },
    {
        "key": "vero",
        "label": "Vero",
        "strategy": "config",
        "locate": _vero_settings,
        "skills_dir": _vero_skills_dir,
    },
    {
        "key": "vscode",
        "label": "VS Code",
        "strategy": "cli",
        "probe": "code",
        "argv": _vscode_add_mcp_argv,
        "skills_dir": _vscode_skills_dir,
    },
    {
        "key": "cursor",
        "label": "Cursor",
        "strategy": "deeplink",
        "link": _cursor_link,
        "skills_dir": _cursor_skills_dir,
    },
    {
        "key": "goose",
        "label": "Goose",
        "strategy": "config_yaml",
        "locate": _goose_config_yaml,
        "write": _goose_write,
        "skills_dir": _goose_skills_dir,
    },
]


def _agents_for(only: list[str] | None) -> list[dict[str, Any]]:
    """Resolve the descriptor rows targeted by an `only` key list.

    `only is None`  -> every agent (the caller, e.g. the menu, narrows it).
    `only=[...]`    -> just the rows whose `key` is listed (order: AGENTS).
    Unknown keys are ignored silently.
    """
    if only is None:
        return list(AGENTS)
    wanted = {k.strip().lower() for k in only}
    return [a for a in AGENTS if a["key"] in wanted]


def register_one(
    agent: dict[str, Any],

    name: str,
    command: str,
    args: list[str],
) -> str:
    """Register the gateway into a single agent. Returns a status string:
    "ok", "skipped" (agent not installed), or "error: <msg>".
    """
    server = StdioMCPServer(command=command, args=args)
    strategy = agent["strategy"]
    try:
        if strategy == "deeplink":
            url, scheme = agent["link"](name, server)
            if not open_deeplink(url, expected_scheme=scheme):
                return "error: could not open deeplink"
            return "ok"

        if strategy == "config":
            path = agent["locate"]()
            if path is None:
                return "skipped"
            # Self-contained clean JSON merge: derives the entry from the
            # StdioMCPServer model (dropping defaults/None) and leaves every
            # neighbouring server entry untouched.
            _merge_config_clean(path, name, server)
            return "ok"



        if strategy == "config_yaml":
            path = agent["locate"]()
            if path is None:
                return "skipped"
            # No fastmcp YAML writer exists for Goose; we merge the native
            # `extensions:` entry ourselves, but still reuse fastmcp's
            # _slugify (id) + StdioMCPServer (command/args) inside _goose_write.
            agent["write"](path, name, server)
            return "ok"

        if strategy == "cli":
            resolved = shutil.which(agent["probe"])
            if resolved is None:
                return "skipped"
            argv = agent["argv"](name, server)
            argv[0] = resolved
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                msg = (result.stderr or result.stdout or "").strip().splitlines()
                return f"error: {msg[-1] if msg else 'CLI exited non-zero'}"
            return "ok"

        return f"error: unknown strategy {strategy!r}"
    except Exception as exc:  # noqa: BLE001 - report, never crash the installer
        return f"error: {exc}"


def gateway_command(dest: Path) -> tuple[str, list[str]]:
    """Compute the gateway launch command for an install at `dest`.

    No path is hard-coded: the launcher script path is derived from the
    install destination at runtime, then passed into the engine.
    """
    if sys.platform == "win32":
        command = str((dest / "run-mcp.bat").resolve())
    else:
        command = str((dest / "run-mcp.sh").resolve())
    config = str((dest / "configs" / "gateway.stdio.yaml").resolve())
    return command, ["nxp.mcp.gateway", config]


def _choose_agents() -> list[dict[str, Any]] | None:
    """Show a plain numbered menu of all supported agents and let the user
    pick which to register. No auto-detection, no "all" pre-selection: the
    user types the numbers they want (or ENTER / 0 to skip).

    Returns the chosen descriptor rows, or None if the user skipped.
    """
    print("\n" + "=" * 62)
    print("  Register the S32DS MCP gateway with your AI agents")
    print("=" * 62)
    print("  Choose which agents to register (config files are merged;")
    print("  Cursor opens its own install dialog):\n")

    for i, agent in enumerate(AGENTS, 1):
        print(f"    {i}. {agent['label']}")
    print("\n  Enter number(s) separated by spaces (e.g. '1 2'),")
    print("  or press ENTER / 0 to skip.")

    try:
        raw = input("\n  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Skipped agent registration.")
        return None

    if raw == "" or raw == "0":
        print("  Skipped agent registration.")
        return None

    chosen: list[dict[str, Any]] = []
    invalid: list[str] = []
    for tok in raw.split():
        try:
            idx = int(tok) - 1
        except ValueError:
            invalid.append(tok)
            continue
        if 0 <= idx < len(AGENTS):
            if AGENTS[idx] not in chosen:
                chosen.append(AGENTS[idx])
        else:
            invalid.append(tok)
    if invalid:
        print(f"  Ignored invalid input: {', '.join(invalid)}")
    return chosen or None


def prompt_and_register(
    dest: Path,
    *,
    assume_yes: bool,
    only: list[str] | None,
    name: str = "s32ds_agentic_ai",
) -> bool:
    """Register the gateway into agents the user selects.

    - only=["none"]    -> skip registration entirely
    - only=[...]       -> register exactly those agent keys (no menu)
    - assume_yes=True  -> register ALL agents (no menu)
    - otherwise        -> show the explicit numbered menu and let the user pick
    """
    try:
        if only is not None and {k.strip().lower() for k in only} == {"none"}:
            return True

        if only is not None:
            targets = _agents_for(only)
        elif assume_yes:
            targets = list(AGENTS)
        else:
            chosen = _choose_agents()
            if not chosen:
                return True
            targets = chosen

        if not targets:
            print("\n  No matching agents to register.")
            return True

        command, args = gateway_command(dest)
        print()
        for agent in targets:
            status = register_one(agent, name, command, args)
            print(f"    {agent['label']:<16} {status}")
        print()
        return True
    except Exception as exc:  # noqa: BLE001 - report, never crash the installer
        print(f"\n  (Agent registration failed: {exc})")
        return False


def _find_skill_dirs(source_root: Path) -> list[Path]:
    """Return every leaf skill folder under source_root.

    A leaf skill folder is any directory that directly contains a SKILL.md
    file (matched case-insensitively). The result is de-duplicated and sorted.
    """
    found: set[Path] = set()
    if not source_root.is_dir():
        return []
    for manifest in source_root.rglob("*"):
        if manifest.is_file() and manifest.name.lower() == "skill.md":
            found.add(manifest.parent)
    return sorted(found)


def _copy_skills_to_dir(skill_dirs: list[Path], destination: Path, yes: bool) -> None:
    """Copy skill folders into destination, asking once before overwriting."""
    destination.mkdir(parents=True, exist_ok=True)
    print(f"      Destination: {destination}")

    existing = [d.name for d in skill_dirs if (destination / d.name).exists()]
    overwrite = True
    if existing and not yes:
        print(f"      {len(existing)} skill folder(s) already exist: "
              f"{', '.join(existing)}")
        answer = input("      Overwrite existing skill folders? [y/N]: ").strip().lower()
        overwrite = answer in ("y", "yes")

    copied = 0
    skipped = 0
    for skill_dir in skill_dirs:
        target = destination / skill_dir.name
        try:
            if target.exists():
                if not overwrite:
                    skipped += 1
                    print(f"      = {skill_dir.name} (kept existing)")
                    continue
                shutil.rmtree(target)
            shutil.copytree(skill_dir, target)
            copied += 1
            print(f"      + {skill_dir.name}")
        except OSError as exc:
            print(f"      ! {skill_dir.name} (failed: {exc})")
    summary = f"      Copied {copied}/{len(skill_dirs)} skill folder(s)."
    if skipped:
        summary += f" Kept {skipped} existing."
    print(summary)


def _choose_copy_skills_agents() -> list[dict[str, Any]] | None:
    """Interactive menu for selecting which agents to copy skills to.

    Shows each agent with its target skills directory. Returns the chosen
    descriptor rows, or None if the user skipped.
    """
    print("\n" + "=" * 62)
    print("  Copy S32 DS Agentic AI skills to your AI agents specific skill directory")
    print("=" * 62)
    print("  Choose which agents to copy skills to:\n")

    for i, agent in enumerate(AGENTS, 1):
        skills_path = agent["skills_dir"]()
        print(f"    {i}. {agent['label']:<16} -> {skills_path}")
    print("\n  Enter number(s) separated by spaces (e.g. '1 2'),")
    print("  or press ENTER / 0 to skip.")

    try:
        raw = input("\n  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Skipped skills copy.")
        return None

    if raw == "" or raw == "0":
        print("  Skipped skills copy.")
        return None

    chosen: list[dict[str, Any]] = []
    invalid: list[str] = []
    for tok in raw.split():
        try:
            idx = int(tok) - 1
        except ValueError:
            invalid.append(tok)
            continue
        if 0 <= idx < len(AGENTS):
            if AGENTS[idx] not in chosen:
                chosen.append(AGENTS[idx])
        else:
            invalid.append(tok)
    if invalid:
        print(f"  Ignored invalid input: {', '.join(invalid)}")
    return chosen or None


def prompt_and_copy_skills(
    source_root: Path,
    *,
    assume_yes: bool,
    only: list[str] | None,
    override_dir: Path | None = None,
) -> bool:
    """Copy bundled skills to the correct per-agent directories.

    Behavior:
    - override_dir is set  -> copy all skills to that single directory
    - only=[...]           -> copy to the skills dirs of those specific agents
    - assume_yes=True      -> copy to all agents without a menu
    - otherwise            -> show interactive menu

    Args:
        source_root: Path to the skills source tree (typically <dest>/skills).
        assume_yes: Skip interactive prompts; copy to all agents.
        only: List of agent keys to target (None means use menu or all).
        override_dir: If set, copy all skills here instead of per-agent dirs.
    """
    try:
        skill_dirs = _find_skill_dirs(source_root)
        print("\n[+] Copying skills...")
        if not skill_dirs:
            print(f"      No skill folders found under {source_root}")
            return True

        # If an explicit path override was given, just copy there.
        if override_dir is not None:
            _copy_skills_to_dir(skill_dirs, override_dir, yes=assume_yes)
            return True

        # Determine target agents.
        if only is not None:
            targets = _agents_for(only)
        elif assume_yes:
            targets = list(AGENTS)
        else:
            chosen = _choose_copy_skills_agents()
            if not chosen:
                return True
            targets = chosen

        if not targets:
            print("\n  No matching agents for skills copy.")
            return True

        # De-duplicate destinations (VS Code and Goose share ~/.agents/skills).
        seen_dirs: set[Path] = set()
        for agent in targets:
            dest = agent["skills_dir"]()
            if dest in seen_dirs:
                print(f"\n      {agent['label']:<16} (same dir as previous agent, skipped)")
                continue
            seen_dirs.add(dest)
            print(f"\n      [{agent['label']}]")
            _copy_skills_to_dir(skill_dirs, dest, yes=assume_yes)

        return True
    except Exception as exc:  # noqa: BLE001 - report, never crash the installer
        print(f"\n  (Skills copy failed: {exc})")
        return False


def main(argv: list[str] | None = None) -> int:
    """Run agent registration (and optionally skills copy) as a standalone command.

    Examples:
        # List all supported agents and what WOULD be written (no changes):
        python register_agents.py --dest . --list
        python register_agents.py --dest . --dry-run

        # Register into every supported agent, no menu:
        python register_agents.py --dest . --yes

        # Register into specific agents only:
        python register_agents.py --dest . --register vero,vscode

        # Interactive (numbered menu):
        python register_agents.py --dest .

        # Copy skills to the registered agents' skills dirs (interactive menu):
        python register_agents.py --dest . --register vero --copy-skills

        # Copy skills to a custom path (no menu, copies directly there):
        python register_agents.py --dest . --copy-skills /my/skills

        # Copy skills only (interactive menu, no registration):
        python register_agents.py --dest . --copy-skills --skip-register

        # Skip copy-skills entirely:
        python register_agents.py --dest . --skip-copy-skills
    """

    import argparse

    parser = argparse.ArgumentParser(
        prog="register_agents",
        description=(
            "Register the S32DS MCP gateway into your AI agents "
            "(Claude Desktop, Vero, VS Code, Cursor, Goose) "
            "and optionally copy bundled skills."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=main.__doc__,
    )
    parser.add_argument(
        "--dest",
        default=".",
        help="MCP install directory containing run-mcp.bat/.sh, configs/, and skills/ "
             "(default: current directory)",
    )
    parser.add_argument(
        "--name",
        default="s32ds_agentic_ai",
        help="Server name to register in the agent configs (default: s32ds_agentic_ai)",
    )
    parser.add_argument(
        "--register",
        metavar="A,B,...",
        default=None,
        help="Comma-separated agent keys to target "
             f"({', '.join(a['key'] for a in AGENTS)}); "
             "use 'none' to skip. Omit to show the interactive menu.",
    )
    parser.add_argument(
        "--skip-register",
        action="store_true",
        help="Skip agent registration entirely (useful when only copying skills).",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Do not show menus; register into all agents and/or copy skills.",
    )
    parser.add_argument(
        "--copy-skills",
        nargs="?",
        const="",
        default="",
        metavar="DIR",
        help=(
            "Copy bundled skills after registration. When DIR is given, copies "
            "all skills there. Otherwise shows an interactive menu to choose "
            "which agents to copy skills to. Skills are always copied unless "
            "--skip-copy-skills is given."
        ),
    )
    parser.add_argument(
        "--skip-copy-skills",
        action="store_true",
        help="Skip the skills copy step entirely.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all supported agents and their registration target, then exit.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the gateway command and the per-agent target/action without "
             "writing anything.",
    )
    args = parser.parse_args(argv)

    dest = Path(args.dest).resolve()
    only = args.register.split(",") if args.register is not None else None
    command, cmd_args = gateway_command(dest)

    if args.list or args.dry_run:
        print(f"\n  Install dir : {dest}")
        print(f"  Server name : {args.name}")
        print(f"  Command     : {command}")
        print(f"  Args        : {cmd_args}")
        print("\n  Supported agents:")
        for i, agent in enumerate(AGENTS, 1):
            if agent["strategy"] in ("config", "config_yaml"):
                loc = agent["locate"]()
                target = str(loc) if loc else "(installs on registration)"
            elif agent["strategy"] == "cli":
                target = f"{agent['probe']} --add-mcp"
            else:
                target = "deeplink dialog"

            skills_path = agent["skills_dir"]()
            print(f"    {i}. {agent['label']:<16} ({agent['key']}) "
                  f"[{agent['strategy']:<8}] -> {target}")
            print(f"       {'skills':<14}              -> {skills_path}")
        print()
        return 0

    # Agent registration step.
    if not args.skip_register:
        prompt_and_register(dest, assume_yes=args.yes, only=only, name=args.name)

    # Skills copy step - always runs unless --skip-copy-skills is given.
    if not args.skip_copy_skills:
        source_root = dest / "skills"
        override_dir = (
            Path(args.copy_skills).expanduser().resolve()
            if args.copy_skills
            else None
        )

        # When a specific path override is given, use it directly.
        # When --register was given (and no path override), copy to those agents.
        # Otherwise use the interactive menu (or all agents with --yes).
        copy_only = only if (override_dir is None) else None
        prompt_and_copy_skills(
            source_root,
            assume_yes=args.yes,
            only=copy_only,
            override_dir=override_dir,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
