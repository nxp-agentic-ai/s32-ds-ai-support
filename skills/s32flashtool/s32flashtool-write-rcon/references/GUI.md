# S32FlashTool Write RCON/EEPROM - GUI / RPC flow

Use this flow only when the user requested GUI behavior or when an active GUI/RPC workflow is already in progress.

## GUI support
Supported.

## Relevant RPC methods
- config: `model.setFullConfigUploadHexToRcon`
- final action: `flash.clickUploadFileToDevice`

Use the method metadata returned by the action catalog as the primary source for:
- required prior steps
- payload shape and example values
- completion semantics
- destructive / confirmation requirements
- user reporting guidance

## Operation-specific caveats
- Writing RCON/EEPROM is destructive.
- The GUI-side destination is `EEPROM (RCON)`.
- Initialization is typically required before the final action.
- Do not claim the RCON write completed only because the final GUI action returned successfully.
- If the GUI operation is aborted, treat RCON contents as indeterminate until read back and inspected.
