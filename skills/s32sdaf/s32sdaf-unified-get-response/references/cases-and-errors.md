# Unified get_response: cases, decision table, and error handling

Supported cases, validation rules, wrapper-vs-raw decision table, and failure
catalog for `s32sdaf-unified-get-response`. Load on demand by reading
`references/cases-and-errors.md` from this skill directory.


## Supported cases

- **A** UID + challenge only
- **B** UID + challenge + `ADKP`
- **C** UID + challenge + `kUID`
- **D** UID + challenge + `scheme_id = 2` + `ADKP`
- **E** UID + challenge + `scheme_id = 2` + `kUID`
- **F** UID + challenge + `scheme_id = 3` + `ADKP`
- **G** UID + challenge + `scheme_id = 3` + `ADK1` + OID / key context
- **H** UID index input such as `UID#2`
- **I** discovery-assisted handling when the UID exists but requested key
  material is missing
- **J** wrapper failure that should trigger raw fallback rather than a
  misleading user-facing conclusion

## Input validation

**UID** - direct: 16 hex (8-byte) or 32 hex (16-byte). Index: `UID#<n>` /
`uid#<n>`, resolved through discovery before execution.

**Challenge** - valid hex, even number of hex chars, matching the expected size
for the selected workflow when known. Do not trim/pad/normalize/reinterpret.

**Scheme** - `1` generic/HSE1-style; `2` HSE2 BootROM-defined; `3` HSE2
HSE-FW-defined. If clearly HSE2 but scheme unspecified, ask one concise
question.

**Key family** - `ADKP` valid for normal flows; `kUID` may be valid on some
installed combinations but must not be substituted for `ADKP` or vice versa;
`ADK1` requires OID / key-name context; `ADK2` is not for standard
`get_response` (redirect to debug-card / DCAT).

## Wrapper vs raw decision table

Generic / HSE1-style:
- UID + challenge only -> wrapper usually appropriate.
- + `ADKP` -> wrapper if `key` is supported.
- + `kUID` -> wrapper only if supported and accepted by installed Volkano.

HSE2 BootROM (`scheme_id = 2`):
- + `ADKP` -> wrapper only if `scheme_id` is truly exposed and forwarded.
- + `kUID` -> same rule; else raw path or report implementation gap.

HSE2 HSE-FW (`scheme_id = 3`):
- + `ADKP` -> wrapper only if fully supported.
- + `ADK1` -> usually requires `oid` and possibly `key_name`; raw path if the
  wrapper cannot represent the full selector set.

Selection logic:
1. All required selectors fit the wrapper surface? yes -> wrapper; no -> raw.
2. Raw-command path actually available? yes -> use it; no -> stop with
   implementation-gap explanation.
3. Wrapper call fails in a way suggesting abstraction mismatch? do not blame
   input; consider raw fallback if available.

Conceptual raw shape:
`volkano.exe -pw <password> -cmd get_response -uid <UID> -chlg <challenge>
[-key <selector>] [-oid <OID>] [-scheme_id <N>]`. Document for reasoning only;
do not claim success through it unless a raw-capable tool was actually used.

## Error handling

- **Invalid UID format** - hex, 16 or 32 chars.
- **UID index not found** - report the index is absent; do not guess another.
- **UID not registered** - report; redirect to `s32sdaf-register-key`.
- **Malformed challenge** - invalid hex or odd length: report; do not execute.
- **Wrong challenge size for scheme** - explain mismatch; stop rather than
  silently normalizing.
- **Requested key material missing** - report the path cannot be used with
  current card contents; do not silently switch families.
- **Wrapper rejects a locally valid request** (`Invalid key selected`,
  `Missing the challenge`, usage errors): consider the flow exceeded the wrapper
  abstraction; prefer raw fallback if available; else report a wrapper
  limitation, not an input-validation failure.
- **HSE2 selectors not executable through current tools** - explain the flow is
  valid conceptually but the tool surface cannot execute it faithfully; do not
  claim to have tested the raw path.
- **ADK1 missing OID / key context** - stop and request it; do not guess.
- **ADK2 in get_response** - not part of the normal path; redirect to
  `s32sdaf-generate-debug-card`.

## Result formatting

Success: `UID input` (if index), `Resolved UID`, `Challenge`, `Key family`
(ADKP/kUID/ADK1), `Scheme` (1/2/3 with label), `Execution path` (wrapper/raw),
`Response`. Failure: validated inputs, which step failed, failure class
(input / card-state / wrapper / execution-surface), and the clean next step.
