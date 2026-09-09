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

import logging
import os
from logging.handlers import RotatingFileHandler

# RotatingFileHandler defaults — 10 MiB per file, keep 5 backups
_FILE_MAX_BYTES = 10 * 1024 * 1024
_FILE_BACKUP_COUNT = 5

# Default timestamp format (strftime-compatible)
_DEFAULT_TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def _build_formatter(timestamp_format: str, fmt: str) -> logging.Formatter:
    """Build a :class:`logging.Formatter` from the given settings.

    Args:
        timestamp_format: ``strftime`` format string used as ``datefmt``.
                          Controls how ``%(asctime)s`` is rendered when the
                          token is present in *fmt*.
        fmt:              A standard Python ``%``-style logging format string,
                          e.g. ``"%(asctime)s [%(name)s] %(levelname)s %(message)s"``.
                          Passed directly to :class:`logging.Formatter` without
                          any transformation.  Use ``"%(message)s"`` to omit
                          all prefix columns including the timestamp.
    """
    datefmt = timestamp_format or _DEFAULT_TS_FORMAT
    return logging.Formatter(fmt or "%(message)s", datefmt=datefmt)


def setup_logging(config, mcp_server_name: str) -> logging.Logger:
    """Configure logging for a mcp server.

    The root logger is initialised at most once (``basicConfig`` is idempotent
    after the first call because it checks for existing handlers).  Each
    server logger then gets its own level so that per-server verbosity
    works correctly when multiple servers are mounted inside the gateway.

    Format is controlled by two ``config`` attributes:

    * ``format`` (``str``) — a standard Python ``%``-style logging format
      string, e.g. ``"%(asctime)s [%(name)s] %(levelname)s %(message)s"``.
      Passed directly to :class:`logging.Formatter`.  Omit ``%(asctime)s``
      from this string to suppress the timestamp column entirely.
    * ``timestamp_format`` (``str``, default ``"%Y-%m-%d %H:%M:%S"``) —
      :mod:`time`-compatible ``strftime`` format string for ``%(asctime)s``.

    If ``config.file`` is a non-empty string the server logger additionally
    writes to that file via a :class:`~logging.handlers.RotatingFileHandler`
    (10 MiB per file, 5 backups).  The directory is created automatically if it
    does not exist.

    Args:
        config:           An object with optional ``level``, ``format``,
                          ``timestamp_format``, and ``file`` attributes.
        mcp_server_name:  Name used for the :class:`logging.Logger` instance.

    Returns:
        A :class:`logging.Logger` scoped to *mcp_server_name*.
    """
    level_str = (getattr(config, "level", None) or "INFO") if config else "INFO"
    level = getattr(logging, str(level_str).upper(), logging.INFO)

    ts_format = (getattr(config, "timestamp_format", None) or _DEFAULT_TS_FORMAT) if config else _DEFAULT_TS_FORMAT

    from nxp.mcp.shared.config.models import _DEFAULT_FORMAT
    fmt_str = (getattr(config, "format", None) or "") if config else ""
    if not fmt_str:
        fmt_str = _DEFAULT_FORMAT

    formatter = _build_formatter(ts_format, fmt_str)

    # Configure the root logger once; subsequent calls are no-ops for basicConfig
    # but we still honour the per-server level via logger.setLevel().
    if not logging.root.handlers:
        logging.basicConfig(
            level=logging.DEBUG,
            format=_DEFAULT_FORMAT,
        )

    logger = logging.getLogger(mcp_server_name)
    logger.setLevel(level)

    # -----------------------------------------------------------------------
    # Optional file handler
    # -----------------------------------------------------------------------
    file_path = (getattr(config, "file", None) or "") if config else ""
    if file_path:
        # Avoid adding a duplicate handler if setup_logging is called again
        # for the same server (e.g. during tests).
        already_has_file_handler = any(
            isinstance(h, RotatingFileHandler)
            and getattr(h, "baseFilename", None) == os.path.abspath(file_path)
            for h in logger.handlers
        )
        if not already_has_file_handler:
            log_dir = os.path.dirname(os.path.abspath(file_path))
            os.makedirs(log_dir, exist_ok=True)
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=_FILE_MAX_BYTES,
                backupCount=_FILE_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger
