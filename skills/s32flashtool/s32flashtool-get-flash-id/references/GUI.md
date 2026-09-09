# S32FlashTool Get Flash ID - GUI / RPC flow

Use this flow only when the user requested GUI behavior or when an active GUI/RPC workflow is already in progress.

## GUI support
Supported.

## Relevant RPC methods
- config: `model.setFullConfigGetFlashId`
- final action: `flash.clickGetId`

Use the method metadata returned by the action catalog as the primary source for:
- required prior steps
- payload shape and example values
- completion semantics
- user reporting guidance

## Operation-specific caveats
- This operation is non-destructive.
- For `FLASH`, initialization is typically required before the final action.
- Do not claim the flash ID was obtained only because the final GUI action returned successfully.
