# Authoring a new peripheral instance in a generated `.mex`

This file is referenced from `SKILL.md` of `s32ct-peripherals-info`.
Although that skill itself is read-only, its output is the canonical input
for **adding a new peripheral to a `.mex` Peripherals-tool configuration**
(typically a `.mex` produced by `s32ct-generate-mex-config`). This document
encodes the authoring rules.

A new peripheral is inserted as an `<instance>` element under:

```
<configuration> -> <tools> -> <peripherals ...>
   -> <functional_groups>
      -> <functional_group name="BOARD_InitPeripherals" ...>
         -> <instances>
            -> <instance ...>
```

The `<instances>` parent already exists in the template; you only add a new
`<instance>...</instance>` sibling.

## Required `<instance>` shape

```xml
<instance name="<user_name>"
          uuid="<fresh-uuid-v4>"
          type="<config_component.id>"
          type_id="<component_folder_name>"
          mode="<mode.id>"
          enabled="true"
          comment=""
          custom_name_enabled="false"
          editing_lock="false">
   <config_set name="<config_set.id>">
      <setting name="Name" value="<user_name>"/>
      <!-- one <setting>, <struct>, or <array> per parameter you want to override;
           the rest fall back to component defaults -->
   </config_set>
</instance>
```

Every attribute on that `<instance>` element comes **directly** from the
peripheral's `.component` file. Use the parent skill (`s32ct-peripherals-info`)
to look the values up  -  never invent them. Inventing values produces a
`.mex` that the S32 Configuration Tools `-ShowProblems` validator will
reject.

## Attribute mapping `.component` -> `.mex`

The peripheral descriptor lives at
`<S32DS_INSTALL>\eclipse\mcu_data\components\<platform_sdk>\<peripheral_folder>\<peripheral_folder>.component`.

| `.mex` attribute | Where to read it from `<peripheral_folder>.component` | Notes |
|---|---|---|
| `type_id` | The **folder name** under `components\<platform_sdk>\` (e.g. `Base`, `Wdg_43_Instance1`, `Can_43_FLEXCAN`, `Lpuart_Uart`). | Case-sensitive. This is what `peripherals.add` accepts as `type_id` in `s32ct-generate-mex-config`. |
| `type` | `<component:config_component id="..." ...>`  -  the **`id`** attribute of the root element. | Often equal to the folder name (`Wdg_43_Instance1`), but **not always** (folder `Base` -> `id="BaseNXP"`). Read it verbatim. |
| `mode` | `<mode id="..." label="..." available="true">`  -  the **`id`** of one of the declared modes. | Common values: `general`, `autosar`, `non_autosar`, `ip`. A component may declare more than one mode; pick the one whose `available="true"` matches the intended use (AUTOSAR vs. non-AUTOSAR vs. IP-only). |
| `name` | Free text  -  the user-chosen instance name. | Must be a valid C identifier (the `Name` `<setting>` enforces this via `isCIdentifier(...)`). Typically equal to `type` or a short alias. |
| `uuid` | Generated. | A fresh **UUID v4**, unique within the `.mex`. Re-using an existing uuid corrupts the project. |
| `enabled` | `true` (normal case) or `false` (declared but skipped during code generation). | |
| `comment` | Free text (often empty). | |
| `custom_name_enabled` | `false` (default)  -  set `true` only if the user renames the instance away from its `type`. | |
| `editing_lock` | `false` (default). | |
| `max_instances` constraint | `<component:config_component ... max_instances="N">`. | Read-only check: the total number of `<instance>` blocks with this `type_id` must not exceed `N`. Many drivers have `max_instances="1"`. |

## Inner `<config_set>` shape

Every `<instance>` contains exactly one `<config_set name="...">`, whose
`name` equals the `<config_set id="...">` attribute in the `.component`
(e.g. `BaseNXP`, `Wdg`, `Mcu`, `Spi`, `Adc`, ...). Inside it:

- `<setting name="<param_id>" value="<param_value>"/>` overrides a scalar
  parameter. Permitted ids and values are exactly those declared under the
  `.component`'s `<settings>` block (`<bool>`, `<enum>`, `<int>`, `<string>`,
  `<float>`, `<dynamic_enum>`). For `<dynamic_enum>` the legal `value` set
  comes from the matching resource table, **not** the `.component`.
- `<struct name="<container_id>"> ...nested settings... </struct>` mirrors a
  `<struct id="...">` container in the `.component`.
- `<array name="<container_id>"/>` (empty) or
  `<array name="<container_id>"><elem index="0">...</elem>...</array>` mirrors a
  `<array id="...">` container.
- `quick_selection="<qs.id>"` on a `<struct>` records that the user picked
  one of the `<quick_selection>` presets declared in the `.component`.

**Defaults are implicit.** Any parameter you do not override falls back to the
`.component`'s default value (sourced from the chosen `<quick_selection>`).
For a minimal new instance you only need to set `Name` plus the few
parameters you actively want to change; everything else is inherited.

## End-to-end example (worked on `PlatformSDK_S32K3`, package `S32K312_172HDQFP`)

Goal: add a new **Wdg** instance based on `Wdg_43_Instance1`.

1. Query the parent skill with `peripheral_name = "Wdg_43_Instance1"`. The
   relevant excerpts of the returned `.component` are:
   ```xml
   <component:config_component id="Wdg_43_Instance1"
                                category="AUTOSAR"
                                max_instances="1">
     ...
     <mode id="autosar" label="AUTOSAR Mode" available="true">
       <config_set_refs><config_set_ref>Wdg</config_set_ref></config_set_refs>
     </mode>
     <config_set id="Wdg" label="Wdg" ...>
       <quick_selection id="WdgDefault" label="Default Values">
         <set id="Name">Wdg</set>
         <set id="WdgGeneral.Name">WdgGeneral</set>
         <set id="WdgGeneral.WdgDevErrorDetect">false</set>
         <set id="WdgGeneral.WdgDisableAllowed">true</set>
         ...
   ```
   Any `<dynamic_enum ref="Wdg...."/>` it contains is resolved against
   `...\<package>\resource_tables\Wdg.xml`.
2. Read off the `<instance>` attributes:
   - `type_id` = `Wdg_43_Instance1`  (folder name)
   - `type`    = `Wdg_43_Instance1`  (`config_component id`)
   - `mode`    = `autosar`           (the only `available="true"` mode)
   - `name`    = `Wdg`               (user-chosen; matches the `Name` default)
   - `uuid`    = a freshly generated UUID v4
3. Insert into the `.mex` under `<instances>` of `BOARD_InitPeripherals`:
   ```xml
   <instance name="Wdg"
             uuid="9b6f4e2c-2a51-4f0e-9e1f-1b9d3a7c5e02"
             type="Wdg_43_Instance1"
             type_id="Wdg_43_Instance1"
             mode="autosar"
             enabled="true"
             comment=""
             custom_name_enabled="false"
             editing_lock="false">
      <config_set name="Wdg">
         <setting name="Name" value="Wdg"/>
         <struct name="WdgGeneral" quick_selection="WdgDefault">
            <setting name="Name" value="WdgGeneral"/>
            <setting name="WdgDevErrorDetect" value="false"/>
            <setting name="WdgDisableAllowed" value="true"/>
         </struct>
      </config_set>
   </instance>
   ```
   Any parameter not listed inherits the `WdgDefault` quick-selection value.

## Mirroring existing instances as templates

When in doubt, the safest authoring strategy is to **copy the closest existing
`<instance>` from a reference `.mex`** (e.g. the bundled `S32K312_default.mex`,
or a freshly generated empty `.mex` for the target MCU) and edit only what
differs. Typical templates available in `S32K312_default.mex`:

| Use case | Copy from `<MCU>_default.mex` (when bundled) |
|---|---|
| Single-mode general / OS-abstraction driver | `<instance name="BaseNXP" ...>` |
| Pin/port driver (IP mode) | `<instance name="Siul2_Port" ...>` |
| Clock / MCU driver (AUTOSAR mode) | `<instance name="Mcu" ...>` |
| ADC | `<instance name="Adc" ...>` |
| FlexCAN | `<instance name="Can_43_FLEXCAN" ...>` |
| LPSPI | `<instance name="Spi" ...>` |
| LPUART / Uart | `<instance name="Uart" ...>` |
| eMIOS PWM | `<instance name="Pwm" ...>` |
| LIN (LPUART/FLEXIO) | `<instance name="Lin_43_LPUART_FLEXIO" ...>` |

Then change only: `name`, `uuid`, and (if the peripheral folder differs)
`type` / `type_id` / `mode`. For non-S32K312 MCUs, generate a one-off
template `.mex` via `s32ct-generate-mex-config` or
`s32ct-cli -EmptyConfig -MCU <mcu> -SDKVersion <rtd> -ExportMEX`.

## Pre-insertion checklist

Before patching a `.mex` with a new `<instance>`, the parent skill should
confirm  -  by quoting the source `.component` (and where applicable the
resource table)  -  that:

1. A `<peripheral_folder>.component` exists for the requested `type_id`
   under `mcu_data\components\<platform_sdk>\`.
2. The chosen `mode` is declared with `available="true"` in that file.
3. The `<config_set name="...">` value matches one of the `<config_set_ref>`
   ids that the chosen mode declares.
4. Every `<setting name="...">` / `<struct name="...">` / `<array name="...">` id
   used inside `<config_set>` exists in the `.component`'s `<settings>` /
   `<struct>` / `<array>` declarations.
5. Every value assigned to a `<dynamic_enum>` setting exists in the matching
   `resource_tables\<Driver>.xml` `<array name="...">` block for the **target
   package**.
6. The new instance does not push the total count of instances of this
   `type_id` above the component's `max_instances` value.

If any check fails, do **not** emit the `<instance>` entry  -  return an
error message that names the offending field and lists the closest legal
alternatives (top-N by Levenshtein distance is usually enough).

## Hand-off

After the `<instance>` entries have been authored:
- Use `s32ct-generate-mex-config` to bake them into a fresh `.mex`
  (pass them under `modifications.peripherals.add` with `type_id`, `mode`,
  `name`; pre-existing instances can be tweaked via
  `modifications.peripherals.patch`), then
- Use `s32ct-peripherals-facade` or `s32ct-generate-code` (`ExportSrc` / `ExportAll`
  on the Peripherals tool) to emit the driver C sources, and
- Use `s32ct-cli` with `-Load <mex> -HeadlessTool Peripherals -ShowProblems`
  to validate the patched `.mex` before code generation. A clean `.mex`
  produces zero problem lines.
