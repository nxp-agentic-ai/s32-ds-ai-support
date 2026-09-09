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

"""Core Volkano client, installation discovery, and validation helpers.

This module is the component-local business logic reused by every S32SDAF
action handler. It is intentionally free of any MCP / FastMCP dependency so it
can be unit-tested in isolation and shared across handlers.

The logic here is ported verbatim from the legacy ``tools/s32sdaf_tools.py``
implementation; only the packaging changed. Handlers on top of this module map
its plain return dicts and raised errors onto the shared ``ActionOutcome``
envelope.
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from nxp.mcp.s32sdaf.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)

HEX_RE = re.compile(r"^[0-9A-Fa-f]+$")

GET_RESPONSE_KEY_TYPES = {
    "ADKP",
    "ADK1",
    "ADK2",
    "kUID",
    "kUID_RF",
    "kUID_PRE_FA",
    "ODAK",
}
REGISTER_KEY_TYPES = {
    "ADKP": "register_adkp",
    "ODAK": "register_odak",
    "ADK1": "register_adk1",
    "ADK2": "register_adk2",
    "kUID": "register_kuid",
    "kUID_RF": "register_kuid_rf",
    "kUID_PRE_FA": "register_kuid_pre_fa",
}
# Minimum applet version required per register key type. ADKP is intentionally
# omitted: register_adkp is supported on smart-card applet versions older than
# 1.4, so no applet-version warning should be emitted for it. The 1.4+/1.5+
# constraints apply only to the wrapped/OID-sensitive flows listed below.
REGISTER_COMMAND_MIN_APPLET = {
    "ODAK": "1.5+",
    "ADK1": "1.5+",
    "ADK2": "1.5+",
    "kUID": "1.4+",
    "kUID_RF": "1.4+",
    "kUID_PRE_FA": "1.4+",
}
GET_RESPONSE_KEY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _build_alias_map(keys: Iterable[str], name: str) -> dict[str, str]:
    """Build a case-insensitive alias map {lowercase: canonical}."""
    result: dict[str, str] = {}
    for k in keys:
        lower = k.lower()
        if lower in result:
            raise ValueError(
                f"Duplicate case-insensitive key '{lower}' in {name}: "
                f"'{result[lower]}' vs '{k}'"
            )
        result[lower] = k
    return result


_GET_RESPONSE_KEY_SELECTOR_ALIASES: dict[str, str] = _build_alias_map(
    GET_RESPONSE_KEY_TYPES, "GET_RESPONSE_KEY_TYPES"
)
_REGISTER_KEY_ALIASES: dict[str, str] = _build_alias_map(
    REGISTER_KEY_TYPES, "REGISTER_KEY_TYPES"
)
_GET_RESPONSE_KNOWN_PREFIXES: frozenset[str] = frozenset(
    k.upper() for k in GET_RESPONSE_KEY_TYPES
)
_GET_RESPONSE_INSTANCE_NAME_PATTERN = re.compile(r"^(.+)_(\d+)$")


# ---------------------------------------------------------------------------
# Volkano installation discovery
# ---------------------------------------------------------------------------

_NXP_ROOT = Path("C:/NXP")
_INSTALL_GLOBS = ["SDAF*", "S32SDAF*", "S32DS*", "S32DBG*"]

# Tie-break priority for the recommended installation when two installs share
# the same (highest) Volkano binary version. Lower rank wins; anything matching
# none of these prefixes sorts last. Intended preference order:
#   SDAF > S32SDAF > S32DS > S32DBG.
# NOTE: the "S32SDAF" prefix must be tested before "SDAF" during matching,
# because "S32SDAF..." also contains "SDAF" as a substring; testing the more
# specific prefix first prevents an "S32SDAF" folder from being mis-ranked as a
# plain "SDAF" match.
_INSTALL_ROOT_MATCH_ORDER = ("S32SDAF", "SDAF", "S32DS", "S32DBG")
_INSTALL_ROOT_RANK = {"SDAF": 0, "S32SDAF": 1, "S32DS": 2, "S32DBG": 3}


def install_root_priority(install_root: str) -> int:
    """Return the tie-break rank for an install root path (lower wins).

    Preference order is C:/NXP/SDAF* > C:/NXP/S32SDAF* > C:/NXP/S32DS* >
    C:/NXP/S32DBG*. Any install root not matching one of these prefixes ranks
    last.
    """

    name = Path(install_root).name.upper()
    for prefix in _INSTALL_ROOT_MATCH_ORDER:
        if name.startswith(prefix):
            return _INSTALL_ROOT_RANK[prefix]
    return len(_INSTALL_ROOT_RANK)




def parse_version_tuple(version: Optional[str]) -> Tuple[int, ...]:
    """Parse a dotted numeric version string (e.g. "1.4.0") into a tuple."""
    if not version:
        return ()
    match = _VERSION_RE.search(version)
    if not match:
        return ()
    return tuple(int(n) for n in match.group(1).split("."))



# A version is a dotted numeric run of at least two components (e.g. "3.6.10").
# Matching this instead of every digit group avoids pulling the "32" out of the
# product-name token "S32DS" (which produced bogus versions like "32.3.6.10")
# and rejects folders with no real version (e.g. "sdaf_Release_win32_latest").
_VERSION_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+)+)")


def extract_version_tuple(folder_name: str) -> Tuple[int, ...]:
    """Extract a numeric version tuple from a folder name for sorting.

    Only a dotted version substring (two or more components) is recognized, so
    digits that are part of the product-name prefix (e.g. the "32" in "S32DS")
    are not mistaken for a version component.
    """
    match = _VERSION_RE.search(folder_name)
    if not match:
        return ()
    return tuple(int(n) for n in match.group(1).split("."))



# Matches the Volkano binary version line, e.g. "Version: 1.4.0 (built on ...)".
_VOLKANO_VERSION_LINE_RE = re.compile(r"^\s*Version:\s*(\d+(?:\.\d+)+)", re.MULTILINE)


def query_volkano_binary_version(exe: Path) -> Optional[str]:
    """Return the real Volkano binary version by running ``volkano.exe -v``.

    The version reported by ``volkano.exe`` (e.g. "1.4.0") is the tool/DLL
    version and is independent of the S32DS install-folder version (e.g.
    "3.6.10"). Returns None if the binary cannot be executed or its output does
    not contain a recognizable ``Version:`` line.
    """
    try:
        completed = subprocess.run(
            [str(exe), "-v"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(exe.parent),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _logger.warning("Could not query Volkano version from %s: %s", exe, exc)
        return None

    combined = f"{completed.stdout}\n{completed.stderr}"
    match = _VOLKANO_VERSION_LINE_RE.search(combined)
    if not match:
        _logger.warning("No 'Version:' line in volkano -v output from %s", exe)
        return None
    return match.group(1)


def find_volkano_installations() -> List[dict]:
    """Search under C:/NXP/S32DS*, C:/NXP/S32SDAF*, C:/NXP/SDAF*, and C:/NXP/S32DBG* for every volkano.exe.


    Returns a list of dicts, sorted by descending version (newest first).

    The reported ``version_label`` is the real Volkano binary version obtained
    by running ``volkano.exe -v``. The install-folder version (e.g. "3.6.10")
    is retained separately as ``install_version_label`` and is only used as a
    sort key / fallback, since it reflects the S32DS install rather than the
    Volkano tool itself.
    """
    results: List[dict] = []

    if not _NXP_ROOT.exists():
        _logger.warning("NXP root folder not found: %s", _NXP_ROOT)
        return results

    for glob in _INSTALL_GLOBS:
        for install_root in sorted(_NXP_ROOT.glob(glob)):
            if not install_root.is_dir():
                continue
            for exe in install_root.rglob("volkano.exe"):
                folder = exe.parent
                ver_tuple = extract_version_tuple(install_root.name)
                install_ver_label = (
                    ".".join(str(n) for n in ver_tuple) if ver_tuple else "unknown"
                )
                binary_ver = query_volkano_binary_version(exe)
                ver_label = binary_ver if binary_ver else install_ver_label
                # Prefer the real Volkano binary version (e.g. 1.4.0) for
                # ranking; fall back to the install-folder version only when
                # the binary could not be queried.
                binary_ver_tuple = parse_version_tuple(binary_ver)
                sort_version = binary_ver_tuple if binary_ver_tuple else ver_tuple
                results.append(
                    {
                        "volkano_folder": str(folder),
                        "install_root": str(install_root),
                        "version_tuple": ver_tuple,
                        "version_label": ver_label,
                        "install_version_label": install_ver_label,
                        "binary_version": binary_ver,
                        "_sort_version": sort_version,
                    }
                )

    # Recommended selection: highest Volkano binary version wins. When several
    # installs share the same highest version, fall back to the install-path
    # priority order C:/NXP/SDAF* > C:/NXP/S32DS* > C:/NXP/S32DBG*.
    # reverse=True sorts the highest version first. For the path-priority
    # tie-break, lower rank should win, so negate it: with reverse=True the
    # largest (least-negative) rank -- i.e. the highest-priority path -- comes
    # first among installs that share the same version.
    results.sort(
        key=lambda r: (r["_sort_version"], -install_root_priority(r["install_root"])),
        reverse=True,
    )

    for r in results:
        r.pop("_sort_version", None)
    return results



def resolve_volkano_folder(volkano_folder: Optional[str], config_path: str = "") -> str:
    """Return volkano_folder if provided, then config_path, then auto-discover.

    Raises RuntimeError if nothing is found.
    """
    if volkano_folder:
        return volkano_folder
    if config_path:
        _logger.info("Using configured installation_path: %s", config_path)
        return config_path

    candidates = find_volkano_installations()
    if not candidates:
        raise RuntimeError(
            "volkano.exe was not found under C:/NXP/S32DS*, C:/NXP/S32SDAF*, C:/NXP/SDAF*, or C:/NXP/S32DBG*. "

            "Install SDAF or provide 'volkano_folder' location explicitly."
        )

    best = candidates[0]
    _logger.info(
        "Auto-discovered volkano installation (newest): %s  [version %s]",
        best["volkano_folder"],
        best["version_label"],
    )
    return best["volkano_folder"]


# ---------------------------------------------------------------------------
# Validation helpers (return an error string, or None when valid)
# ---------------------------------------------------------------------------

# Flags whose *following* value carries secret material and must never appear
# in logs or in the ``command`` field echoed back to the client. Includes
# -input_key / -new_pwd used by volkano_utils.exe (wrap_key / password change),
# which the original list omitted.
_SENSITIVE_FLAGS: frozenset[str] = frozenset(
    {"-pw", "--password", "-key", "-keybin", "-input_key", "-new_pwd"}
)


def redact_sensitive_args(args: list[str]) -> list[str]:
    """Redact the value following any sensitive flag (see _SENSITIVE_FLAGS)."""
    redacted: list[str] = []
    skip_next = False
    for arg in args:
        if skip_next:
            redacted.append("***")
            skip_next = False
        elif arg in _SENSITIVE_FLAGS:
            redacted.append(arg)
            skip_next = True
        else:
            redacted.append(arg)
    return redacted


def validate_volkano_installation(folder: str) -> None:
    """Raise FileNotFoundError if the Volkano installation folder is invalid.

    The folder is normalized via Path.resolve() before use so that relative
    segments (".."), redundant separators, and mixed slashes collapse to a
    single canonical path. This is a robustness measure for operator-supplied
    paths; it intentionally does not enforce an allow-list of roots because
    users may legitimately point at custom install locations.
    """
    try:
        resolved = Path(folder).resolve(strict=False)
    except (OSError, ValueError) as exc:
        raise FileNotFoundError(f"Invalid installation path '{folder}': {exc}") from exc

    exe = resolved / "volkano.exe"
    if not exe.is_file():
        raise FileNotFoundError(
            f"volkano.exe not found at {exe}. "
            "Check that 'volkano_folder' points to the correct installation directory."
        )



def validate_uid(uid: str) -> Optional[str]:
    if len(uid) not in (16, 32):
        return "UID must be 16 hex characters (8 bytes) or 32 hex characters (16 bytes)."
    if not HEX_RE.fullmatch(uid):
        return "UID must contain only hexadecimal characters."
    return None


def validate_password(name: str, value: str) -> Optional[str]:
    """Validate a Volkano smart-card user password.

    Password rules from the SDAF User Guide: must not be null/empty and must be
    between 4 and 127 characters (inclusive). Returns an error string, or None
    when the value is valid. The value itself is never included in the error
    message so secrets do not leak into logs or client responses.
    """
    if not value:
        return f"{name} must not be empty."
    if len(value) < 4 or len(value) > 127:
        return f"{name} must be between 4 and 127 characters long."
    return None


def validate_hex_param(name: str, value: str, *, even_length: bool = True) -> Optional[str]:

    if not value:
        return f"{name} must not be empty."
    if not HEX_RE.fullmatch(value):
        return f"{name} must contain only hexadecimal characters."
    if even_length and len(value) % 2 != 0:
        return f"{name} must contain an even number of hexadecimal characters."
    return None


def validate_get_response_key_name(key_name: str) -> Optional[str]:
    if not str(key_name).strip():
        return "key_name must be a non-empty key name returned by Volkano discover."
    if not GET_RESPONSE_KEY_NAME_PATTERN.fullmatch(str(key_name)):
        return (
            "key_name contains unsupported characters. Use the exact key name returned by "
            "Volkano discover/query output."
        )
    return None


def normalize_get_response_key_selector(key: str) -> str:
    if not key:
        return key
    return _GET_RESPONSE_KEY_SELECTOR_ALIASES.get(key.lower(), key)


def looks_like_known_get_response_key(key: str) -> bool:
    if not key:
        return False
    upper = key.upper()
    if upper in _GET_RESPONSE_KNOWN_PREFIXES:
        return True
    match = _GET_RESPONSE_INSTANCE_NAME_PATTERN.match(upper)
    if match:
        return match.group(1) in _GET_RESPONSE_KNOWN_PREFIXES
    return False


def normalize_register_key_type(key_type: Optional[str]) -> Optional[str]:
    if not key_type:
        return None
    raw = key_type.strip()
    if not raw:
        return None
    return _REGISTER_KEY_ALIASES.get(raw.lower())


def validate_oid_16_bytes(oid: str) -> Optional[str]:
    err = validate_hex_param("oid", oid)
    if err:
        return err
    if len(oid) != 32:
        return "OID must be exactly 32 hex characters (16 bytes)."
    return None


def validate_uid_16_bytes(uid: str) -> Optional[str]:
    err = validate_uid(uid)
    if err:
        return err
    if len(uid) != 32:
        return "This key type requires a 16-byte UID, so uid must be exactly 32 hex characters."
    return None


def validate_wrapped_key(name: str, key: str) -> Optional[str]:
    err = validate_hex_param(name, key)
    if err:
        return err
    if len(key) != 512:
        return f"{name} must be exactly 512 hex characters (256 bytes)."
    return None


def validate_key_index(key_index: Optional[int]) -> Optional[str]:
    if key_index is None:
        return "key_index is required."
    if not isinstance(key_index, int):
        return "key_index must be an integer in the range 0..15."
    if key_index < 0 or key_index > 15:
        return "key_index must be in the range 0..15."
    return None


def normalize_adk2_key_type(key_type: Optional[str]) -> Optional[str]:
    if key_type is None:
        return None
    value = str(key_type).strip().upper()
    if value not in {"AES", "ECC"}:
        return None
    return value


def applet_warning(normalized_key_type: Optional[str]) -> Optional[str]:
    min_version = REGISTER_COMMAND_MIN_APPLET.get(normalized_key_type or "")
    if min_version:
        return (
            f"This command requires a smart card with applet version {min_version}. "
            f"If the card is older, Volkano may return unsupported-operation style errors."
        )
    return None


# ---------------------------------------------------------------------------
# VolkanoClient
# ---------------------------------------------------------------------------

class VolkanoClient:
    """Thin async wrapper around volkano.exe / volkano_utils.exe."""

    def __init__(self, base_folder: str) -> None:
        self.base_folder = Path(base_folder)
        self._lock = asyncio.Lock()

    async def _exec(self, exe: Path, args: list[str]) -> dict:
        # Fail-fast serialization: if another coroutine already holds the lock
        # for this client instance, return immediately instead of queuing.
        #
        # NOTE: do not use ``asyncio.wait_for(self._lock.acquire(), timeout=0)``
        # here. With timeout=0 the acquire coroutine is wrapped in a Task that
        # has not been scheduled yet, so wait_for cancels it and raises
        # TimeoutError on EVERY call -- even when the lock is free -- which
        # incorrectly reports "Client is already executing a command."
        #
        # A synchronous ``locked()`` check followed by ``acquire()`` is safe in
        # asyncio's single-threaded event loop: no other coroutine can run
        # between the check and the acquire, and acquiring an uncontended lock
        # completes without yielding, so there is no TOCTOU window to close.
        if self._lock.locked():
            return {
                "status": "error",
                "exit_code": -1,
                "output": "Client is already executing a command.",
            }
        await self._lock.acquire()


        try:
            try:
                if not exe.is_file():
                    return {
                        "status": "error",
                        "exit_code": -1,
                        "output": f"Executable not found: {exe}",
                    }
                cmd = [str(exe)] + [str(a) for a in args]

                _logger.info("Executing: %s", " ".join(redact_sensitive_args(cmd)))

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.base_folder),
                )
                stdout, stderr = await process.communicate()

                out = stdout.decode("utf-8", errors="replace").strip()
                err = stderr.decode("utf-8", errors="replace").strip()
                combined = out or err

                status = "ok" if process.returncode == 0 else "error"
                return {
                    "status": status,
                    "exit_code": process.returncode,
                    "output": combined,
                    "command": " ".join(redact_sensitive_args(cmd)),
                }
            except Exception as exc:
                _logger.exception("Failed to execute %s", exe)
                return {"status": "error", "exit_code": -1, "output": f"Exception: {exc}"}
        finally:
            self._lock.release()

    async def run_volkano(self, args: list[str], password: Optional[str] = None) -> dict:

        exe = self.base_folder / "volkano.exe"
        full_args: list[str] = []
        if password:
            full_args += ["-pw", password]
        full_args += args
        return await self._exec(exe, full_args)

    async def run_volkano_utils(self, args: list[str]) -> dict:
        exe = self.base_folder / "volkano_utils.exe"
        return await self._exec(exe, args)

    async def wrap_key(self, plain_key: str, public_key: str) -> dict:
        return await self.run_volkano_utils(
            ["-cmd", "wrap_key", "-input_key", plain_key, "-key", public_key]
        )
