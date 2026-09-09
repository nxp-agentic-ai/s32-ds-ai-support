# S32FlashTool SRAM Execute - GUI / RPC flow

Use this flow only when the user requested GUI behavior or when an active GUI/RPC workflow is already in progress.

## GUI support
Partially supported.

## Relevant RPC methods
- config: `model.setFullConfigSram`
- follow-up action: `init.clickLaunchInitialization`
- final execute action: not exposed separately through the documented GUI/RPC action set

Use the method metadata returned by the action catalog as the primary source for:
- required prior steps
- payload shape and example values
- completion semantics
- user reporting guidance

## Operation-specific caveats
- `model.setFullConfigSram` is a configuration-only step.
- `init.clickLaunchInitialization` is the next exposed GUI/RPC step, but it does not imply that a separate final SRAM execute action exists over RPC.
- Do not claim the SRAM binary was executed through RPC unless such an exposed final action actually exists and was called.
- Success usually requires confirmation from the target, not just from the GUI/RPC call sequence.
