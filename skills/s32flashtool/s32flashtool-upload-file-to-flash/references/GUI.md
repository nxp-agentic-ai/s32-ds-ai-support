# S32FlashTool Program Flash Memory - GUI / RPC flow

Use this flow only when the user requested GUI behavior or when an active GUI/RPC workflow is already in progress.

## GUI support
Supported.

## Relevant RPC methods
- config: `model.setFullConfigUploadFileToDevice`
- final action: `flash.clickUploadFileToDevice`

Use the method metadata returned by the action catalog as the primary source for:
- required prior steps
- payload shape and example values
- completion semantics
- destructive / confirmation requirements
- user reporting guidance
- validation hints

## Operation-specific caveats
- Programming flash is destructive.
- For `FLASH`, initialization is typically required before the final action.
- Do not claim programming completed only because the final GUI action returned successfully.
- If the GUI operation is aborted, treat flash contents as indeterminate until validated.
