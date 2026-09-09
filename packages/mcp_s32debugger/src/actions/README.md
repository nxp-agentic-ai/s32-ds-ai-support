# S32Debugger actions

This folder contains the executable action source of truth for the S32Debugger MCP server.

## Layout

- `*.py` - one Python module per action

The Python action modules in this folder and builds the runtime `ActionCatalog`.

## Current actions

### bridge
- `bridge.command`
- `bridge.create_config`
- `bridge.interrupt`
- `bridge.status`
- `bridge.transcript`

### control
- `control.adopt_session`
- `control.exec`
- `control.get_installation_path`
- `control.interrupt`
- `control.read_output`
- `control.set_installation_path`
- `control.start_gdb`
- `control.start_gta`
- `control.status`
- `control.stop_gdb`
- `control.stop_gta`
- `control.stop_session`
- `control.wait_output`

### generate
- `generate.config_from_template`

### inspect
- `inspect.all`
- `inspect.ccs`
- `inspect.ccs_port`
- `inspect.installation`
- `inspect.processes`
- `inspect.session_all`
- `inspect.session_diagnostics`
- `inspect.session_status`

## Example action module

Each action module exports either `ACTION_NAME = ActionExecutable(...)` or `ACTIONS = (...)`.

Example:

```python
from nxp.mcp.shared import ActionContract, ActionExecutable
from nxp.mcp.s32debugger.handlers.action_handlers import inspect_installation

INSPECT_INSTALLATION_ACTION = ActionExecutable(
    contract=ActionContract(
        name="inspect.installation",
        description="Inspect effective installation path resolution and current installation state.",
        related_actions=(
            "control.get_installation_path",
            "control.set_installation_path",
        ),
    ),
    handler=inspect_installation,
)
```

## Notes

- Keep contracts metadata-focused and handlers explicit.
- `params[]` should stay ordered with required params first.
- Public/agent-facing `input_schema` is derived by the shared action-protocol layer from internal `params[]`.
