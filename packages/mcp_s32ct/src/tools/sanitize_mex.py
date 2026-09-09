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

"""``sanitize_mex`` - clean up cross-references in a freshly-spliced ``.mex``.

When a driver `<instance>` block is grafted from an RTD example .mex into a
project that has fewer pre-wired drivers, the grafted block typically carries
cross-references that resolve in the example's environment but not in the
target. The three families of dangling references we systematically see are:

  * ``/Mcu/Mcu/McuModuleConfiguration/<config>/<NAME>`` where ``<NAME>`` is
    something like ``LPUART_CLK``, ``AIPS_PLAT_CLK``, ``BOARD_BootClockRUN``
    that the template Mcu instance doesn't expose. Validation reports these
    as "value is not available".

  * ``/Mcl/Mcl/MclConfig/...`` for DMA channels, FlexIO logic channels, eMIOS
    common master buses, etc. - when no Mcl driver instance exists.

  * Singleton ``<setting name="Foo" value="/Driver/..."/>`` whose target
    driver is absent (most often ``UartHwChannelRef`` when ``UartHwUsing`` is
    LPUART_IP rather than FLEXIO_IP).

This module performs the same three sweeps that
``skills/s32ct/s32ct-peripherals-graft-mex/scripts/sanitize.py`` does, exposed
as the ``s32ct.sanitize`` action so it composes with ``s32ct.validate``, the
``s32ct.inspect_*`` actions, and ``s32ct.generate_code`` in a single workflow.
:func:`sanitize_mex_impl` is the entry point the action handler calls.


The transformation is **idempotent** - running it twice on the same .mex
produces the same output as running it once. It's safe to run as a
prophylactic step after any splice.

Returned shape::

    {
      "ok": true,
      "project_path": "C:\\...\\Project.mex",
      "output_path": "C:\\...\\Project_Sanitised.mex",
      "in_place": false,
      "stats": {
        "mcu_refs_redirected": 12,
        "mcl_arrays_emptied": 5,
        "singletons_blanked": 1
      },
      "samples": {
        "mcu_refs": ["LPUART_CLK", "AIPS_PLAT_CLK", ...],
        "mcl_arrays": ["SpiPhyTxDmaChannel", "UartDmaRxChannelRef", ...]
      },
      "size_before": 212063,
      "size_after":  211456
    }
"""
import logging
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from nxp.mcp.s32ct.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


# ---------------------------------------------------------------------------
# Canonical redirect target
# ---------------------------------------------------------------------------

DEFAULT_CLOCKREF = (
    "/Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/McuClockReferencePoint_0"
)

# Setting names whose *value* should be blanked when it points into an absent
# driver. Documented in
# ``skills/s32ct/s32ct-peripherals-graft-mex/references/cross-reference-map.md``.
SINGLETON_BLANK: tuple[tuple[str, str], ...] = (
    # (field_name, regex pattern in the value to trigger the blanking)
    ("UartHwChannelRef", r"/Mcl/"),
    # Add new fields here as they surface in future RTD releases.
)


# ---------------------------------------------------------------------------
# Nested-array helper (balanced)
# ---------------------------------------------------------------------------


def _find_all_balanced_arrays(text: str):
    """Yield ``(name, open_start, body_start, body_end, close_end)`` for every
    ``<array name="NAME">...</array>``, with correct nesting.

    Self-closing ``<array name="X"/>`` elements have no body and are skipped.
    """
    # First pass: find every opening tag in source order
    opens = [
        (m.start(), m.group(1))
        for m in re.finditer(r'<array name="([A-Za-z0-9_]+)">', text)
    ]
    # Second pass: for each opening, walk forward through array tokens with
    # depth accounting until we find the matching close.
    token_re = re.compile(r"<array\b[^>]*?(/?)>|</array>")
    for op_start, name in opens:
        body_start = op_start + len(f'<array name="{name}">')
        depth = 1
        for m in token_re.finditer(text, body_start):
            tok = m.group(0)
            if tok == "</array>":
                depth -= 1
                if depth == 0:
                    yield (name, op_start, body_start, m.start(), m.end())
                    break
            elif tok.endswith("/>"):
                continue
            else:
                depth += 1


# ---------------------------------------------------------------------------
# The three sweeps (pure functions for testability)
# ---------------------------------------------------------------------------


def sweep_mcu_refs(
    txt: str, canonical: str = DEFAULT_CLOCKREF
) -> tuple[str, int, list[str]]:
    """Redirect every ``/Mcu/Mcu/McuModuleConfiguration/...`` reference that
    doesn't already end in ``McuClockReferencePoint_0`` to the canonical
    target. Returns (new_text, count_redirected, sample_targets_seen).
    """
    count = 0
    samples: list[str] = []

    def repath(m: re.Match) -> str:
        nonlocal count
        full = m.group(0)
        # Already pointing at the canonical ref - leave alone.
        if "/McuClockReferencePoint_0" in full and full.endswith(
            'McuClockReferencePoint_0"'
        ):
            return full
        # Extract the original tail for the report
        path = re.search(r'value="([^"]+)"', full).group(1)
        leaf = path.rsplit("/", 1)[-1]
        if leaf not in samples and len(samples) < 25:
            samples.append(leaf)
        count += 1
        return f'value="{canonical}"'

    new_txt = re.sub(
        r'value="/Mcu/Mcu/McuModuleConfiguration/[^"]+"', repath, txt
    )
    return new_txt, count, samples


def sweep_mcl_arrays(txt: str) -> tuple[str, int, list[str]]:
    """Self-close every ``<array name="X">...</array>`` whose body contains a
    ``/Mcl/`` cross-reference. Returns (new_text, count_emptied, sample_names).
    """
    samples: list[str] = []
    # Collect targets first, then rewrite end->start so offsets stay valid.
    arrays = list(_find_all_balanced_arrays(txt))
    to_replace: list[tuple[int, int, str]] = []
    for name, op_start, body_start, body_end, close_end in arrays:
        if "/Mcl/" in txt[body_start:body_end]:
            to_replace.append((op_start, close_end, name))

    # Apply rewrites end -> start
    for op_start, close_end, name in sorted(to_replace, key=lambda t: -t[0]):
        txt = txt[:op_start] + f'<array name="{name}"/>' + txt[close_end:]
        if name not in samples and len(samples) < 25:
            samples.append(name)

    return txt, len(to_replace), samples


def sweep_singletons(txt: str) -> tuple[str, int, list[str]]:
    """Blank documented singleton ``*Ref`` fields whose value matches the
    associated dangling-reference pattern. Returns (new_text, count, sample_names).
    """
    count = 0
    samples: list[str] = []
    for field, value_pat in SINGLETON_BLANK:
        rx = re.compile(
            rf'<setting name="{re.escape(field)}" value="[^"]*?{value_pat}[^"]*"/>'
        )
        new_txt, n = rx.subn(f'<setting name="{field}" value=""/>', txt)
        if n:
            count += n
            if field not in samples:
                samples.append(field)
        txt = new_txt
    return txt, count, samples


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------


def sanitize_text(
    txt: str, canonical_clockref: str = DEFAULT_CLOCKREF
) -> tuple[str, dict, dict]:
    """Run all three sweeps. Returns (new_text, stats_dict, samples_dict)."""
    txt, n_mcu, sample_mcu = sweep_mcu_refs(txt, canonical_clockref)
    txt, n_arr, sample_arr = sweep_mcl_arrays(txt)
    txt, n_sing, sample_sing = sweep_singletons(txt)

    # XML well-formedness sanity check - sanitization should never break it.
    try:
        ET.fromstring(txt)
    except ET.ParseError as e:
        raise RuntimeError(f"Sanitization produced malformed XML: {e}") from e

    stats = {
        "mcu_refs_redirected": n_mcu,
        "mcl_arrays_emptied": n_arr,
        "singletons_blanked": n_sing,
    }
    samples = {
        "mcu_refs": sample_mcu,
        "mcl_arrays": sample_arr,
        "singletons": sample_sing,
    }
    return txt, stats, samples


# ---------------------------------------------------------------------------
# Public implementation entry point
# ---------------------------------------------------------------------------


def sanitize_mex_impl(
    project_path: str,
    output_path: Optional[str] = None,
    canonical_clockref: Optional[str] = None,
    overwrite: bool = False,
) -> dict:
    """Run the three sanitization sweeps over a ``.mex`` and write the result.

    This is the implementation behind the ``s32ct.sanitize`` action. Unlike the
    other S32CT actions it needs no ``S32CTContext``: the transformation is
    pure XML rewriting and never invokes the launcher.
    """
    proj = Path(project_path)
    if not proj.exists() or proj.suffix.lower() != ".mex":
        return {
            "ok": False,
            "project_path": str(proj),
            "error": f"project_path must be an existing .mex file. Got: {proj}",
        }

    out: Path = Path(output_path) if output_path else proj
    in_place = out == proj
    if (not in_place) and out.exists() and not overwrite:
        return {
            "ok": False,
            "project_path": str(proj),
            "error": (
                f"output_path exists: {out}. Pass overwrite=true to replace."
            ),
        }
    if out.suffix.lower() != ".mex":
        return {
            "ok": False,
            "project_path": str(proj),
            "error": f"output_path must have .mex extension. Got: {out}",
        }

    try:
        src_txt = proj.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "ok": False,
            "project_path": str(proj),
            "error": f"Failed to read project: {e}",
        }

    size_before = len(src_txt)
    canon = canonical_clockref or DEFAULT_CLOCKREF

    try:
        new_txt, stats, samples = sanitize_text(src_txt, canon)
    except Exception as e:
        _logger.exception("sanitize_text failed")
        return {
            "ok": False,
            "project_path": str(proj),
            "error": f"{type(e).__name__}: {e}",
        }

    # Also try to carry along ClockConfigurationMappings.txt if it lives
    # alongside the source - same convention the build_mex.py script uses.
    sidecar_copied: Optional[str] = None
    sidecar_src = proj.parent / "ClockConfigurationMappings.txt"
    if (not in_place) and sidecar_src.exists():
        sidecar_dst = out.parent / "ClockConfigurationMappings.txt"
        try:
            if (not sidecar_dst.exists()) or overwrite:
                shutil.copyfile(sidecar_src, sidecar_dst)
                sidecar_copied = str(sidecar_dst)
        except Exception as e:
            _logger.warning("could not copy sidecar: %s", e)

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(new_txt, encoding="utf-8", newline="\n")
    except Exception as e:
        return {
            "ok": False,
            "project_path": str(proj),
            "output_path": str(out),
            "error": f"Failed to write output: {e}",
        }

    return {
        "ok": True,
        "project_path": str(proj),
        "output_path": str(out),
        "in_place": in_place,
        "stats": stats,
        "samples": samples,
        "size_before": size_before,
        "size_after": len(new_txt),
        "sidecar_copied": sidecar_copied,
    }


