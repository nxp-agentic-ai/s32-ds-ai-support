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

"""``validate`` - configuration validation gate for a ``.mex`` project.

Exposed to agents as the ``s32ct.validate`` action; :func:`validate_impl` is
the entry point the action handler calls.

Runs S32 Configuration Tools in headless mode with ``-ShowProblems`` for one or
more of its 9 tools (Pins, Clocks, Peripherals, DCD, IVT, eFUSE, GTM, QuadSPI,
FFC) and reports whether the configuration is valid.

Why a dedicated action rather than reusing the cli action with
``validate=true``:

``toolsc.exe`` **always exits 0** even when its Problems View contains
``SEVERE`` errors. Trusting the exit code (or the truncated ``stderr_tail``
that ``cli`` returns) misses real validation failures. The only honest
signal is to parse the *full* stderr text and count ``SEVERE: [TOOL]`` /
``SEVERE: [Generation`` lines **after** stripping the well-known framework
noise patterns documented in the ``s32ct-pins-author-mex`` and
``s32ct-peripherals-author-mex`` skills.

This tool encodes that 4-step procedure once, so every other agent gets the
correct answer without having to re-implement the filter.

Returned shape (per tool requested, plus an aggregate verdict at the top
level)::
    {
      "valid": bool,                    # True iff every requested tool passed
      "project_path": "...",            # absolute path of the validated .mex
      "tools": [
        {
          "tool": "Peripherals",
          "valid": true,
          "exit_code": 0,               # FYI only - not the truth signal
          "stderr_lines_total": 181,
          "stderr_lines_severe": 2,     # after step-2 [TOOL]/[Generation] filter
          "real_problems_count": 0,     # after step-3 noise filter
          "real_problems": [],          # verbatim lines that survived
          "command": "<rendered cmd>",  # for debug / reproducibility
          "duration_s": 14.3,
          "noise_filtered": 2           # how many lines were dropped as noise
        },
        ...
      ]
    }
"""
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Literal, Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME
from nxp.mcp.s32ct.tools.launcher import (
    ALLOWED_TOOLS,
    S32CTContext,
    _build_prefix,
    _resolve_launcher,
    _run,
)

_logger = logging.getLogger(MCP_SERVER_NAME)


# ---------------------------------------------------------------------------
# Stderr-noise filter
# ---------------------------------------------------------------------------
# Patterns that *always* surface even on a known-good ``.mex``. They originate
# in the Eclipse framework / SerDes Config Tool / RTD MEM driver expression
# evaluator and are not real configuration problems.
#
# The reasoning behind each pattern is documented at length in
# ``skills/s32ct/s32ct-pins-author-mex/SKILL.md`` (step 7
# "Validate via headless CLI"). When new noise sources appear in future S32CT
# releases, extend this list - keep it ordered alphabetically by pattern so
# diffs are reviewable.
_NOISE_PATTERNS: tuple[str, ...] = (
    r"Cannot get container for IPath",
    r"No script file found while trying to recompile the codegeneration script for SerDes Config Tool",
    # The MEM/INFLS feature-expression parser logs a misleading parse error
    # for every project that doesn't use the corresponding feature flag.
    r"Error in expression parsing\. Missing right bracket '\)' .* in expression: \(featureDefined\(`FEATURE_",
    r"Problem occurred during invocation of function derefAsr",
    # Pins/Peripherals JS evaluator noise - fires on any project that has
    # at least one PortPin configured, even when the value is valid.
    r"Port_GetNumOfPinConfig",
    r"getTotalNumOfChans",
    r"getTotalNumOfGroups",
    r"getChildById",
    # Peripherals Siul2_Port shadow noise - surfaces when a Pins-only project
    # is loaded under -HeadlessTool Peripherals because the Peripherals tool
    # tries to apply default values to Pins-side rows.
    r'\[DATA\] \[Siul2_Port\] Trying to apply item defaults or quick selection on setting with id ".*PortPinPcr"',
)

_NOISE_RE = re.compile("|".join(_NOISE_PATTERNS))


# ---------------------------------------------------------------------------
# Structured "Problems view" line parser (used by the chained-call fast path)
# ---------------------------------------------------------------------------
#
# When multiple ``-HeadlessTool <T> -Enable -ShowProblems`` segments are
# chained into a single launcher invocation, the validation engine re-emits
# *all* accumulated problems after each segment. Every entry comes out as a
# structured line of the form::
#
#     SEVERE: From Problems view: Tool problem issue: "<MESSAGE>",
#         origin: <ORIGIN>, target: <TARGET>, resource: <RESOURCE>
#
# This is strictly richer than the ``[TOOL]`` / ``[Generation`` lines the
# per-tool path relies on:
#   * ``target`` tells us exactly which tool's Problems View owns the entry
#     (perfect bucket key - no banner-scanning needed);
#   * ``origin`` carries the producing tool and (optionally) the functional
#     group as ``Tool:Group``;
#   * ``resource`` identifies the offending instance / pin / etc.
#
# The same ``(target, origin, resource, message)`` tuple is repeated across
# segments, so de-duplication on that tuple is mandatory.
_PROBLEMS_VIEW_RE = re.compile(
    r'^SEVERE:\s+From Problems view:\s+Tool problem issue:\s+'
    r'"(?P<message>.*?)",\s+'
    r'origin:\s+(?P<origin>[^,]*?),\s+'
    r'target:\s+(?P<target>[^,]*?),\s+'
    r'resource:\s*(?P<resource>.*?)\s*$'
)

# Problems with this message text mean "the requested tool simply isn't
# applicable to the selected MCU" (e.g. DCD/IVT/eFUSE/GTM/QuadSPI on an
# S32K3 part). The per-tool ``-Enable -ShowProblems`` path doesn't surface
# them at all because the tool just exits cleanly; the chained path does.
# To preserve behavior parity with the per-tool path by default, we filter
# them out unless the caller explicitly opts in via
# ``include_unsupported_tool_problems=True``.
_UNSUPPORTED_TOOL_MSG = "The tool does not support the selected processor."

# Problems-view entries with this message text are always a *cascade* of an
# upstream tool problem (the real root-cause entry is already emitted by the
# offending tool; this one is just the codegen pipeline reporting that it
# couldn't produce sources because the upstream model is invalid). It carries
# no diagnostic value on its own and would mask the count signal, so it is
# filtered unconditionally - there is no opt-in to surface it.
_CASCADE_CODEGEN_MSG = "Code generation failed."


def _parse_problems_view(stderr_text: str) -> list[dict]:
    """Parse all ``SEVERE: From Problems view: ...`` lines from a chained run.

    Returns a list of de-duplicated records, one per unique problem. Each
    record has the shape::
        {
          "message":  "<problem text>",
          "origin":   "<Tool[:FunctionalGroup]>",
          "tool":     "<Tool>",       # origin split on ':'
          "group":    "<Group>"|None, # origin split on ':'
          "target":   "<Tool>",       # bucket key
          "resource": "<Resource>",   # may be ""
          "raw":      "<verbatim line>",
        }

    De-duplication uses the tuple ``(target, origin, resource, message)``
    because the validation engine re-emits every accumulated problem after
    each ``-HeadlessTool`` segment in a chained call.
    """
    seen: set[tuple[str, str, str, str]] = set()
    records: list[dict] = []
    for line in stderr_text.splitlines():
        m = _PROBLEMS_VIEW_RE.match(line)
        if not m:
            continue
        message = m.group("message")
        origin = m.group("origin")
        target = m.group("target")
        resource = m.group("resource")
        key = (target, origin, resource, message)
        if key in seen:
            continue
        seen.add(key)
        if ":" in origin:
            tool, group = origin.split(":", 1)
        else:
            tool, group = origin, None
        records.append(
            {
                "message": message,
                "origin": origin,
                "tool": tool,
                "group": group,
                "target": target,
                "resource": resource,
                "raw": line,
            }
        )
    return records


# ---------------------------------------------------------------------------
# Problem-to-fix hints (mirrors s32ct-peripherals-graft-mex/references/error-decision-tree.md)
# ---------------------------------------------------------------------------
#
# Each entry: (pattern_regex, short_fix_hint). The hint is meant to be a
# one-liner that points at the right sibling skill / tool. Keep concise - the
# decision-tree reference file holds the long-form explanation.
#
# When a problem matches multiple patterns, we append all matching hints so
# the consumer gets the union of advice rather than just the first match.

_PROBLEM_HINTS: tuple[tuple[str, str], ...] = (
    (
        r"The value is not available",
        "Likely cause: clock-ref path into a non-existent McuClockReferencePoint, "
        "or cross-ref into an absent driver (commonly /Mcl/...). "
        "Run `sanitize_mex` to redirect Mcu refs and self-close Mcl arrays, "
        "then re-validate.",
    ),
    (
        r"OPWFMB mode is not available for selected channel",
        "Pwm: the chosen eMIOS channel doesn't support OPWFMB. "
        "Switch to a channel that supports it (CH_0..CH_7 on eMIOS_0 are safest), "
        "or change EmiosChMode. Mode-vs-channel masks live in RTD/Pwm.xml "
        "(EmiosPwmModesMappingInst_0 / _1).",
    ),
    (
        r"Counter bus in internal counter mode can be used only for OPWFMB mode and OPWFM mode",
        "Pwm: EMIOS_PWM_IP_BUS_INTERNAL is incompatible with the current "
        "EmiosChMode. Either switch the mode to OPWFMB/OPWFM, or pick a "
        "BUS_A/BUS_F counter bus (which then requires an Mcl EmiosCommon).",
    ),
    (
        r"configure a channel first by browsing in the EmiosCommon tab in MCL driver",
        "Pwm: a non-INTERNAL counter bus needs an Mcl EmiosCommon masterbus. "
        "Simplest fix: set EmiosChCounterBus=EMIOS_PWM_IP_BUS_INTERNAL and "
        "EmiosChMode=EMIOS_PWM_IP_MODE_OPWFMB.",
    ),
    (
        r"destination node referenced must be within",
        "Cross-ref points to a sibling with a duplicated name. Most common case: "
        "two CanController children both contain CanControllerBaudrateConfig_0. "
        "Rename per parent (e.g. CanControllerBaudrateConfig_0 under "
        "CanController_0, _1 under CanController_1) and update the refs.",
    ),
    (
        r"Adc Physical Channel ID must equal number after ChanNum",
        "Adc: AdcChannelId must equal the trailing integer of AdcChannelName. "
        "E.g. AdcChannelName='P1_ChanNum1' requires AdcChannelId=1.",
    ),
    (
        r"At least one HwFilter Need to be assigned per HW Object",
        "Can: every CanHardwareObject needs at least one CanHwFilter child. "
        "The example .mex carries one by default - check it survived the splice.",
    ),
    (
        r"Out of baudrate configuration for current controller",
        "Can: every CanController needs at least one CanControllerBaudrateConfig "
        "child. Lift the missing block from the RTD Can example.",
    ),
    (
        r"Hardware Channel must be unique across all CAN controllers",
        "Can: two CanController entries default to the same CanHwChannel. "
        "Set CanHwChannel explicitly per controller with distinct values "
        "(use `resource_lookup kind=enum_values driver=Can "
        "array_path=CanConfigSet.CanHwChannelList` to see legal values).",
    ),
    (
        r"Name must be a valid C identifier",
        "Some struct has Name=''. Most often a missing "
        "CommonPublishedInformation container, or a struct emitted with an "
        "empty Name. Compare the offending instance to its RTD example block.",
    ),
    (
        r"Duplicated\s+UartHwChannel|LPUART HW channel is being used by UART driver",
        "Two drivers claim the same LPUART. Each LPUART can be owned by exactly "
        "one driver - Uart OR Lin_43_LPUART_FLEXIO. Move one to a different "
        "instance.",
    ),
    (
        r"period .* > max 65534|PwmPeriodDefault",
        "Pwm: PwmPeriodDefault exceeds the uint16 ceiling. Set "
        "PwmPeriodInTicks=true and pick a value <= 65534.",
    ),
    (
        r"Group id must be unique among all Groups",
        "Adc: AdcGroupId is global across the driver, not per-HwUnit. Use a "
        "running counter (0,1,2,...) across every AdcGroup.",
    ),
)


def _explain_problem(line: str) -> list[str]:
    """Return zero or more fix hints for a real problem line."""
    hints: list[str] = []
    for pat, hint in _PROBLEM_HINTS:
        if re.search(pat, line):
            hints.append(hint)
    return hints


def _filter_stderr(stderr_text: str) -> tuple[int, int, list[str]]:
    """Apply the documented 3-step filter to a full stderr capture.

    Returns ``(total_line_count, severe_line_count, real_problem_lines)``.
    ``real_problem_lines`` is de-duplicated by message tail (the timestamp
    prefix is stripped before comparing).
    """
    lines = stderr_text.splitlines()

    # Step 2: keep only lines tagged as real-tool problems by S32CT itself.
    # ``[TOOL]`` is the Problems View; ``[Generation`` is the codegen path's
    # parallel reporter. Other categories ([DATA], [SYSTEM], [PLUGINS], ...) are
    # informational.
    candidates = [
        l for l in lines if "SEVERE: [TOOL]" in l or "SEVERE: [Generation" in l
    ]

    # Step 3: drop documented framework noise.
    real = [l for l in candidates if not _NOISE_RE.search(l)]

    # De-dup by message tail (timestamps differ across runs; messages don't).
    seen: set[str] = set()
    uniq: list[str] = []
    for l in real:
        key = _problem_key(l)
        if key not in seen:
            seen.add(key)
            uniq.append(l)

    return len(lines), len(candidates), uniq


# ---------------------------------------------------------------------------
# Per-tool validation invocation
# ---------------------------------------------------------------------------


def _validate_one(
    ctx: S32CTContext,
    launcher: Path,
    tools_ini: Path,
    distribution: str,
    project_path: Path,
    tool_name: str,
    sdk_version: Optional[str],
    timeout_s: int,
    explain: bool = False,
) -> dict:
    """Run ``-ShowProblems`` for one tool and apply the noise filter.

    The command shape mirrors ``generate_code_impl`` so that every
    tool in this package generates ``toolsc.exe`` invocations the same way.
    """
    cmd = _build_prefix(launcher, tools_ini, distribution)
    cmd += ["-Load", str(project_path)]
    if sdk_version:
        cmd += ["-SDKVersion", sdk_version]
    cmd += ["-HeadlessTool", tool_name, "-Enable", "-ShowProblems"]

    started = time.monotonic()
    try:
        rc, _so, se = _run(cmd, timeout_s=timeout_s)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = -1
        timed_out = True
        raw = exc.stderr or b""
        se = raw.decode(errors="replace") if isinstance(raw, bytes) else (raw or "")
    duration_s = round(time.monotonic() - started, 2)

    total, severe, real = _filter_stderr(se)
    noise_filtered = severe - len(real)
    is_valid = (not timed_out) and len(real) == 0

    result: dict = {
        "tool": tool_name,
        "valid": is_valid,
        "exit_code": rc,
        "timed_out": timed_out,
        "stderr_lines_total": total,
        "stderr_lines_severe": severe,
        "noise_filtered": noise_filtered,
        "real_problems_count": len(real),
        "real_problems": real,
        "duration_s": duration_s,
        "command": " ".join(f'"{c}"' if " " in c else c for c in cmd),
    }
    if explain:
        result["hints"] = [
            {"problem": p, "hints": _explain_problem(p)} for p in real
        ]
    return result


# ---------------------------------------------------------------------------
# Chained validation invocation (fast path)
# ---------------------------------------------------------------------------


def _render_problem_line(rec: dict) -> str:
    """Render a parsed Problems-view record to a stable, comparable line.

    The chained path returns *normalized* problem text (no per-run timestamp
    prefix), so the rendered line is directly usable as a stable dedup / diff
    key. The format mirrors the launcher's own ``From Problems view``
    template so operators recognize it instantly.
    """
    return (
        f'From Problems view: "{rec["message"]}", '
        f'origin: {rec["origin"]}, target: {rec["target"]}, '
        f'resource: {rec["resource"]}'
    )


def _validate_chain(
    ctx: S32CTContext,
    launcher: Path,
    tools_ini: Path,
    distribution: str,
    project_path: Path,
    tools: list[str],
    sdk_version: Optional[str],
    timeout_s: int,
    explain: bool = False,
    include_unsupported_tool_problems: bool = False,
) -> tuple[list[dict], dict]:
    """Validate every tool in ``tools`` using a *single* chained launcher call.

    The launcher accepts an unlimited number of ``-HeadlessTool <T> ...``
    segments after one shared ``-Load``. We exploit that to pay the launcher
    cold-start cost exactly once - replacing N processes with 1 typically
    cuts wall-clock time by 3-7x on a full 9-tool validation.

    Returns ``(per_tool_results, chain_meta)`` where ``per_tool_results``
    has the same shape as ``_validate_one`` returns (one entry per requested
    tool) and ``chain_meta`` describes the single underlying process.
    """
    cmd = _build_prefix(launcher, tools_ini, distribution)
    cmd += ["-Load", str(project_path)]
    if sdk_version:
        cmd += ["-SDKVersion", sdk_version]
    for t in tools:
        cmd += ["-HeadlessTool", t, "-Enable", "-ShowProblems"]

    rendered_cmd = " ".join(f'"{c}"' if " " in c else c for c in cmd)

    # The chain shares one launcher startup, but the actual per-tool
    # validation still scales with N. Scale the timeout so a slow tool
    # doesn't blow the budget for the whole batch.
    chain_timeout = max(timeout_s, timeout_s * max(1, len(tools)) // 2)

    started = time.monotonic()
    try:
        rc, _so, se = _run(cmd, timeout_s=chain_timeout)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = -1
        timed_out = True
        raw = exc.stderr or b""
        se = raw.decode(errors="replace") if isinstance(raw, bytes) else (raw or "")
    duration_s = round(time.monotonic() - started, 2)

    total_lines = len(se.splitlines())
    records = _parse_problems_view(se)
    # Always drop the codegen cascade entry - it is never a root cause and
    # would double-count the upstream problem that produced it.
    records = [r for r in records if r["message"] != _CASCADE_CODEGEN_MSG]
    if not include_unsupported_tool_problems:
        records = [
            r for r in records if r["message"] != _UNSUPPORTED_TOOL_MSG
        ]

    # Bucket records by ``target`` - that is the tool whose Problems View
    # owns the entry. Tools requested in the chain but with zero matching
    # records => valid.
    per_tool: list[dict] = []
    for t in tools:
        bucket = [r for r in records if r["target"] == t]
        rendered = [_render_problem_line(r) for r in bucket]
        is_valid = (not timed_out) and len(bucket) == 0

        entry: dict = {
            "tool": t,
            "valid": is_valid,
            "exit_code": rc,
            "timed_out": timed_out,
            # In chained mode per-tool stderr line counts aren't meaningful
            # (one shared stream). Expose chain totals so downstream code
            # that reads these fields doesn't crash, and flag the source.
            "stderr_lines_total": total_lines,
            "stderr_lines_severe": len(records),
            "noise_filtered": 0,  # implicit - regex only matches real entries
            "real_problems_count": len(bucket),
            "real_problems": rendered,
            "duration_s": duration_s,
            "command": rendered_cmd,
            "source": "chain",
        }
        if explain:
            entry["hints"] = [
                {"problem": p, "hints": _explain_problem(p)} for p in rendered
            ]
        per_tool.append(entry)

    chain_meta = {
        "used": True,
        "process_count": 1,
        "duration_s": duration_s,
        "exit_code": rc,
        "timed_out": timed_out,
        "tools_in_chain": list(tools),
        "stderr_lines_total": total_lines,
        "problems_view_records": len(records),
        "include_unsupported_tool_problems": include_unsupported_tool_problems,
        "command": rendered_cmd,
    }
    return per_tool, chain_meta


# ---------------------------------------------------------------------------
# Public implementation entry point
# ---------------------------------------------------------------------------


_DEFAULT_TOOLS: tuple[str, ...] = (
    # Order chosen to surface user-edited tools first (Pins/Peripherals/Clocks
    # carry the bulk of authored content) so a partial-failure report fails
    # fast on what the user most likely touched.
    "Pins",
    "Peripherals",
    "Clocks",
    "DCD",
    "IVT",
    "eFUSE",
    "GTM",
    "QuadSPI",
    "FFC",
)

def _problem_key(line: str) -> str:
    """Strip timestamp prefix for stable deduplication across runs."""
    return line[line.find("SEVERE:"):] if "SEVERE:" in line else line


def validate_impl(
    ctx: S32CTContext,
    project_path: str,
    tool_name: Optional[
        Literal[
            "Pins", "Clocks", "Peripherals", "DCD", "IVT",
            "eFUSE", "GTM", "QuadSPI", "FFC",
        ]
    ] = None,
    sdk_version: Optional[str] = None,
    s32ct_launcher: Optional[str] = None,
    launcher_ini: Optional[str] = None,
    timeout_s: Optional[int] = None,
    stop_on_first_failure: bool = False,
    explain: bool = False,
    diff_against: Optional[str] = None,
    chain: bool = True,
    include_unsupported_tool_problems: bool = False,
) -> dict:
    """Validate a ``.mex`` against the S32CT Problems View.

    This is the implementation behind the ``s32ct.validate`` action. It was
    previously the body of a ``@server.tool``-decorated closure; the server /
    config pair is now an explicit ``ctx`` supplied by the action handler, so
    the same logic is reachable from the action catalog and directly unit
    testable.
    """
    proj = Path(project_path)
    if not proj.exists() or proj.suffix.lower() != ".mex":
        return {
            "valid": False,
            "project_path": str(proj),
            "error": f"project_path must be an existing .mex file. Got: {proj}",
            "tools": [],
        }

    if tool_name is not None and tool_name not in ALLOWED_TOOLS:
        return {
            "valid": False,
            "project_path": str(proj),
            "error": (
                f"Invalid tool_name '{tool_name}'. "
                f"Allowed: {sorted(ALLOWED_TOOLS)}"
            ),
            "tools": [],
        }

    try:
        launcher, tools_ini, distribution = _resolve_launcher(
            ctx, s32ct_launcher, launcher_ini
        )
    except FileNotFoundError as e:
        return {
            "valid": False,
            "project_path": str(proj),
            "error": str(e),
            "tools": [],
        }

    effective_timeout = (
        int(timeout_s) if timeout_s is not None else ctx.timeout_s
    )

    targets: list[str] = (
        [tool_name] if tool_name is not None else list(_DEFAULT_TOOLS)
    )

    # Dispatch: chained call (one process, N -HeadlessTool segments)
    # vs. per-tool loop (N processes). Chaining is strictly faster
    # because the launcher cold-start dominates each invocation.
    #
    # `stop_on_first_failure` is fundamentally incompatible with
    # chaining (the launcher runs every segment regardless), so it
    # forces the per-tool path. Same for `chain=False` callers.
    use_chain = chain and not stop_on_first_failure

    results: list[dict] = []
    chain_meta: Optional[dict] = None
    overall_valid = True

    if use_chain:
        _logger.info(
            "validate (chain): project=%s tools=%s", proj, ",".join(targets)
        )
        results, chain_meta = _validate_chain(
            ctx, launcher, tools_ini, distribution, proj, targets,
            sdk_version, effective_timeout, explain=explain,
            include_unsupported_tool_problems=include_unsupported_tool_problems,
        )
        overall_valid = all(r["valid"] for r in results)
    else:
        for t in targets:
            _logger.info("validate: project=%s tool=%s", proj, t)
            r = _validate_one(
                ctx, launcher, tools_ini, distribution, proj, t,
                sdk_version, effective_timeout, explain=explain,
            )
            results.append(r)
            if not r["valid"]:
                overall_valid = False
                if stop_on_first_failure:
                    break

    # Optional diff: validate a previous .mex with the same scope, then
    # compute per-tool delta sets so the caller can see "what got fixed"
    # vs. "what got introduced". Both files validated with the same tool
    # list, same sdk_version, same launcher - so the comparison is
    # apples-to-apples.
    diff_block: Optional[dict] = None
    if diff_against:
        prev = Path(diff_against)
        if not prev.exists() or prev.suffix.lower() != ".mex":
            diff_block = {
                "error": (
                    f"diff_against must be an existing .mex file. Got: {prev}"
                ),
            }
        else:
            tool_order = [r["tool"] for r in results]
            if use_chain:
                prev_results, _prev_chain_meta = _validate_chain(
                    ctx, launcher, tools_ini, distribution, prev, tool_order,
                    sdk_version, effective_timeout, explain=False,
                    include_unsupported_tool_problems=include_unsupported_tool_problems,
                )
            else:
                prev_results = []
                for t in tool_order:
                    pr = _validate_one(
                        ctx, launcher, tools_ini, distribution, prev, t, sdk_version,
                        effective_timeout, explain=False,
                    )
                    prev_results.append(pr)
            # Map tool -> set(problem_key) so timestamp differences don't
            # introduce false deltas. With chain results the problem lines
            # are already normalized (no timestamp prefix), so `_problem_key`
            # is a no-op for them - which is exactly what we want.

            per_tool_diff: list[dict] = []
            for cur, old in zip(results, prev_results):
                cur_keys = {_problem_key(l) for l in cur["real_problems"]}
                old_keys = {_problem_key(l) for l in old["real_problems"]}
                introduced = sorted(cur_keys - old_keys)
                resolved = sorted(old_keys - cur_keys)
                persisting = sorted(cur_keys & old_keys)
                per_tool_diff.append(
                    {
                        "tool": cur["tool"],
                        "previous_problem_count": len(old_keys),
                        "current_problem_count": len(cur_keys),
                        "delta": len(cur_keys) - len(old_keys),
                        "introduced": introduced,
                        "resolved": resolved,
                        "persisting": persisting,
                    }
                )
            diff_block = {
                "previous_path": str(prev),
                "per_tool": per_tool_diff,
                "total_introduced": sum(
                    len(d["introduced"]) for d in per_tool_diff
                ),
                "total_resolved": sum(
                    len(d["resolved"]) for d in per_tool_diff
                ),
            }

    # Short human-readable summary for log output / quick eyeballing.
    summary_parts = []
    for r in results:
        if r["timed_out"]:
            summary_parts.append(f"{r['tool']}=timeout")
        elif r["valid"]:
            summary_parts.append(f"{r['tool']}=PASS")
        else:
            summary_parts.append(f"{r['tool']}=FAIL({r['real_problems_count']})")
    summary = "; ".join(summary_parts)

    out: dict = {
        "valid": overall_valid,
        "project_path": str(proj),
        "summary": summary,
        "tools": results,
    }
    if chain_meta is not None:
        out["chain"] = chain_meta
    if diff_block is not None:
        out["diff"] = diff_block
    return out
