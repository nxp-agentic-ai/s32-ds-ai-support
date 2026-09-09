# Authoring Procedure

## Mandatory globals sequence

Set these before sourcing any init script, in this order-sensitive preparation
phase:
1. `_PROBE_IP`
2. `_SOC_NAME`
3. `_CORE_NAME`

Use authoritative `_SOC_NAME` and `_CORE_NAME` values from family context.
Use `s32dbg:<probe-ip>` for `_PROBE_IP`.
Do not source any init script before these mandatory globals are set.

## Scenario mapping

### Bareboard load/debug sequence
1. Use `<family>_generic_bareboard.py`.
2. Use `<family>_generic_bareboard_all_cores.py` for multicore/all-core flows.
3. Source the selected script.
4. Call `board_init()`.
5. Call `core_init()`.
6. Use `load` plus `symbol-file`.

### Attach from first instruction sequence
1. Use `<family>_attach_first_instruction.py`.
2. Source the script.
3. Use `symbol-file` only.
4. Do not use `load`.

### Attach to running target sequence
1. Use `<family>_attach.py`.
2. Source the script.
3. Use `symbol-file` only.
4. Do not reframe it as full bareboard reinitialization.

### Multicore follow-on connection sequence
1. Reuse the appropriate script for the family and scenario.
2. Source the script if needed for the follow-on client.
3. Skip `board_init()`.
4. Run only `core_init()`.

### Flash programming boundary
1. Use the appropriate bareboard init path only as context when needed.
2. Hand physical flash writes to `s32debugger-flash-programming`.
3. Do not use GDB `load` as a flash substitute.

## Ordering rules

After sourcing the init script:
1. `board_init()` first when full board bring-up is required.
2. `core_init()` second.

In a multicore session:
1. First core -> `board_init()` then `core_init()`.
2. Subsequent cores -> `core_init()` only.
3. Do not call `board_init()` more than once in the multicore session.

## Load vs symbols rules

1. Use `load` only for memory-loading scenarios.
2. Use `symbol-file` for attach scenarios and explicit symbolization.
3. Do not treat `load` as a flash-programming primitive.

## Optional overrides

Only set optional globals when needed, such as:
- `_REMOTE_TIMEOUT`
- `_IS_LOGGING_ENABLED`
- `_JTAG_SPEED`
