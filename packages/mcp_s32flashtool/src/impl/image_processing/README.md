# image_processing

Copied integration subset from `board-config-mcp` for board image alignment and configuration analysis.

## Included
- `src/board_config_mcp/vision/align.py`
- `src/board_config_mcp/runtime_rules.py`
- `src/board_config_mcp/dataset_store.py`
- `src/board_config_mcp/server.py`
- `src/board_config_mcp/editor_backend.py`
- `apps/roi-editor/index.html`
- `run_editor.py`
- `schemas/board.schema.json`
- `boards/S32N79-RDB/board.json`
- `examples/run_partial_match_demo.py`

## Notes
This folder now contains a broader support subset, including:
- `faiss_store.py`
- `template_store.py`
- `schemas.py`
- `vision/annotate.py`
- `vision/classify.py`
- `vision/sample_data.py`

Some of these are lightweight compatibility copies/placeholders to make the transplanted module easier to run inside the target MCP workspace.

## Run the ROI editor
From:

```bat
C:\Users\nxf94919\Documents\mcp_server\image_processing
```

run:

```bat
python run_editor.py
```

Then open:

```text
http://127.0.0.1:8010/
```

## Runtime dependencies
Requires Python packages used by the original project, especially:
- `opencv-python`
- `numpy`
- `Pillow`
- `fastmcp`
- `pydantic`
- `fastapi`
- `uvicorn`
