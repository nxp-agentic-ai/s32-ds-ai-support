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

"""``s32ct.validate`` - trustworthy pass/fail verdict for a ``.mex``."""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter

from nxp.mcp.s32ct.actions import _params as P
from nxp.mcp.s32ct.handlers.action_handlers import validate


VALIDATE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.validate",
        description=(
            "Validate an S32 Configuration Tools .mex against its Problems "
            "View and return a trustworthy pass/fail verdict. This is the only "
            "reliable way to know whether a configuration is correct: the "
            "launcher always exits 0 even when the Problems View contains "
            "SEVERE errors, so this action parses the full stderr, strips the "
            "documented framework noise, and buckets the surviving problems by "
            "the tool that owns them. By default every tool is validated in one "
            "chained launcher invocation (typically 3-7x faster than a per-tool "
            "loop); pass tool_name to validate just one. Set explain=true to "
            "attach a one-line fix hint to each problem, and diff_against=<older "
            ".mex> to report which problems an edit introduced versus resolved. "
            "Returns {valid, project_path, summary, tools, chain?, diff?}."
        ),
        params=(
            P.PROJECT_PATH_REQUIRED,
            ActionParameter(
                name="tool_name",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Validate only this tool. Omit to validate all 9, which "
                        "is the recommended default."
                    ),
                    "enum": list(P.TOOL_NAMES),
                },
            ),
            ActionParameter(
                name="explain",
                required=False,
                schema={
                    "type": "boolean",
                    "description": (
                        "Attach a short fix hint to each surviving problem, "
                        "mapped from the known S32CT error decision tree."
                    ),
                    "default": False,
                },
            ),
            ActionParameter(
                name="diff_against",
                required=False,
                schema={
                    "type": "string",
                    "description": (
                        "Path to an earlier .mex to validate as well, so the "
                        "response reports the per-tool delta of new versus "
                        "resolved problems. Use it to prove an edit introduced "
                        "no regressions."
                    ),
                },
            ),
            ActionParameter(
                name="chain",
                required=False,
                schema={
                    "type": "boolean",
                    "description": (
                        "Validate every tool in one launcher invocation. Leave "
                        "true unless you need the legacy per-tool loop."
                    ),
                    "default": True,
                },
            ),
            ActionParameter(
                name="stop_on_first_failure",
                required=False,
                schema={
                    "type": "boolean",
                    "description": (
                        "Stop at the first failing tool. Forces the slower "
                        "per-tool loop, since a chained run always executes "
                        "every segment."
                    ),
                    "default": False,
                },
            ),
            ActionParameter(
                name="include_unsupported_tool_problems",
                required=False,
                schema={
                    "type": "boolean",
                    "description": (
                        "Keep 'The tool does not support the selected "
                        "processor.' problems, which are otherwise filtered out "
                        "as expected noise for tools the MCU does not have."
                    ),
                    "default": False,
                },
            ),
            P.SDK_VERSION,
            P.S32CT_LAUNCHER,
            P.LAUNCHER_INI,
            P.TIMEOUT_S,
        ),
        preconditions=(
            "project_path must be an existing .mex file.",
            "An S32 Configuration Tools installation must be resolvable; check "
            "with s32ct.env_status.",
        ),
        workflow_hints=(
            "Run after every configure or splice, and always before "
            "s32ct.generate_code.",
            "When problems mention 'The value is not available', run "
            "s32ct.sanitize and re-validate - the cause is usually a dangling "
            "cross-reference rather than a real misconfiguration.",
            "Use s32ct.inspect_xrefs to locate the offending reference.",
        ),
        related_actions=(
            "s32ct.sanitize",
            "s32ct.generate_code",
            "s32ct.inspect_xrefs",
        ),
        category="validate",
    ),
    handler=validate,
)


__all__ = ["VALIDATE_ACTION"]
