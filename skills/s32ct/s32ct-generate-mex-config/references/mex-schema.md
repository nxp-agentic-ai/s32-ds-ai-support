# `.mex` XML schema notes

Reference details for how S32 Configuration Tools serialises a project
file and which parts must be preserved verbatim when patching.

## Namespace preservation

The `.mex` root carries an `xmlns` attribute of the form
`http://mcuxpresso.nxp.com/XSD/mex_configuration_<N>`, where `<N>` is the
S32CT schema major version. The bundled `S32K312_default.mex` uses
`mex_configuration_19` (S32CT v19). Other templates may declare `_17`,
`_18`, `_20`, ...

Rules:

- Never strip the `xmlns`. S32CT rejects `.mex` files whose namespace has
  been removed.
- Never rewrite `<N>` unless intentionally cross-porting between S32CT
  releases (out of scope here).
- Preserve the exact namespace of the input template on write.

## Top-level anatomy of a template

The bundled `S32K312_default.mex` illustrates the typical structure:

- Processor block: `<processor>S32K312</processor>`, package
  `S32K312_172HDQFP`, MCU data `PlatformSDK_S32K3`, core `M7_0`.
- Tools **enabled** in the template: `Pins` (v17.0), `Clocks` (v19.0),
  `Peripherals` (with 9 pre-wired instances - see below).
- Tools present but **disabled**: `DCD`, `IVT`, `QuadSPI`, `eFUSE`,
  `GTM`, `SERDES`.
- Pre-wired peripheral instances (`type_id` values): `Base`,
  `Siul2_Port`, `Adc`, `Can_43_FLEXCAN`, `Spi`, `Mcu`, `Uart`, `Pwm`,
  `Lin_43_LPUART_FLEXIO`.

Other MCUs will have different pre-wired sets - inspect the template
itself, or use `s32ct-peripherals-author-mex`, to see what is already
there.

## Sidecars

The optional `ClockConfigurationMappings.txt` sits next to the `.mex`.
It carries a `,PB,ClockConfig0` mapping line. When the tool consumes the
`.mex`, this sidecar tells S32CT the name of the clock configuration.
Propagate it alongside the generated `.mex` whenever the template ships
one.

## Element/attribute rules for patching

- `<configuration uuid="...">` at the top level is per-project. Assign a
  fresh UUID v4 when the intent is a distinct project.
- `<part_number>` (package) and `<mcu_data>` are informational identity
  fields inside the template. Cross-check any user-supplied `package` /
  `mcu_data` against these; do not rewrite them (the template must match
  the target install).
- `<pins>`, `<clocks>`, `<peripherals>`, `<dcd>`, `<ivt>`, `<efuse>`,
  `<gtm>`, `<quadspi>`, `<ffc>`, `<serdes>` sections each carry an
  `enabled` attribute. Toggle it to switch tools on/off.
- Peripheral instances live under `<peripherals><periphs><components>`
  as `<instance name="..." type_id="..." uuid="...">` blocks. Removing
  by `name` is the safe operation.
- Parameter overrides for an instance are `<set id="...">value</set>`
  children beneath `<config_set>`. Create the `<set>` node if it doesn't
  exist yet.

## Encoding and formatting

- Encoding is UTF-8, byte-order-mark not required (do not add one).
- Line endings follow the input template - typically CRLF on Windows
  S32CT saves. Preserve on write.
- Whitespace inside text nodes is normalised away by the parser; do not
  invest in pretty-printing beyond matching the template's style.

## Related

- `references/patching-recipes.md` - concrete JSON patch shapes and how
  they map to XML edits.
- `references/adding-new-mcu.md` - procedure for bundling a new
  `<MCU>_default.mex`.
