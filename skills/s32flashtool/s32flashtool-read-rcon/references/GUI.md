# S32FlashTool Read RCON/EEPROM - GUI / RPC flow

Use this flow only when the user requested GUI behavior or when an active GUI/RPC workflow is already in progress.
VERY IMPORTANT: read `s32flashtool-rpc-api/SKILL.md` only before the first `gui_* action` call.

## RPC transport rules
Also apply:
- `s32flashtool-rpc-api/SKILL.md`

## Standard GUI read-to-console workflow
1. Probe the GUI RPC session with action=`hello` only if the previous RPC API command failed
2. If using UART, set:
   - `communicationDevice = COM`
   - `comPort = "<COMx[,ftdi]>"`
3. Set `fullConfigDownloadFromDevice` with `destination`=`EEPROM (RCON)` and `algorithmId`=`RCON`
4. Call `init.clickLaunchInitialization`
5. Call `flash.clickDownloadFromDevice`
6. Tell the user "Please continue and monitor/complete the actual read operation in the S32FlashTool GUI window.".
7. STOP (don't inspect GUI/log/output/status)

## Standard GUI read-to-file workflow
1. Probe the GUI RPC session with action=`hello` only if the previous RPC API command failed
2. If using UART, set:
   - `communicationDevice = COM`
   - `comPort = "<COMx[,ftdi]>"`
3. Set `fullConfigDownloadFromDeviceToFile` with `destination`=`EEPROM (RCON)` and `algorithmId`=`RCON`
4. Call `init.clickLaunchInitialization`
5. Call `flash.clickDownloadFromDeviceToFile`
6. Tell the user "Please continue and monitor/complete the actual operation in the S32FlashTool GUI window.".
7. STOP (don't inspect GUI/log/output/status)

## Required GUI config payload fields
Use:

- `targetId` - not as full path
- `algorithmId` - not as full path
- `destination`
- `startAddress` - as hex
- `size` - as hex
- `binaryMode`

For read-to-file also include:
- `filePath`

## GUI payload example: read to console
```json
{
  "targetId": "S32N5x",
  "algorithmId": "RCON",
  "destination": "EEPROM (RCON)",
  "filePath": "",
  "startAddress": "0x0",
  "size": "0x18",
  "binaryMode": false
}
```

## GUI payload example: read to file
```json
{
  "targetId": "S32N5x",
  "algorithmId": "RCON",
  "destination": "EEPROM (RCON)",
  "filePath": "C:/Users/username/Downloads/rcon_dump.bin",
  "startAddress": "0x0",
  "size": "0x18",
  "binaryMode": true
}
```

## GUI RPC example sequence
```json
[
  { "action": "hello" },
  {
    "action": "model.set",
    "params": { "key": "communicationDevice", "value": "COM" }
  },
  {
    "action": "model.set",
    "params": { "key": "comPort", "value": "COM15,ftdi" }
  },
  {
    "action": "model.set",
    "params": {
      "key": "fullConfigDownloadFromDevice",
      "value": {
        "targetId": "S32N5x",
        "algorithmId": "RCON",
        "destination": "EEPROM (RCON)",
        "filePath": "",
        "startAddress": "0x0",
        "size": "0x18",
        "binaryMode": false
      }
    }
  },
  { "action": "init.clickLaunchInitialization" },
  { "action": "flash.clickDownloadFromDevice" }
]
```

## GUI-specific rules
- For UART, use `communicationDevice = COM`, not `UART`.
- Reuse an existing RPC session if `hello` succeeds.
- Do not invent undocumented `model` keys.
- Do not invent undocumented actions.
- Do not call `model.get` after every `model.set` unless readback is needed.

## Failure modes (GUI-specific)

### Missing initialization (GUI / RPC)
- Symptom: `flash.clickDownloadFromDevice*` fails or reports that the source is not initialized when destination is `RCON`.
- Interpretation: `init.clickLaunchInitialization` was skipped or failed for `RCON`.
- Response:
  - Call `init.clickLaunchInitialization` before retrying the read.
  - If initialization itself fails, treat it as a target/algorithm mismatch or a communication failure.

### User-aborted read in GUI dialog
- Symptom: `flash.clickDownloadFromDevice` or `flash.clickDownloadFromDeviceToFile` returns successfully with destination `RCON`, but the GUI dialog is cancelled by the user, or the GUI reports the operation as aborted.
- Interpretation: the RPC click was dispatched; the read did not complete or completed partially.
- Response: do not present any returned bytes as authoritative. Report the read as cancelled and ask whether to re-run.
