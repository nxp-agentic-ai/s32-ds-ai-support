# Editing the `.launch` File for Secure Debugging

The S32DS MCP plugin exposes **no** action that can write the secure-debugging
fields: `listDebugLaunches` is read-only and `startDebug` only accepts
`name` / `build`. Therefore the primary, automatable way to enable secure
debugging is to edit the launch configuration's `.launch` XML directly. The
S32DS GUI (Debug Configurations -> Debugger tab) remains a manual fallback.

## 1. Find the file

Each config is stored under the project's `Project_Settings/Debugger/` folder as
`<config-name>.launch`:

```
<workspace>/<project>/Project_Settings/Debugger/<config-name>.launch
```

If unsure, search the workspace:

```
dir /s /b "<workspace>" | findstr /i "<config-name>.launch"
```

## 2. Required attributes

Set both of these lines:

```xml
<booleanAttribute key="com.nxp.s32ds.debug.ide.s32debugger.core.useSecureDebugging" value="true"/>
<stringAttribute  key="com.nxp.s32ds.debug.ide.s32debugger.core.secureDebuggingType" value="CR"/>
```

- `useSecureDebugging` -> `true` enables secure debugging.
- `secureDebuggingType` -> the exact token S32DS stores:
  - **`PWD`** = Password (static secret).
  - **`CR`**  = Challenge & Response (dynamic; smart card computes the response).
  - An empty value (`""`) means "not configured".

## 3. Related attributes (adjust only if needed)

All keys are prefixed with `com.nxp.s32ds.debug.ide.s32debugger.core.`

| Attribute suffix | Purpose |
|---|---|
| `secureDebuggingDebugCard` | path to the debug card / smart-card artifact (e.g. `${VOLKANO_UTILITY_DIR}/debug_card.bin`) |
| `useSecureDebuggingDebugCard` | `true` to use the debug-card file |
| `secureDebuggingKeyIndex` / `useSecureDebuggingKeyIndex` | key index selection |
| `secureDebuggingDebugSignalMap` / `useSecureDebuggingDebugSignalMap` | debug signal map |

Leave these at their defaults unless the SoC provisioning requires otherwise.

## 4. Persist / reload

If S32DS is running with the config open, it may cache the old values. After
editing on disk, either rebuild the project or restart S32DS / re-read the
config so the launch uses the new attributes before `startDebug`.

## Reading the SoC UID and registering the key (CR prerequisite)

For Challenge & Response the smart card must hold this SoC's **UID + ADKP**
before `startDebug` can unlock the chip. If it is not yet registered:

1. Make sure **no debug session is running** - the GTA utility launches its own
   server and will collide with an active session. Terminate first
   (`terminateDebug`).
2. Read the UID/status from the target:
   ```
   <S32DS>\tools\S32Debugger\Debugger\Server\gta\gta.exe -t s32dbg:<probe>
   ```
   - `<probe>` = the S32 Debug Probe **IP** (Ethernet) or its USB connection
     string. Do **not** assume `127.0.0.1`: that loopback is the GTA server, not
     the probe address; using it typically yields `SoC Error 301` / `327`.

     ```
     # Ethernet probe
     gta.exe -t s32dbg:192.168.0.1

     # USB probe (Windows — use the probe serial number)
     gta.exe -t s32dbg:usb:<serial>
     ```
   - On success GTA prints the security state and the Device Unique ID (UID).
3. Register the UID with the sample's ADKP:
   ```
   execute_action(action="register_key", params={"key_type":"ADKP",
                  "uid":"<uid>", "key":"<ADKP hex>",
                  "password":"<smart-card password>"})
   ```
   Length rule: 8-byte UID -> 16-byte (32 hex) ADKP; 16-byte UID -> 32-byte
   (64 hex) ADKP. Provide the ADKP without a leading `0x`.
4. Confirm with `execute_action(action="discover", params={...})` that the UID
   now lists `ADKP`.

### GTA `gta.exe -t s32dbg:<probe>` error codes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ccs:CC driver failure` / `SoC Error 301` | Probe/target unreachable, CC driver could not open the connection | Verify the probe is powered and reachable; use the real probe IP/USB string, not `127.0.0.1`; ensure no other tool/session holds the probe |
| `SoC Error 327` | Target not responding / wrong probe address / board off | Power-cycle the board, confirm cabling and probe address |
| GTA hangs or refuses to start | A debug session or another GTA instance is already running | Terminate the debug session (`terminateDebug`); if it still hangs, confirm no stale `gta.exe` remains and kill it - on Windows: `taskkill /F /IM gta.exe` - then retry |

## Error catalog

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Error 102 / "SoC is still secure" | Secure debugging not enabled, or unlock failed | Confirm `useSecureDebugging=true` and the right `secureDebuggingType`; enable the GDB Server log to see the unlock exchange |
| Secure debug enabled but no unlock attempt occurs | `secureDebuggingType` is empty (`""`) or missing | Set `secureDebuggingType` to `PWD` or `CR` explicitly |
| Error 601 / no console error | Wrong auth type, wrong password, or the debug key does not match the SoC | Match the SoC's provisioned type (PWD vs CR); verify the correct password / registered key; power-cycle before retry |
| IDE never prompts / C&R does nothing | Smart card / Secure Keys Registry not selected in the config | Set the card/registry attributes for Challenge & Response |
| Smart-card auth dialog fails | Card not inserted / wrong smart-card password | Verify reader and card; do not guess the password |
| Debug key not found for this SoC | Key never registered, or registered for a different UID | Register the debug key once for this exact SoC (`s32sdaf-register-key`) |
