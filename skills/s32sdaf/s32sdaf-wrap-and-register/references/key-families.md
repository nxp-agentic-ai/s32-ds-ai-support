# Wrap-and-register key-family requirements

Per-family requirements, validation rules, and error handling for the
`s32sdaf-wrap-and-register` workflow. Load on demand by reading
`references/key-families.md` from this skill directory.

> Note: This file is intentionally self-contained and scoped to the
> `s32sdaf-wrap-and-register` workflow. It deliberately overlaps with
> `s32sdaf-register-key/references/key-families.md`; each skill keeps its own
> copy so it can be loaded and reasoned about in isolation without a
> cross-skill dependency. Keep shared facts (per-family table, formats) in sync
> across both files when either is updated.


## Rule of thumb

- **ADKP is the only key type that can be registered in plain form** - it does
  not use this skill; use `s32sdaf-register-key`.
- **Every non-ADKP key type must be wrapped first** before registration.
- The wrapped result passed into registration must be exactly **512 hex
  characters**.

## UID and key input

- UID: 16 hex characters = 8-byte UID; 32 hex characters = 16-byte UID.
- Plain key: valid hex suitable for the intended wrapped-key workflow. Do not
  infer the exact semantic type from length alone; use user intent plus
  workflow context.

## Per-family requirements

| Family | UID | OID | key_index | adk2_key_type | Applet |
|--------|-----|-----|-----------|---------------|--------|
| `KUID` | 8 or 16 byte | - | - | - | - |
| `KUID_RF` | 8 or 16 byte | - | - | - | 1.4+ |
| `KUID_PRE_FA` | 8 or 16 byte | - | - | - | 1.4+ |
| `ODAK` | 16 byte (32 hex) | - | - | - | 1.5+ |
| `ADK1` | 16 byte (32 hex) | 16 byte (32 hex) | 0..15 | - | 1.5+ |
| `ADK2` | 16 byte (32 hex) | 16 byte (32 hex) | 0..15 | AES or ECC | 1.5+ |

Notes:
- ODAK rejects an 8-byte UID.
- OID, when required, is valid hex of exactly 32 characters (16 bytes). Do not
  trim, pad, or normalize it silently.

## Decision logic

- **User already has a valid wrapped (512-hex) key** -> do not re-export or
  re-wrap; switch to `s32sdaf-register-key`.
- **User wants plain ADKP** -> do not wrap; switch to `s32sdaf-register-key`.
- **User has a plain key for a wrapped family** (`KUID`, `KUID_RF`,
  `KUID_PRE_FA`, `ODAK`, `ADK1`, `ADK2`) -> proceed with this skill.

## Error handling

- **Invalid UID format** - must be hex, 16 or 32 chars.
- **Invalid plain key** - must be hex; if the user supplied a wrapped key,
  redirect to `s32sdaf-register-key`.
- **Invalid OID** - must be valid hex of exactly 32 chars for ADK1/ADK2.
- **Export wrapkey failure** - card may be unavailable/not ready; verify card
  connection and environment.
- **Wrap failure** - plain key or public key may be invalid; verify hex,
  re-export the public wrapping key if needed. If the failure looks like a
  missing command or bad invocation, note wrapping must use
  `volkano_utils.exe -cmd wrap_key` and classify it as a wrapper/backend defect
  (do not switch to `volkano.exe`).
- **Wrapped-key validation failure** - if the result is not 512 hex chars, stop
  before registration.
- **Registration failure** - report the exact tool failure; likely causes are
  card capacity, password, wrapped-key validity, or selector mismatch. If the
  card may be full, recommend discovery and cleanup before retrying.
- **ODAK with 8-byte UID** - reject; ODAK requires a 16-byte UID.
- **ADK1 / ADK2 selector errors** - report clearly when `oid`, `key_index`, or
  `adk2_key_type` is missing or invalid.
