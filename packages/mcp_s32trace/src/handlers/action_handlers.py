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

from dataclasses import dataclass
from typing import Any

from nxp.mcp.shared.action import ActionExecutionError

from nxp.mcp.s32trace.impl.analysis import (
    TRACE_SESSION_CACHE,
    TraceDataset,
    query_summary,
    query_find_event,
    query_address_at,
    query_time_between,
    query_range_events,
    query_get_source,
)
from nxp.mcp.s32trace.impl.common.elf_index import ElfIndex
from nxp.mcp.s32trace.impl.common.source_index import SourceIndex
from nxp.mcp.s32trace.impl.common.source_snippet import SourceSnippet
from nxp.mcp.s32trace.impl.timeline import (
    TIMELINE_SESSION_CACHE,
    TimelineDataset,
    query_timeline_summary,
    query_timeline_hotspots,
    query_timeline_function,
    query_timeline_source,
    query_timeline_window,
    query_timeline_call_sequence,
)
from nxp.mcp.s32trace.impl.coverage import (
    COVERAGE_SESSION_CACHE,
    CoverageDataset,
    query_coverage_summary,
    query_coverage_function,
    query_coverage_file,
    query_coverage_uncovered,
    query_coverage_hotspots,
    query_coverage_get_source,
)
from nxp.mcp.s32trace.impl.performance import (
    PERFORMANCE_SESSION_CACHE,
    PerformanceDataset,
    query_performance_summary,
    query_performance_hotspots,
    query_performance_function,
    query_performance_callgraph,
    query_performance_get_source,
)

from nxp.mcp.s32trace.impl.configurator import (
    list_templates,
    inspect_template,
    describe_trace_flow as _describe_trace_flow,
    create_from_template as _create_from_template,
    set_output_folder as _set_output_folder,
    set_target_access as _set_target_access,
    set_timestamp_generator as _set_timestamp_generator,
    configure_data_streams as _configure_data_streams,
    configure_sink as _configure_sink,
    configure_core as _configure_core,
    configure_soc_module as _configure_soc_module,
)

_HANDLER_ERROR_CODE = -32002


@dataclass(frozen=True)
class S32TraceSessionManager:
    """Minimal session context for S32Trace handlers.

    Carries the S32DS installation path that was resolved at server startup.
    Handlers that need the path call ``effective_installation_path`` and raise
    ``ActionExecutionError`` when neither the per-call param nor the startup
    path is available.
    """

    installation_path: str | None


def _require_session_manager(session_manager: S32TraceSessionManager | None) -> S32TraceSessionManager:
    if session_manager is None:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "MISSING_CONTEXT",
            error_details={"message": "Missing session manager."},
        )
    return session_manager


def _resolve_installation_path(params: dict[str, Any], session_manager: S32TraceSessionManager) -> str:
    """Return the installation path from params override or session default.

    Raises ``ActionExecutionError`` when no path is available from either source.
    """
    path: str | None = params.get("s32ds_installation_path") or session_manager.installation_path
    if not path:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={
                "message": (
                    "No S32DS installation path available. "
                    "Either pass 's32ds_installation_path' as a parameter or set "
                    "'installation_path' in configs/s32trace.standalone.yaml."
                ),
            },
        )
    return path


# ---------------------------------------------------------------------------
# Read-only / discovery handlers
# ---------------------------------------------------------------------------

async def list_configurator_templates(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    sm = _require_session_manager(session_manager)
    path = _resolve_installation_path(params, sm)
    try:
        templates = list_templates(path)
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    return {"count": len(templates), "templates": templates}


async def inspect_configurator_template(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        schema = inspect_template(params["template_path"])
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    return {"schema": schema}


async def describe_trace_flow(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        return _describe_trace_flow(params["config_path"])
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


# ---------------------------------------------------------------------------
# Config creation handler
# ---------------------------------------------------------------------------

async def create_from_template(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        return _create_from_template(
            template_path=params["template_path"],
            output_path=params.get("output_path"),
        )
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


# ---------------------------------------------------------------------------
# Config editing handlers
# ---------------------------------------------------------------------------

async def set_output_folder(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        return _set_output_folder(
            config_path=params["config_path"],
            output_folder=params["output_folder"],
        )
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def set_target_access(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        return _set_target_access(
            config_path=params["config_path"],
            settings=params["settings"],
        )
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def set_timestamp_generator(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        return _set_timestamp_generator(
            config_path=params["config_path"],
            enabled=params["enabled"],
            module_base_address=params.get("module_base_address"),
            counter_base_frequency=params.get("counter_base_frequency"),
            halt_on_debug=params.get("halt_on_debug"),
            mem_space=params.get("mem_space"),
        )
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def configure_data_streams(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        return _configure_data_streams(
            config_path=params["config_path"],
            trace_location=params["trace_location"],
            continuous_collection=params.get("continuous_collection"),
        )
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def configure_sink(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        return _configure_sink(
            config_path=params["config_path"],
            sink_name=params["sink_name"],
            settings=params["settings"],
        )
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def configure_core(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        return _configure_core(
            config_path=params["config_path"],
            core_name=params["core_name"],
            settings=params["settings"],
        )
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def configure_soc_module(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        return _configure_soc_module(
            config_path=params["config_path"],
            module_name=params["module_name"],
            settings=params["settings"],
        )
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


# ---------------------------------------------------------------------------
# Analysis handlers
# ---------------------------------------------------------------------------

async def analysis_load_trace(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        trace_id = TRACE_SESSION_CACHE.new_id()
        ds = TraceDataset.load(
            trace_id=trace_id,
            csv_path=params["csv_path"],
            elf_path=params["elf_path"],
            source_root=params.get("source_root"),
            extra_source_roots=params.get("extra_source_roots") or [],
            label=params.get("label"),
            time_unit_ns=params.get("time_unit_ns"),
            snippet_window=params.get("snippet_window", 3),
        )
        TRACE_SESSION_CACHE.put(ds)
        return ds.to_load_summary()
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def analysis_summary(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TRACE_SESSION_CACHE.get(params["trace_id"])
        return query_summary(ds, top_n=params.get("top_n", 10))
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def analysis_find_event(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TRACE_SESSION_CACHE.get(params["trace_id"])
        return query_find_event(
            ds,
            selector=params["selector"],
            limit=params.get("limit", 100),
            include_source=params.get("include_source", True),
            include_details=params.get("include_details", False),
            snippet_window=params.get("snippet_window"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def analysis_address_at(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        trace_id = params.get("trace_id")
        elf_path = params.get("elf_path")

        ds: TraceDataset | None = None
        standalone_elf: ElfIndex | None = None
        standalone_src: SourceIndex | None = None
        standalone_snip: SourceSnippet | None = None

        if trace_id:
            ds = TRACE_SESSION_CACHE.get(trace_id)
        elif elf_path:
            standalone_elf = ElfIndex.from_file(elf_path)
            standalone_snip = SourceSnippet()
        else:
            raise ValueError("Provide 'trace_id' or 'elf_path'.")

        return query_address_at(
            ds,
            pc=params.get("pc"),
            symbol=params.get("symbol"),
            elf_index=standalone_elf,
            src_index=standalone_src,
            snippets=standalone_snip,
            snippet_window=params.get("snippet_window"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def analysis_time_between(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TRACE_SESSION_CACHE.get(params["trace_id"])
        return query_time_between(
            ds,
            from_selector=params["from_selector"],
            to_selector=params["to_selector"],
            occurrence=params.get("occurrence", "first"),
            max_intermediate_symbols=params.get("max_intermediate_symbols", 10),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def analysis_range_events(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TRACE_SESSION_CACHE.get(params["trace_id"])
        return query_range_events(
            ds,
            time_range=params.get("time_range"),
            from_selector=params.get("from_selector"),
            to_selector=params.get("to_selector"),
            include_raw_rows=params.get("include_raw_rows", False),
            limit=params.get("limit", 100),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def analysis_get_source(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TRACE_SESSION_CACHE.get(params["trace_id"])
        return query_get_source(
            ds,
            file_hint=params.get("file_hint"),
            line=params.get("line"),
            symbol=params.get("symbol"),
            snippet_window=params.get("snippet_window"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


# ---------------------------------------------------------------------------
# Timeline handlers
# ---------------------------------------------------------------------------

async def timeline_load(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        session_id = TIMELINE_SESSION_CACHE.new_id()
        ds = TimelineDataset.load(
            session_id=session_id,
            timeline_path=params["timeline_path"],
            elf_path=params.get("elf_path"),
            source_root=params.get("source_root"),
            extra_source_roots=params.get("extra_source_roots") or [],
            label=params.get("label"),
            snippet_window=params.get("snippet_window", 5),
        )
        TIMELINE_SESSION_CACHE.put(ds)
        return ds.to_load_summary()
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def timeline_summary(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TIMELINE_SESSION_CACHE.get(params["session_id"])
        return query_timeline_summary(
            ds,
            source_name=params.get("source_name"),
            top_k=params.get("top_k", 10),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def timeline_hotspots(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TIMELINE_SESSION_CACHE.get(params["session_id"])
        return query_timeline_hotspots(
            ds,
            source_name=params.get("source_name"),
            sort_by=params.get("sort_by", "samples"),
            top_k=params.get("top_k", 10),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def timeline_function(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TIMELINE_SESSION_CACHE.get(params["session_id"])
        return query_timeline_function(
            ds,
            name=params["name"],
            source_name=params.get("source_name"),
            include_source=params.get("include_source", True),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def timeline_window(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TIMELINE_SESSION_CACHE.get(params["session_id"])
        return query_timeline_window(
            ds,
            start_tick=params.get("start_tick"),
            end_tick=params.get("end_tick"),
            source_name=params.get("source_name"),
            top_k=params.get("top_k", 20),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def timeline_sequence(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TIMELINE_SESSION_CACHE.get(params["session_id"])
        return query_timeline_call_sequence(
            ds,
            source_name=params.get("source_name"),
            limit=params.get("limit", 100),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def timeline_source(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = TIMELINE_SESSION_CACHE.get(params["session_id"])
        return query_timeline_source(
            ds,
            symbol=params.get("symbol"),
            file_hint=params.get("file_hint"),
            line=params.get("line"),
            source_name=params.get("source_name"),
            snippet_window=params.get("snippet_window"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


# ---------------------------------------------------------------------------
# Coverage handlers
# ---------------------------------------------------------------------------

async def coverage_load(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        session_id = COVERAGE_SESSION_CACHE.new_id()
        ds = CoverageDataset.load(
            session_id=session_id,
            flatprofiler_path=params["flatprofiler_path"],
            elf_path=params["elf_path"],
            source_root=params["source_root"],
            extra_source_roots=params.get("extra_source_roots") or [],
            label=params.get("label"),
            snippet_window=params.get("snippet_window", 5),
        )
        COVERAGE_SESSION_CACHE.put(ds)
        return ds.to_load_summary()
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def coverage_summary(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = COVERAGE_SESSION_CACHE.get(params["session_id"])
        return query_coverage_summary(
            ds,
            core=params.get("core"),
            top_k=params.get("top_k", 10),
            include_no_source_info=params.get("include_no_source_info", False),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def coverage_function(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = COVERAGE_SESSION_CACHE.get(params["session_id"])
        return query_coverage_function(
            ds,
            name=params["name"],
            core=params.get("core"),
            include_source_rows=params.get("include_source_rows", True),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def coverage_file(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = COVERAGE_SESSION_CACHE.get(params["session_id"])
        return query_coverage_file(
            ds,
            file_hint=params["file_hint"],
            core=params.get("core"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def coverage_uncovered(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = COVERAGE_SESSION_CACHE.get(params["session_id"])
        return query_coverage_uncovered(
            ds,
            granularity=params.get("granularity", "function"),
            sort_by=params.get("sort_by", "size"),
            top_k=params.get("top_k", 20),
            core=params.get("core"),
            include_no_source_info=params.get("include_no_source_info", False),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def coverage_hotspots(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = COVERAGE_SESSION_CACHE.get(params["session_id"])
        return query_coverage_hotspots(
            ds,
            sort_by=params.get("sort_by", "time"),
            granularity=params.get("granularity", "function"),
            top_k=params.get("top_k", 10),
            core=params.get("core"),
            include_no_source_info=params.get("include_no_source_info", False),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def coverage_get_source(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = COVERAGE_SESSION_CACHE.get(params["session_id"])
        return query_coverage_get_source(
            ds,
            symbol=params.get("symbol"),
            file_hint=params.get("file_hint"),
            line=params.get("line"),
            core=params.get("core"),
            snippet_window=params.get("snippet_window"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


# ---------------------------------------------------------------------------
# Performance handlers
# ---------------------------------------------------------------------------

async def performance_load(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        session_id = PERFORMANCE_SESSION_CACHE.new_id()
        ds = PerformanceDataset.load(
            session_id=session_id,
            perf_path=params["perf_path"],
            elf_path=params.get("elf_path"),
            source_root=params.get("source_root"),
            extra_source_roots=params.get("extra_source_roots") or [],
            label=params.get("label"),
            snippet_window=params.get("snippet_window", 5),
        )
        PERFORMANCE_SESSION_CACHE.put(ds)
        return ds.to_load_summary()
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def performance_summary(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = PERFORMANCE_SESSION_CACHE.get(params["session_id"])
        return query_performance_summary(
            ds,
            core=params.get("core"),
            top_k=params.get("top_k", 10),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def performance_function(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = PERFORMANCE_SESSION_CACHE.get(params["session_id"])
        return query_performance_function(
            ds,
            name=params["name"],
            core=params.get("core"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def performance_hotspots(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = PERFORMANCE_SESSION_CACHE.get(params["session_id"])
        return query_performance_hotspots(
            ds,
            sort_by=params.get("sort_by", "inclusive"),
            top_k=params.get("top_k", 10),
            core=params.get("core"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def performance_callgraph(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = PERFORMANCE_SESSION_CACHE.get(params["session_id"])
        return query_performance_callgraph(
            ds,
            root=params["root"],
            depth=params.get("depth", 3),
            direction=params.get("direction", "callees"),
            core=params.get("core"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc


async def performance_get_source(
    params: dict[str, Any],
    session_manager: S32TraceSessionManager | None = None,
) -> Any:
    try:
        ds = PERFORMANCE_SESSION_CACHE.get(params["session_id"])
        return query_performance_get_source(
            ds,
            symbol=params.get("symbol"),
            file_hint=params.get("file_hint"),
            line=params.get("line"),
            core=params.get("core"),
            snippet_window=params.get("snippet_window"),
        )
    except KeyError as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "PRECONDITION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
    except Exception as exc:
        raise ActionExecutionError(
            _HANDLER_ERROR_CODE,
            "ACTION_FAILED",
            error_details={"message": str(exc)},
        ) from exc
