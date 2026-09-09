# S32FlashTool Erase Flash - GUI / RPC flow

Use this flow only when the user requested GUI behavior or when an active GUI/RPC workflow is already in progress.

## GUI support
Supported.

## Relevant RPC methods
- config: `model.setFullConfigEraseFlashMemory`
- final action: `flash.clickEraseMemoryRange`

Use the method metadata returned by the action catalog as the primary source for:
- required prior steps
- payload shape and example values
- completion semantics
- destructive / confirmation requirements
- user reporting guidance
- validation hints

## Operation-specific caveats
- Erase is destructive.
- For `FLASH`, initialization is typically required before the final action.
- Sector-based flash may erase a larger region than the requested byte range.
- Do not claim the erase completed only because the final GUI action returned successfully.
