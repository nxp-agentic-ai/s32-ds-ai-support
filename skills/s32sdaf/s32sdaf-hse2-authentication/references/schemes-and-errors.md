# HSE2 scheme selection, key paths, and error handling

Decision logic, key-selection guidance, and failure catalog for
`s32sdaf-hse2-authentication`. Load on demand by reading
`references/schemes-and-errors.md` from this skill directory.


## Scheme map (from the KB)

- `scheme_id = 1` -> HSE1-based S32 family flows (use `s32sdaf-auth-device`).
- `scheme_id = 2` -> HSE2, BootROM-defined algorithms.
- `scheme_id = 3` -> HSE2, HSE-FW-defined algorithms.

HSE2 schemes (`scheme_id > 1`) require applet version **1.5+**.
The KB documents a **32-byte challenge** requirement for response calculation.

## Grounded command reference

`volkano.exe get_response` documented parameters:
`-uid <UID value>`, `-oid <OID value>`, `-chlg <challenge value>`,
`-key [key name]`, `-scheme_id <1|2|3>`.

This documents raw semantics for reasoning only. The generic MCP wrapper
`execute_action(action="get_response", params={...})` does not expose `-scheme_id`, `-oid`, or
`-key`. If the chosen HSE2 path depends on any of them, the wrapper is
insufficient - do not treat a wrapper invocation as having tested the raw HSE2
path.

## Decision logic

- **Case 0 - chosen HSE2 mode needs selectors not in the wrapper**
  (`scheme_id`, `oid`, `key`/key-name/index, or any raw selector): do not treat
  the wrapper as equivalent; stop with an implementation-gap explanation or
  switch to a raw-command-capable path.
- **Case 1 - user says HSE2 BootROM**: select `scheme_id = 2`; determine ADKP
  vs ADK1; verify prerequisites.
- **Case 2 - user says HSE2 HSE-FW**: select `scheme_id = 3`; determine key
  context; verify prerequisites.
- **Case 3 - HSE2 but BootROM vs HSE-FW unknown**: ask one concise
  clarification question; do not guess when correctness depends on it.
- **Case 4 - scheme known, key path unknown**: determine ADKP vs ADK1 using
  discovery / registration knowledge; do not assume.
- **Case 5 - really a generic flow**: route back to `s32sdaf-auth-device`.

## Key-selection guidance

- **ADKP-backed HSE2 response** - based on device UID and ADKP material; the
  simpler path when no OID/ADK1 context is involved.
- **ADK1-backed HSE2 response** - relies on OID-associated ADK1 material; the
  user must have the OID/key context available.
- **ADK2 is not a supported response-calculation selector here.** The KB
  documents ADK2 for debug-card/DCAT; redirect to `s32sdaf-generate-debug-card`
  if the user mentions ADK2 for challenge-response.

## Error handling

- **HSE2 scheme not specified** - ask one concise BootROM-vs-HSE-FW question;
  do not guess.
- **Invalid challenge format** - must be valid hex and match expected size; do
  not fabricate or normalize silently.
- **Missing UID** - required and must correspond to a registered record.
- **Missing OID / ADK1 context** - stop and resolve first; use discovery.
- **Applet too old** - HSE2 schemes require applet 1.5+.
- **Wrong key type (ADK2 for challenge-response)** - explain ADK2 is for
  debug-card/DCAT; redirect to `s32sdaf-generate-debug-card`.
- **Wrapper reports missing challenge though it was provided and validated**
  (valid hex, even length, correct expected size): do not blame the input.
  Confirm whether the mode required selectors not exposed by the wrapper, and
  explain the wrapper may be building an incomplete/mismatched raw command.
- **Smart card unavailable or key missing** - classify as connectivity / UID
  not registered / required key missing / wrong scheme selection.
