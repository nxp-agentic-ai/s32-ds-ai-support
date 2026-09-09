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

"""Canonical public manifest for S32Trace action executables.

Consumers should import ``ACTIONS`` from this package to build the active
component action catalog. Individual action constants remain module-level
implementation details.
"""

from .list_configurator_templates import LIST_CONFIGURATOR_TEMPLATES_ACTION
from .inspect_configurator_template import INSPECT_CONFIGURATOR_TEMPLATE_ACTION
from .describe_trace_flow import DESCRIBE_TRACE_FLOW_ACTION
from .create_from_template import CREATE_FROM_TEMPLATE_ACTION
from .set_output_folder import SET_OUTPUT_FOLDER_ACTION
from .set_target_access import SET_TARGET_ACCESS_ACTION
from .set_timestamp_generator import SET_TIMESTAMP_GENERATOR_ACTION
from .configure_data_streams import CONFIGURE_DATA_STREAMS_ACTION
from .configure_sink import CONFIGURE_SINK_ACTION
from .configure_core import CONFIGURE_CORE_ACTION
from .configure_soc_module import CONFIGURE_SOC_MODULE_ACTION
from .analysis_load_trace import ANALYSIS_LOAD_TRACE_ACTION
from .analysis_summary import ANALYSIS_SUMMARY_ACTION
from .analysis_find_event import ANALYSIS_FIND_EVENT_ACTION
from .analysis_address_at import ANALYSIS_ADDRESS_AT_ACTION
from .analysis_time_between import ANALYSIS_TIME_BETWEEN_ACTION
from .analysis_range_events import ANALYSIS_RANGE_EVENTS_ACTION
from .analysis_get_source import ANALYSIS_GET_SOURCE_ACTION
from .timeline_load import TIMELINE_LOAD_ACTION
from .timeline_summary import TIMELINE_SUMMARY_ACTION
from .timeline_hotspots import TIMELINE_HOTSPOTS_ACTION
from .timeline_function import TIMELINE_FUNCTION_ACTION
from .timeline_window import TIMELINE_WINDOW_ACTION
from .timeline_sequence import TIMELINE_SEQUENCE_ACTION
from .timeline_source import TIMELINE_SOURCE_ACTION
from .coverage_load import COVERAGE_LOAD_ACTION
from .coverage_summary import COVERAGE_SUMMARY_ACTION
from .coverage_function import COVERAGE_FUNCTION_ACTION
from .coverage_file import COVERAGE_FILE_ACTION
from .coverage_uncovered import COVERAGE_UNCOVERED_ACTION
from .coverage_hotspots import COVERAGE_HOTSPOTS_ACTION
from .coverage_get_source import COVERAGE_GET_SOURCE_ACTION
from .performance_load import PERFORMANCE_LOAD_ACTION
from .performance_summary import PERFORMANCE_SUMMARY_ACTION
from .performance_function import PERFORMANCE_FUNCTION_ACTION
from .performance_hotspots import PERFORMANCE_HOTSPOTS_ACTION
from .performance_callgraph import PERFORMANCE_CALLGRAPH_ACTION
from .performance_get_source import PERFORMANCE_GET_SOURCE_ACTION


ACTIONS = (
    LIST_CONFIGURATOR_TEMPLATES_ACTION,
    INSPECT_CONFIGURATOR_TEMPLATE_ACTION,
    DESCRIBE_TRACE_FLOW_ACTION,
    CREATE_FROM_TEMPLATE_ACTION,
    SET_OUTPUT_FOLDER_ACTION,
    SET_TARGET_ACCESS_ACTION,
    SET_TIMESTAMP_GENERATOR_ACTION,
    CONFIGURE_DATA_STREAMS_ACTION,
    CONFIGURE_SINK_ACTION,
    CONFIGURE_CORE_ACTION,
    CONFIGURE_SOC_MODULE_ACTION,
    ANALYSIS_LOAD_TRACE_ACTION,
    ANALYSIS_SUMMARY_ACTION,
    ANALYSIS_FIND_EVENT_ACTION,
    ANALYSIS_ADDRESS_AT_ACTION,
    ANALYSIS_TIME_BETWEEN_ACTION,
    ANALYSIS_RANGE_EVENTS_ACTION,
    ANALYSIS_GET_SOURCE_ACTION,
    TIMELINE_LOAD_ACTION,
    TIMELINE_SUMMARY_ACTION,
    TIMELINE_HOTSPOTS_ACTION,
    TIMELINE_FUNCTION_ACTION,
    TIMELINE_WINDOW_ACTION,
    TIMELINE_SEQUENCE_ACTION,
    TIMELINE_SOURCE_ACTION,
    COVERAGE_LOAD_ACTION,
    COVERAGE_SUMMARY_ACTION,
    COVERAGE_FUNCTION_ACTION,
    COVERAGE_FILE_ACTION,
    COVERAGE_UNCOVERED_ACTION,
    COVERAGE_HOTSPOTS_ACTION,
    COVERAGE_GET_SOURCE_ACTION,
    PERFORMANCE_LOAD_ACTION,
    PERFORMANCE_SUMMARY_ACTION,
    PERFORMANCE_FUNCTION_ACTION,
    PERFORMANCE_HOTSPOTS_ACTION,
    PERFORMANCE_CALLGRAPH_ACTION,
    PERFORMANCE_GET_SOURCE_ACTION,
)


__all__ = ["ACTIONS"]
