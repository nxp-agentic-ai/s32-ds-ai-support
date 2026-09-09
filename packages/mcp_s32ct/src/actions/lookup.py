# Copyright 2026 NXP
#
# NXP Proprietary. This software is owned or controlled by NXP and may
# only be used strictly in accordance with the applicable license terms.
# By expressly accepting such terms or by downloading, installing,
# activating and/or otherwise using the software, you are agreeing that
# you have read, and that you agree to comply with and are bound by,
# such license terms.  If you do not agree to be bound by the applicable
# license terms, then you may not retain, install, activate or otherwise
# use the software.

"""``s32ct.lookup_*`` - allowed-value queries against the MCU data package.

These four actions answer "what values are legal here?" by reading the XML
resource tables that ship with the S32CT MCU data package. They are the
counterpart to the inspect actions: inspect tells you what a project currently
contains, lookup tells you what it is permitted to contain.

Use them before writing a ``set_values`` assignment so the value is known-good
rather than guessed. All four are read-only and never invoke the launcher.
"""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter

from nxp.mcp.s32ct.actions import _params as P
from nxp.mcp.s32ct.handlers import action_handlers

_MCU = ActionParameter(
    name="mcu",
    required=True,
    schema={
        "type": "string",
        "description": "MCU part name, for example S32K344.",
    },
)

_PACKAGE = ActionParameter(
    name="package",
    required=True,
    schema={
        "type": "string",
        "description": (
            "Package / pin-count variant of the MCU, for example "
            "S32K344_172HDQFP. Determines which pins physically exist."
        ),
    },
)

_PLATFORM_SDK = ActionParameter(
    name="platform_sdk",
    required=False,
    schema={
        "type": "string",
        "description": (
            "Override the PlatformSDK_* folder under the MCU directory. "
            "Auto-detected when omitted."
        ),
    },
)

_DRIVER = ActionParameter(
    name="driver",
    required=True,
    schema={
        "type": "string",
        "description": (
            "Driver name as it appears in the resource tables, for example Can, "
            "Adc, Pwm or Uart. Discover valid names with s32ct.lookup_drivers."
        ),
    },
)


LOOKUP_PIN_SIGNAL_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.lookup_pin_signal",
        description=(
            "List the pins that can legally carry a given peripheral signal on "
            "a specific MCU package, read from signal_configuration.xml. Use "
            "this before routing a signal so you pick a pin the silicon "
            "actually supports - for example which pins can serve as "
            "LPUART0 TX on an S32K344 172-pin package. Read-only. Returns "
            "{kind, mcu, package, result, source}."
        ),
        params=(
            _MCU,
            _PACKAGE,
            ActionParameter(
                name="peripheral",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Peripheral instance name, for example LPUART0 or "
                        "FlexCAN0."
                    ),
                },
            ),
            ActionParameter(
                name="signal",
                required=True,
                schema={
                    "type": "string",
                    "description": "Signal name on that peripheral, for example TX or RX.",
                },
            ),
            _PLATFORM_SDK,
            P.MCU_DATA_ROOT,
        ),
        preconditions=(
            "The MCU data package for this mcu and package must be installed.",
        ),
        workflow_hints=(
            "Feed the chosen pin into s32ct.configure_pins via set_values.",
        ),
        related_actions=("s32ct.configure_pins", "s32ct.inspect_pins"),
        category="lookup",
    ),
    handler=action_handlers.lookup_pin_signal,
)


LOOKUP_ENUM_VALUES_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.lookup_enum_values",
        description=(
            "List the legal values for one dotted array path of a driver, read "
            "from the driver's XML resource table. This is how you find out "
            "exactly what a setting will accept before assigning it - for "
            "example the permitted CanHwChannel values for the Can driver via "
            "array_path=CanConfigSet.CanHwChannelList. Discover valid array_path "
            "values with s32ct.lookup_arrays. Read-only. Returns "
            "{kind, mcu, package, result, source}."
        ),
        params=(
            _MCU,
            _PACKAGE,
            _DRIVER,
            ActionParameter(
                name="array_path",
                required=True,
                schema={
                    "type": "string",
                    "description": (
                        "Dotted path to the array inside the driver's resource "
                        "table, for example CanConfigSet.CanHwChannelList. List "
                        "the available paths with s32ct.lookup_arrays."
                    ),
                },
            ),
            _PLATFORM_SDK,
            P.MCU_DATA_ROOT,
        ),
        preconditions=(
            "The MCU data package for this mcu and package must be installed.",
            "driver must have a resource table on this package; check with "
            "s32ct.lookup_drivers.",
        ),
        workflow_hints=(
            "Call s32ct.lookup_arrays first to learn the dotted paths a driver "
            "exposes.",
            "Assign the chosen value with a configure action's set_values.",
        ),
        related_actions=(
            "s32ct.lookup_arrays",
            "s32ct.lookup_drivers",
            "s32ct.configure_peripherals",
        ),
        category="lookup",
    ),
    handler=action_handlers.lookup_enum_values,
)


LOOKUP_ARRAYS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.lookup_arrays",
        description=(
            "List every dotted array path a driver exposes in its resource "
            "table. This is the discovery step that tells you which array_path "
            "values s32ct.lookup_enum_values will accept for this driver. "
            "Read-only. Returns {kind, mcu, package, result, source}."
        ),
        params=(_MCU, _PACKAGE, _DRIVER, _PLATFORM_SDK, P.MCU_DATA_ROOT),
        preconditions=(
            "The MCU data package for this mcu and package must be installed.",
            "driver must have a resource table on this package; check with "
            "s32ct.lookup_drivers.",
        ),
        workflow_hints=(
            "Follow up with s32ct.lookup_enum_values on the path you care about.",
        ),
        related_actions=("s32ct.lookup_enum_values", "s32ct.lookup_drivers"),
        category="lookup",
    ),
    handler=action_handlers.lookup_arrays,
)


LOOKUP_DRIVERS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.lookup_drivers",
        description=(
            "List every driver that has a resource table for a given MCU "
            "package. Start here when you do not yet know the exact driver name "
            "to pass to s32ct.lookup_arrays or s32ct.lookup_enum_values, or to "
            "confirm a driver is supported on this part at all. Read-only. "
            "Returns {kind, mcu, package, result, source}."
        ),
        params=(_MCU, _PACKAGE, _PLATFORM_SDK, P.MCU_DATA_ROOT),
        preconditions=(
            "The MCU data package for this mcu and package must be installed.",
        ),
        workflow_hints=(
            "This is the entry point of the lookup chain: drivers -> arrays -> "
            "enum_values.",
        ),
        related_actions=("s32ct.lookup_arrays", "s32ct.lookup_enum_values"),
        category="lookup",
    ),
    handler=action_handlers.lookup_drivers,
)


LOOKUP_MCUS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.lookup_mcus",
        description=(
            "List every MCU part supported by the installed S32CT MCU data "
            "package, read from the processors/ folder. This is the top of the "
            "discovery chain: run it when you do not yet know the exact mcu "
            "value to pass to a configure, gtm or lookup action - for example "
            "to answer 'which MCUs are available' or to confirm a part is "
            "installed at all before bootstrapping an empty configuration. "
            "Read-only; never invokes the launcher. Returns "
            "{kind, result:{mcu_count, mcus}, source}."
        ),
        params=(P.MCU_DATA_ROOT,),
        preconditions=(
            "An MCU data package must be installed; check with s32ct.env_status "
            "if mcu_data_root is empty.",
        ),
        workflow_hints=(
            "Follow up with s32ct.lookup_sdks on a chosen mcu to see its "
            "PlatformSDK_* folders.",
            "The mcu value feeds configure actions (empty_config=true), "
            "s32ct.gtm_create_from_usecase, and the other lookup actions.",
        ),
        related_actions=(
            "s32ct.lookup_sdks",
            "s32ct.lookup_drivers",
            "s32ct.env_status",
        ),
        category="lookup",
    ),
    handler=action_handlers.lookup_mcus,
)


LOOKUP_SDKS_ACTION = ActionExecutable(
    contract=ActionContract(
        name="s32ct.lookup_sdks",
        description=(
            "List the PlatformSDK_* folders installed for one MCU, read from "
            "processors/<mcu>/. Use this after s32ct.lookup_mcus to discover "
            "which platform SDK / RTD versions a part supports before binding a "
            "new configuration to one - for example to pick the platform_sdk or "
            "sdk_version for an empty_config bootstrap or "
            "s32ct.gtm_create_from_usecase. Read-only; never invokes the "
            "launcher. Returns {kind, mcu, result:{mcu, sdk_count, sdks}, "
            "source}. Note the returned names are the on-disk folder names "
            "(e.g. PlatformSDK_S32K3); the -SDKVersion string a configure "
            "action expects may differ."
        ),
        params=(_MCU, P.MCU_DATA_ROOT),
        preconditions=(
            "The MCU folder must exist under the data package; check with "
            "s32ct.lookup_mcus.",
        ),
        workflow_hints=(
            "Run s32ct.lookup_mcus first if you do not know the exact mcu name.",
        ),
        related_actions=(
            "s32ct.lookup_mcus",
            "s32ct.lookup_drivers",
            "s32ct.gtm_create_from_usecase",
        ),
        category="lookup",
    ),
    handler=action_handlers.lookup_sdks,
)


LOOKUP_ACTIONS: tuple[ActionExecutable, ...] = (
    LOOKUP_MCUS_ACTION,
    LOOKUP_SDKS_ACTION,
    LOOKUP_PIN_SIGNAL_ACTION,
    LOOKUP_ENUM_VALUES_ACTION,
    LOOKUP_ARRAYS_ACTION,
    LOOKUP_DRIVERS_ACTION,
)


__all__ = [
    "LOOKUP_ACTIONS",
    "LOOKUP_ARRAYS_ACTION",
    "LOOKUP_DRIVERS_ACTION",
    "LOOKUP_ENUM_VALUES_ACTION",
    "LOOKUP_MCUS_ACTION",
    "LOOKUP_PIN_SIGNAL_ACTION",
    "LOOKUP_SDKS_ACTION",
]


