# S32FlashTool Read Flash - GUI / RPC flow

Use this flow only when the user requested GUI behavior or when an active GUI/RPC workflow is already in progress.

## GUI support
Supported.

## Relevant RPC methods
- config (read to console/view): `model.setFullConfigDownloadFromDevice`
- final action (read to console/view): `flash.clickDownloadFromDevice`
- config (read to file): `model.setFullConfigDownloadFromDeviceToFile`
- final action (read to file): `flash.clickDownloadFromDeviceToFile`

Use the method metadata returned by the action catalog as the primary source for:
- required prior steps
- payload shape and example values
- completion semantics
- user reporting guidance

## Operation-specific caveats
- For `FLASH`, initialization is typically required before the final action.
- Do not claim the read completed only because the final GUI action returned successfully.
- For read-to-file, do not claim the output file is complete or authoritative until the GUI reports completion.
