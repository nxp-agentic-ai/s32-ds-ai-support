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

"""Helper for resolving configuration paths against the config file location.

Relative paths in a YAML config file are resolved against the directory that
contains the config file, so users can launch MCP servers from any working
directory without setting ``cwd`` in their MCP client settings.

Resolution is explicit: each component calls :func:`resolve_path` only for the
settings it knows to be file-system paths. Values that are not paths (log
format strings, provider names, model identifiers, ...) are never passed to it.
"""
from pathlib import Path


def resolve_path(value: str, base_dir: Path) -> str:
    """Resolve a single path *value* against *base_dir*.

    An empty string is returned unchanged (empty means "unset/disabled" for
    optional fields such as ``skills`` and ``logging.file``). A leading ``~`` is
    expanded to the user home directory. An absolute path is normalised and
    returned. A relative path is joined onto *base_dir* and resolved to an
    absolute path.

    Args:
        value:    Path string taken from a known path config field.
        base_dir: Directory relative paths are resolved against, typically
                  ``Path(config_file_path).resolve().parent``.

    Returns:
        The resolved absolute path, or the original value when it is empty.
    """
    if not value:
        return value
    p = Path(value).expanduser()
    if p.is_absolute():
        return str(p)
    return str((base_dir / p).resolve())


def resolve_model_ref(value: str, base_dir: Path) -> str:
    """Resolve a model reference that may be a path OR a bare model id.

    Some config fields (e.g. ``embedder.model`` / ``reranker.model``) accept
    either a filesystem path to a pre-downloaded model directory OR a bare
    HuggingFace Hub identifier such as ``"BAAI/bge-base-en-v1.5"``. A bare id
    must be passed through untouched so the underlying library can download it
    into the cache; only path-like values are resolved against *base_dir*.

    A value is treated as a path when it:

    * is empty (returned unchanged),
    * starts with ``~``, ``./``, ``../``, ``.\\`` or ``..\\``,
    * is an absolute path, or
    * refers to an existing entry under *base_dir*.

    Any other value (e.g. ``"org/name"`` HuggingFace ids) is returned unchanged.

    Args:
        value:    Model reference from a config field.
        base_dir: Directory relative paths are resolved against.

    Returns:
        The resolved absolute path for path-like values, otherwise the
        original value unchanged.
    """
    if not value:
        return value
    if value.startswith(("~", "./", "../", ".\\", "..\\")):
        return resolve_path(value, base_dir)
    p = Path(value).expanduser()
    if p.is_absolute():
        return resolve_path(value, base_dir)
    if (base_dir / p).exists():
        return resolve_path(value, base_dir)
    # Bare model identifier (e.g. a HuggingFace Hub id) - leave untouched.
    return value


