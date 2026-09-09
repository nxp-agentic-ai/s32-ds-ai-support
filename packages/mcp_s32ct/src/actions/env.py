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

"""``s32ct.env_*`` - read-only environment and installation probes.

These are the diagnostics to reach for first when a launcher-backed action
fails: they answer whether S32CT was found at all, which distribution and
version was selected, and what else is installed on the host. None of them
mutate anything.
"""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter

from nxp.mcp.s32ct.actions import _params as P
from nxp.mcp.s32ct.handlers import action_handlers


ENV_STATUS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.env_status",
        description=(
            "Smoke-test the active S32 Configuration Tools configuration. "
            "Returns the selected distribution ('desktop' for a standalone "
            "S32CT install, 'integrated_s32ds' for the variant bundled inside "
            "S32 Design Studio), the version, why that install was selected, "
            "and the resolved installation_path, launcher, launcher .ini, "
            "mcu_data_root and documentation_path - each with an _exists flag - "
            "plus the effective timeout. Run this first whenever another action "
            "fails with a launcher or path error, and to confirm the server "
            "configuration end-to-end before a real headless invocation."
        ),
        params=(),
        workflow_hints=(
            "An empty installation_path or launcher_exists=false means no "
            "install was resolved: set s32ct.settings.installation_path in the "
            "YAML, or install S32CT under a standard scan root.",
            "Use s32ct.env_installs to see every install available on the host.",
        ),
        related_actions=("s32ct.env_version", "s32ct.env_installs"),
        category="env",
    ),
    handler=action_handlers.env_status,
)


ENV_VERSION_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.env_version",
        description=(
            "Return the installed S32 Configuration Tools product name and "
            "version string, together with the install path and whether the "
            "launcher binary is present. Reads product metadata; it does not "
            "start the tool. Pass installation_path or s32ct_launcher to probe a "
            "specific install rather than the one selected at startup."
        ),
        params=(
            ActionParameter(
                name="installation_path",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Probe this installation directory instead of the one "
                        "selected at server startup."
                    ),
                },
            ),
            P.S32CT_LAUNCHER,
        ),
        workflow_hints=(
            "Use s32ct.env_status when you need the full configuration snapshot "
            "rather than just the version string.",
        ),
        related_actions=("s32ct.env_status", "s32ct.env_installs"),
        category="env",
    ),
    handler=action_handlers.env_version,
)


ENV_INSTALLS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.env_installs",
        description=(
            "List every S32 Configuration Tools installation discovered on this "
            "host, covering both the standalone desktop distribution and the "
            "variant bundled in S32 Design Studio, with each one's version, "
            "launcher path and MCU data root. Also reports which install the "
            "server selected at startup and why. Rescans the filesystem on every "
            "call, so it reflects what is installed right now; changing the "
            "selected install still requires a server restart."
        ),
        params=(),
        workflow_hints=(
            "Use this to discover a valid installation_path to pin in the YAML "
            "when auto-selection picked the wrong install.",
        ),
        related_actions=("s32ct.env_status", "s32ct.env_version"),
        category="env",
    ),
    handler=action_handlers.env_installs,
)


ENV_ACTIONS: tuple[ActionExecutable, ...] = (
    ENV_STATUS_ACTION,
    ENV_VERSION_ACTION,
    ENV_INSTALLS_ACTION,
)


__all__ = [
    "ENV_ACTIONS",
    "ENV_INSTALLS_ACTION",
    "ENV_STATUS_ACTION",
    "ENV_VERSION_ACTION",
]
