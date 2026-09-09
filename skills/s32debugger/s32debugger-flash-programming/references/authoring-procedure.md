# Authoring Procedure

## Scenario classification

### Scenario A: flash-only
Use when the user wants to:
- write/program/flash a binary or ELF
- read/dump flash contents
- erase flash
- verify flash
- query flash info

And does not want to continue into same-session debug-from-flash.

### Scenario B: debug-from-flash
Use when the user wants to:
- flash/program an image
- then debug from flash
- without ending the session after programming

## Shared prerequisites

- GTA started before GDB
- GDB with Python support running
- probe/session connection established
- `s32flash.py` available
- valid bareboard init script chosen
- matching symbol file available for debug-from-flash continuation

## Routing

- flash-only -> `s32debugger-flash-only-operations`
- same-session debug-from-flash -> `s32debugger-debug-from-flash`

## Key distinctions

### Flash-only
- ends with `fl_close`
- does not continue into symbolic debug

### Debug-from-flash
- stays in the same GDB session
- does not end with `fl_close`
- continues with reset/register/PC/symbol steps

## Fallback policy

If the request is incomplete:
1. identify whether the ambiguity is about intent or startup context
2. ask for the smallest missing routing detail
3. avoid expanding into full execution logic
4. re-route as soon as the request becomes clear
