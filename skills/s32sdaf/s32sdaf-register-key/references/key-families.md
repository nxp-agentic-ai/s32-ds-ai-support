# Register-key families, validation, and error handling

Per-family requirements, decision logic, and failure catalog for
`s32sdaf-register-key`. Load on demand by reading
`references/key-families.md` from this skill directory.

> Note: This file is intentionally self-contained and scoped to the
> `s32sdaf-register-key` workflow. It deliberately overlaps with
> `s32sdaf-wrap-and-register/references/key-families.md`; each skill keeps its
> own copy so it can be loaded and reasoned about in isolation without a
> cross-skill dependency. Keep shared facts (per-family table, formats) in sync
> across both files when either is updated.


## Core rule

- **ADKP is the only key type that may be registered in plain form.**
- **All other families use wrapped key material** (exactly 512 hex characters).
- Plain non-ADKP key material must be wrapped first via
  `s32sdaf-wrap-and-register`.

## Input formats

- UID: 16 hex chars = 8-byte; 32 hex chars = 16-byte.
- OID (when required): valid hex, exactly 32 hex chars (16 bytes). Do not trim,
  pad, or normalize silently.
- Plain ADKP: 32 hex chars (16-byte, with 8-byte UID) or 64 hex chars (32-byte,
  with 16-byte UID). `keybin` may supply the ADKP as a binary-file path.
- Wrapped key: exactly 512 hex chars.

## Per-family requirements

| Family | UID | OID | key_index | adk2_key_type | Applet | Form |
|--------|-----|-----|-----------|---------------|--------|------|
| `ADKP` | 8 or 16 byte | - | - | - | 1.4+ | plain (hex or keybin) |
| `ODAK` | 16 byte | - | - | - | 1.5+ | wrapped |
| `ADK1` | 16 byte | 16 byte | 0..15 | - | 1.5+ | wrapped |
| `ADK2` | 16 byte | 16 byte | 0..15 | AES or ECC | 1.5+ | wrapped |
| `KUID` | 8 or 16 byte | - | - | - | - | wrapped |
| `KUID_RF` | 8 or 16 byte | - | - | - | 1.4+ | wrapped |
| `KUID_PRE_FA` | 8 or 16 byte | - | - | - | 1.4+ | wrapped |

## Decision logic

- **Case 1 - plain ADKP**: valid ADKP length for the UID, or a binary `keybin`.
  Call `execute_action(register_key)(key_type="ADKP", ...)` (compat:
  `execute_action(action="register_key", params={"key_type":"ADKP", ...})`).
- **Case 2 - wrapped KUID-family** (`KUID`, `KUID_RF`, `KUID_PRE_FA`, `ODAK`):
  wrapped key of 512 hex chars. Use `execute_action(action="register_key", params={...})` (compat
  for plain KUID only: `execute_action(action="register_key", params={"key_type":"kUID", ...})`).
- **Case 3 - plain key for a non-ADKP family**: do not register directly;
  switch to `s32sdaf-wrap-and-register`.
- **Case 4 - ODAK**: require 16-byte UID (reject 8-byte); applet 1.5+.
- **Case 5 - ADK1**: 16-byte UID, 16-byte OID, wrapped key, key_index 0..15;
  applet 1.5+. Call `register_key(key_type="ADK1", ...)`.
- **Case 6 - ADK2**: 16-byte UID, 16-byte OID, wrapped key, key_index 0..15,
  `adk2_key_type` in {AES, ECC}; applet 1.5+. Call
  `register_key(key_type="ADK2", ...)`.
- **Case 7 - KUID_RF / KUID_PRE_FA**: wrapped material, applet 1.4+, generic
  register tool.

## Error handling

- **Invalid UID** - must be hex, 16 or 32 chars.
- **Invalid OID** - must be valid hex of exactly 32 chars for ADK1/ADK2.
- **Invalid ADKP length** - 8-byte UID + 16-byte ADKP, or 16-byte UID + 32-byte
  ADKP.
- **Invalid wrapped-key length** - must be exactly 512 hex chars.
- **ODAK with 8-byte UID** - reject; ODAK requires a 16-byte UID (32 hex).
- **ADK1/ADK2 selector errors** - report clearly when `oid`, `key_index`, or
  `adk2_key_type` is missing/invalid.
- **Plain non-ADKP key for a wrapped family** - cannot register directly;
  redirect to `s32sdaf-wrap-and-register`.
- **Smart card full** - explain storage appears full; recommend discovery and
  deleting unused records before retrying.
- **Auth/password failure** - report clearly; do not guess or retry with
  invented credentials.
- **Card unavailable** - verify card connection, reader, install/config; use
  status or installation discovery.
- **Wrapped-key failure** - the wrapped data may be invalid; verify it was
  wrapped with the card's public wrapping key. If the user has only plain
  material, switch to `s32sdaf-wrap-and-register`.
