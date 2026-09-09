# s32ct-generate-code - Worked Examples

Concrete scenarios for `nxp_s32ct_execute_action(action_name="s32ct.generate_code", params={...})`.
The `<launcher-prefix>` shown below is the `desktop` form. For the
`integrated_s32ds` form (`s32dsc.exe` + `-data <ws>`), see
`s32ct-distributions`.

## Example 1 - Regenerate only the Pins source code

**Inputs**

```python
nxp_s32ct_execute_action(
    action_name="s32ct.generate_code",
    params={
        "project_path": r"C:/projects/my_motor_ctrl/my_motor_ctrl.mex",
        "tool_name": "Pins",
        "output_dir": r"C:/projects/my_motor_ctrl/board/generated/pins",
        "export_kind": "ExportSrc",
    },
)
```

**Resolved CLI (desktop)**

```
toolsc.exe -noSplash --launcher.ini <tools.ini> ^
  -application com.nxp.swtools.framework.application -consoleLog ^
  -Load "C:\projects\my_motor_ctrl\my_motor_ctrl.mex" ^
  -HeadlessTool Pins -Enable ^
  -ExportSrc "C:\projects\my_motor_ctrl\board\generated\pins"
```

## Example 2 - Full regeneration and export of all Clocks artifacts

**Inputs**

```python
nxp_s32ct_execute_action(
    action_name="s32ct.generate_code",
    params={
        "project_path": r"C:/projects/bldc_demo/bldc_demo.mex",
        "tool_name": "Clocks",
        "output_dir": r"C:/projects/bldc_demo/out/clocks",
        "export_kind": "ExportAll",
        "sdk_version": "s32sdk_s32k3_rtm_402",
    },
)
```

**Resolved CLI (desktop)**

```
toolsc.exe -noSplash --launcher.ini <tools.ini> ^
  -application com.nxp.swtools.framework.application -consoleLog ^
  -Load "C:\projects\bldc_demo\bldc_demo.mex" ^
  -SDKVersion s32sdk_s32k3_rtm_402 ^
  -HeadlessTool Clocks -Enable ^
  -ExportAll "C:\projects\bldc_demo\out\clocks"
```

## Example 3 - Peripherals HTML report only

**Inputs**

```python
nxp_s32ct_execute_action(
    action_name="s32ct.generate_code",
    params={
        "project_path": r"C:/projects/x/x.mex",
        "tool_name": "Peripherals",
        "output_dir": r"C:/projects/x/out/peripherals",
        "export_kind": "ExportHTML",
    },
)
```

Adds `-HeadlessTool Peripherals -Enable -ExportHTML "<output_dir>"` to
the tail.

## Notes

- `ExportAll` is a superset of `ExportSrc` + `ExportHTML` + tool-specific
  exports (`ExportCSV` for Pins, `ExportRegisters` for Clocks, ...). Use
  `ExportSrc` when only source code is needed.
- A successful return confirms *generation*, not *compilation*.
- If the project pins an SDK, always pass `sdk_version=` - otherwise the
  run may fail at `-Load` time.
- To regenerate several tools, call the skill multiple times. S32CT does
  accept chained `-HeadlessTool` blocks separated by `;`, but this skill
  stays scoped for predictability and clearer failure modes.
