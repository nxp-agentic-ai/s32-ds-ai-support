# Typical Usage Examples  -  s32ct-pins-info

This file is referenced from `SKILL.md`. It captures the canonical
invocation payloads for the five most common query patterns this skill
handles. Examples use `S32K312_172HDQFP` for concreteness; substitute any
other `<mcu> / <platform_sdk> / <package>` triple to ask the same
questions on a different device.

## 1. Package overview
> "What's on the `S32K312_172HDQFP` package?"

```jsonc
{ "mcu": "S32K312", "package": "S32K312_172HDQFP", "include_routings": false }
```
-> Returns `part_number`, total pin count, the list of peripheral types, the
list of peripheral instances, and the count of pins per peripheral type.

## 2. Where can a signal go?
> "Which pins can carry `LPUART2_TX` on this package?"

```jsonc
{
  "mcu": "S32K312", "package": "S32K312_172HDQFP",
  "filter": { "signal": "LPUART2_TX" }
}
```
-> Walks every `<pin>` containing an `<assign>` ->
`<peripheral_signal_ref peripheral="LPUART2" signal="lpuart2_tx"/>` and
returns the pin list with a verbatim `<assign>` excerpt each.

## 3. Properties of a specific pin
> "What can I configure on `PTA10`?"

```jsonc
{
  "mcu": "S32K312", "package": "S32K312_172HDQFP",
  "filter": { "pin": "PTA10" }
}
```
-> Returns its `<functional_properties>` (mode, pull, drive strength, slew,
direction, open-drain... with their legal values) and the list of legal
peripheral routings.

## 4. All signals of a peripheral instance
> "Show me everything `LPSPI0` can do on this package."

```jsonc
{
  "mcu": "S32K312", "package": "S32K312_172HDQFP",
  "filter": { "peripheral": "LPSPI0" }
}
```
-> Lists each `LPSPI0` signal (`LPSPI0_SCK`, `LPSPI0_SIN`, ...) with the pins
it can be assigned to.

## 5. Cross-MCU usage
> "Where can `CAN0_TX` go on `S32G274A_257MAPBGA`?"

```jsonc
{
  "mcu": "S32G274A", "platform_sdk": "PlatformSDK_S32G2",
  "package": "S32G274A_257MAPBGA",
  "filter": { "signal": "CAN0_TX" }
}
```
-> Same algorithm; reads
`...\mcu_data\processors\S32G274A\PlatformSDK_S32G2\S32G274A_257MAPBGA\signal_configuration.xml`.
