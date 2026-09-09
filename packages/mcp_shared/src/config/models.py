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

from dataclasses import dataclass, field

# Default Python logging format string used when the user does not supply one.
# Users may override this with any valid % -style logging format string, e.g.:
#   format: "%(asctime)s %(levelname)s %(message)s"
_DEFAULT_FORMAT: str = "%(asctime)s [%(name)s] %(levelname)s %(message)s"


@dataclass(slots=True)
class LoggingSettings:
    level: str = "INFO"
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"
    format: str = _DEFAULT_FORMAT
    file: str = ""          # absolute or relative path; empty string = no file output


@dataclass(slots=True)
class BaseMcpServerConfig:
    """Shared base for all MCP server configs.

    Subclasses add a server-specific ``settings`` field::

        @dataclass(slots=True)
        class DemoMcpServerConfig(BaseMcpServerConfig):
            settings: DemoSettings = field(default_factory=DemoSettings)

    The optional ``skills`` field points to a directory containing skill
    definitions (SKILL.md files).  When set, the server will register a
    ``SkillsDirectoryProvider`` so the skills are exposed as MCP resources.
    An empty string (the default) means no skills provider is registered.

    The ``namespace`` field is a template string controlling the prefix
    prepended to all tool, resource, and prompt names registered by this
    server.  The placeholder ``{server_name}`` is substituted at runtime
    with each server's own ``MCP_SERVER_NAME`` constant.
    """

    logging: LoggingSettings = field(default_factory=LoggingSettings)
    skills: str = ""                       # path to skills directory; empty string = disabled
    namespace: str = "nxp_{server_name}"   # template; {server_name} resolved per-server
