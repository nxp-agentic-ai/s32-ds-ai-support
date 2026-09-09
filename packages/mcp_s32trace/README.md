# mcp_s32trace

MCP server for **S32Trace** - the NXP trace capture and analysis tool bundled with S32 Design Studio.

The server exposes two independent action categories:

## Configurator actions (`configurator.*`)

Create and edit S32Trace configuration XML files from within the chat, without opening the S32Trace GUI.

| Action | What it does |
|---|---|
| `configurator.list_templates` | List all S32Trace configuration templates installed with S32DS |
| `configurator.inspect_template` | Show every configurable attribute in a template or saved config |
| `configurator.describe_trace_flow` | Parse a config and return the full trace pipeline (cores, sinks, funnels) |
| `configurator.create_from_template` | Copy a template to a new output path |
| `configurator.set_output_folder` | Set the trace capture output folder in a config |
| `configurator.set_target_access` | Configure the GTA/CCS target-access endpoint |
| `configurator.set_timestamp_generator` | Enable/disable and configure the timestamp generator |
| `configurator.configure_data_streams` | Set trace location (ETF/DDR) and collection mode |
| `configurator.configure_sink` | Configure an ETF or DDR sink |
| `configurator.configure_core` | Enable/disable a core and set its tracing options |
| `configurator.configure_soc_module` | Configure a funnel or other SoC module |

## Analysis actions (`analysis.*`)

Analyze a decoded S32Trace capture (Trace view CSV + ELF + optional source tree) and answer questions about instruction addresses, timing, hot functions, and code quality - all without opening S32DS.

### Inputs

| Input | Required | Description |
|---|---|---|
| CSV | Yes | Decoded Trace-view CSV exported from S32Trace. Located in `.AnalysisData/<name>/<name>.csv`. |
| ELF | Yes | Application ELF binary with DWARF debug info. Located next to the CSV as `<name>_<core>.elf`. |
| Source root | Optional | Root of the project source tree. Enables code snippets in query results. |

### Actions

| Action | What it does |
|---|---|
| `analysis.load_trace` | Load CSV + ELF (+ optional source root) and return a `trace_id` handle |
| `analysis.summary` | Total duration, per-core counts, top-N hottest functions by event count and instruction count |
| `analysis.find_event` | Filter events by symbol, address range, file:line, event type, core, time range, or instruction regex |
| `analysis.address_at` | ELF lookup: resolve an address or symbol name to symbol@offset, file:line, and a source snippet |
| `analysis.time_between` | Measure the time delta between two matched events; summarize intermediate symbols |
| `analysis.range_events` | Roll up all events between two timestamps or two event selectors |
| `analysis.get_source` | Fetch a source code snippet by file:line or symbol name |

### Example session

```
1. analysis.load_trace(
     csv_path    = "C:/.AnalysisData/trace_0/trace_0.csv",
     elf_path    = "C:/.AnalysisData/trace_0/trace_0_R52_0_0.elf",
     source_root = "C:/myproject/src",
     time_unit_ns = 1.0
   )
   -> { trace_id: "abc-123", parent_event_count: 45321, ... }

2. analysis.summary(trace_id="abc-123")
   -> { top_functions_by_events: [{ symbol: "ISR_Handler", event_count: 8000 }, ...] }

3. analysis.get_source(trace_id="abc-123", symbol="ISR_Handler")
   -> { snippet: { file: "...", lines: [...] } }

4. analysis.time_between(
     trace_id      = "abc-123",
     from_selector = { symbol: "ISR_Enter" },
     to_selector   = { symbol: "ISR_Exit" },
     occurrence    = "all"
   )
   -> { pairs: [{ delta_raw: 1234, delta_ns: 1234.0, ... }, ...] }
```

## Configuration

The server requires `installation_path` to point to the S32DS installation.
Set it in `configs/s32trace.standalone.yaml` or pass `s32ds_installation_path`
per call for the configurator actions.

Analysis actions do not require an S32DS installation - they only read the CSV,
ELF, and source files you provide.
