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

"""
Build the <instance> blocks for the 6 routed drivers, with per-controller
config containers populated from the .component schemas AND the per-package
resource tables (the dynamic_enum value providers).

The emitted XML fragment is written to the path given by --out (see
parse_args at the bottom of this file); nothing is written until the
destination has been resolved and reported.

Validation findings the v1 version missed (now fixed):
  - Spi:   SpiPhyUnit needs SpiPhyUnitMapping = LPSPI_<N> (was: missing)
  - Uart:  UartHwUsing is the constant LPUART_IP; the per-channel module
           number goes in UartHwChannel = LPUART_<N>, which lives inside
           DetailModuleConfiguration (was: LPUART<N> in UartHwUsing)
  - Lin:   LinHwChannel = LPUART_IP_<N> from RTD/Lin.xml
  - Adc:   AdcHwUnitId = ADC0/ADC1 (was: missing); AdcChannelId is a bare
           numeric id matching ChanNum and AdcChannelName is the verbatim
           resource-table value P<N>_ChanNum<N> (was: AN_<N>); AdcGroupId
           must be unique across all units; AdcGroupDefinition must
           cross-reference the channel container.
  - Pwm:   PwmPeriodDefault as ticks must be <= 65534 (was: 1 second's worth
           of ticks at 120 MHz); set PwmPeriodInTicks=true so the value is
           taken verbatim.
  - Can:   CanControllerHwChannel does not exist; the FlexCAN module is
           selected via CanHwChannel = FLEXCAN_<N>. CanControllerId must be
           sequential (it is the array index). Each CanController needs at
           least one CanControllerBaudrateConfig and one CanHwObject with
           at least one CanHwFilter.

All names are case-sensitive and copied verbatim from the resource_tables
files for the S32K312_172HDQFP package.
"""
import argparse
import sys
import uuid
from pathlib import Path

INDENT = "                  "  # 18 spaces - matches existing siblings under <instances>
I2 = INDENT + "   "             # 21
I3 = I2 + "   "                 # 24
I4 = I3 + "   "                 # 27
I5 = I4 + "   "                 # 30
I6 = I5 + "   "                 # 33
I7 = I6 + "   "                 # 36
I8 = I7 + "   "                 # 39

def U(): return str(uuid.uuid4())

def setting(name, value, indent=I3):
    return [f'{indent}<setting name="{name}" value="{value}"/>']

def struct_open(name, indent=I3, quick_selection=None):
    qs = f' quick_selection="{quick_selection}"' if quick_selection else ""
    return [f'{indent}<struct name="{name}"{qs}>']

def struct_close(indent=I3):
    return [f'{indent}</struct>']

def array_open(name, indent=I3):
    return [f'{indent}<array name="{name}">']

def array_empty(name, indent=I3):
    return [f'{indent}<array name="{name}"/>']

def array_close(indent=I3):
    return [f'{indent}</array>']

def array_elem_open(idx, indent=I4):
    return [f'{indent}<struct name="{idx}">']

def array_elem_close(indent=I4):
    return [f'{indent}</struct>']

def instance_open(name, type_, type_id, mode, indent=INDENT):
    return [(
        f'{indent}<instance name="{name}" uuid="{U()}" type="{type_}" type_id="{type_id}"'
        f' mode="{mode}" enabled="true" comment="" custom_name_enabled="false" editing_lock="false">'
    )]

def instance_close(indent=INDENT):
    return [f'{indent}</instance>']

def config_set_open(name, indent=I2):
    return [f'{indent}<config_set name="{name}">']

def config_set_close(indent=I2):
    return [f'{indent}</config_set>']

def common_published_info(module_id, vendor_api_infix="",
                          ar_minor="9", sw_major="7", sw_minor="0", sw_patch="1"):
    """Emit the CommonPublishedInformation struct that every AUTOSAR driver
    needs. Missing this triggers 'Name must be a valid C identifier'."""
    L = []
    L += struct_open("CommonPublishedInformation")
    L += setting("Name", "CommonPublishedInformation", I4)
    L += setting("ModuleId", str(module_id), I4)
    L += setting("VendorId", "43", I4)
    L += setting("VendorApiInfix", vendor_api_infix, I4)
    L += setting("ArReleaseMajorVersion", "4", I4)
    L += setting("ArReleaseMinorVersion", ar_minor, I4)
    L += setting("ArReleaseRevisionVersion", "0", I4)
    L += setting("SwMajorVersion", sw_major, I4)
    L += setting("SwMinorVersion", sw_minor, I4)
    L += setting("SwPatchVersion", sw_patch, I4)
    L += struct_close(I3)
    return L

# ============================================================================
# 1) Spi - LPSPI0 + LPSPI1
# ============================================================================
def build_spi():
    L = []
    L += instance_open("Spi", "Spi", "Spi", "autosar")
    L += config_set_open("Spi")
    L += setting("Name", "Spi")

    L += struct_open("ConfigTimeSupport")
    L += setting("POST_BUILD_VARIANT_USED", "false", I4)
    L += setting("IMPLEMENTATION_CONFIG_VARIANT", "VARIANT-PRE-COMPILE", I4)
    L += struct_close(I3)

    L += struct_open("SpiGeneral")
    L += setting("Name", "SpiGeneral", I4)
    L += setting("SpiTimeoutMethod", "OSIF_COUNTER_DUMMY", I4)
    L += setting("SpiDevErrorDetect", "false", I4)
    L += setting("SpiCancelApi", "true", I4)
    L += setting("SpiHwStatusApi", "true", I4)
    L += setting("SpiInterruptibleSeqAllowed", "false", I4)
    L += setting("SpiLevelDelivered", "2", I4)
    L += setting("SpiSupportConcurrentSyncTransmit", "false", I4)
    L += setting("SpiVersionInfoApi", "true", I4)
    L += setting("SpiGlobalDmaEnable", "false", I4)

    # SpiPhyUnit array - per-controller. SpiPhyUnitMapping is REQUIRED and
    # comes from resource_tables/Spi.xml -> values LPSPI_0..LPSPI_6
    L += array_open("SpiPhyUnit", I4)
    for idx, mapping in enumerate(["LPSPI_0", "LPSPI_1"]):
        L += array_elem_open(str(idx), I5)
        L += setting("Name", f"SpiPhyUnit_{idx}_{mapping}", I6)
        L += setting("SpiPhyUnitMapping", mapping, I6)
        L += setting("SpiPhyUnitMode", "SPI_MASTER", I6)
        L += setting("SpiPhyUnitAsyncUseDma", "false", I6)
        L += array_elem_close(I5)
    L += array_close(I4)
    L += struct_close(I3)

    L += struct_open("SpiDriver")
    L += setting("Name", "SpiDriver", I4)
    L += struct_close(I3)

    L += struct_open("SpiAutosarExt")
    L += setting("Name", "SpiAutosarExt", I4)
    L += setting("SpiEnableUserModeSupport", "false", I4)
    L += setting("SpiDisableDemReportErrorStatus", "false", I4)
    L += setting("SpiFlexioEnable", "false", I4)
    L += struct_close(I3)

    L += common_published_info(module_id=83)
    L += config_set_close()
    L += instance_close()
    return L


# ============================================================================
# 2) Uart - LPUART6 + LPUART3
# ============================================================================
def build_uart():
    L = []
    L += instance_open("Uart", "Uart", "Uart", "autosar")
    L += config_set_open("Uart")
    L += setting("Name", "Uart")

    L += struct_open("ConfigTimeSupport")
    L += setting("POST_BUILD_VARIANT_USED", "false", I4)
    L += setting("IMPLEMENTATION_CONFIG_VARIANT", "VARIANT-PRE-COMPILE", I4)
    L += struct_close(I3)

    L += struct_open("GeneralConfiguration")
    L += setting("Name", "GeneralConfiguration", I4)
    L += setting("UartDevErrorDetect", "true", I4)
    L += setting("UartDmaEnable", "false", I4)
    L += struct_close(I3)

    L += struct_open("UartGlobalConfig")
    L += setting("Name", "UartGlobalConfig", I4)
    L += array_open("UartChannel", I4)
    # From K344 reference example:
    #   UartHwUsing = LPUART_IP (or FLEXIO_IP)
    #   UartHwChannel = LPUART_<N> (lives INSIDE DetailModuleConfiguration)
    #   UartInteruptDmaMethod = LPUART_UART_IP_USING_INTERRUPTS
    for idx, hwc in enumerate(["LPUART_6", "LPUART_3"]):
        L += array_elem_open(str(idx), I5)
        L += setting("Name", f"UartChannel_{idx}_{hwc}", I6)
        L += setting("UartHwUsing", "LPUART_IP", I6)
        L += setting("UartChannelId", str(idx), I6)
        L += array_empty("UartChannelEcucPartitionRef", I6)
        L += struct_open("DetailModuleConfiguration", I6)
        L += setting("Name", "DetailModuleConfiguration", I7)
        L += setting("UartHwChannel", hwc, I7)
        L += setting("DesireBaudrate", "LPUART_UART_BAUDRATE_115200", I7)
        L += setting("UartInteruptDmaMethod", "LPUART_UART_IP_USING_INTERRUPTS", I7)
        L += array_empty("UartDmaTxChannelRef", I7)
        L += array_empty("UartDmaRxChannelRef", I7)
        L += setting("UartParityType", "LPUART_UART_IP_PARITY_DISABLED", I7)
        L += setting("UartStopBitNumber", "LPUART_UART_IP_ONE_STOP_BIT", I7)
        L += setting("UartWordLength", "LPUART_UART_IP_8_BITS_PER_CHAR", I7)
        L += setting("UartInternalLoopbackEnable", "false", I7)
        L += setting("UartTimeoutEnable", "false", I7)
        L += struct_close(I6)
        L += array_elem_close(I5)
    L += array_close(I4)
    L += struct_close(I3)

    L += common_published_info(module_id=255)
    L += config_set_close()
    L += instance_close()
    return L


# ============================================================================
# 3) Can_43_FLEXCAN - CAN1 + CAN4
# ============================================================================
def build_can():
    L = []
    L += instance_open("Can_43_FLEXCAN", "Can_43_FLEXCAN", "Can_43_FLEXCAN", "autosar")
    L += config_set_open("Can")
    L += setting("Name", "Can")

    L += struct_open("ConfigTimeSupport")
    L += setting("POST_BUILD_VARIANT_USED", "false", I4)
    L += setting("IMPLEMENTATION_CONFIG_VARIANT", "VARIANT-PRE-COMPILE", I4)
    L += struct_close(I3)

    L += struct_open("CanGeneral")
    L += setting("Name", "CanGeneral", I4)
    L += setting("CanMainFunctionModePeriod", "0.001", I4)
    L += setting("CanTimeoutDuration", "0.01", I4)
    L += setting("CanEnableDualClockMode", "false", I4)
    L += setting("CanGlobalTimeSupport", "false", I4)
    L += array_open("CanMainFunctionRWPeriods", I4)
    L += array_elem_open("0", I5)
    L += setting("Name", "CanMainFunctionRWPeriods_0", I6)
    L += setting("CanMainFunctionPeriod", "0.001", I6)
    L += array_elem_close(I5)
    L += array_close(I4)
    L += struct_close(I3)

    L += struct_open("CanConfigSet")
    L += setting("Name", "CanConfigSet", I4)
    L += array_open("CanController", I4)
    # From K344 reference: per-controller has CanControllerBaseAddress=0,
    # CanControllerId=<N>, CanControllerDefaultBaudrate=path to a baud config.
    controller_names = []
    # CanControllerId MUST be sequential (0, 1, ..., N-1) - it's the array index,
    # not the FlexCAN module number. The FlexCAN module is picked via CanHwChannel
    # (NOT CanControllerHwChannel which doesn't exist). Use FLEXCAN_1, FLEXCAN_4.
    for idx, fc in enumerate(["FLEXCAN_1", "FLEXCAN_4"]):
        ctrl_name = f"CanController_{idx}"
        controller_names.append(ctrl_name)
        L += array_elem_open(str(idx), I5)
        L += setting("Name", ctrl_name, I6)
        L += setting("CanHwChannel", fc, I6)
        L += setting("CanControllerBaseAddress", "0", I6)
        L += setting("CanControllerId", str(idx), I6)
        L += setting("CanControllerActivation", "true", I6)
        L += setting("CanRxProcessing", "INTERRUPT", I6)
        L += setting("CanTxProcessing", "POLLING", I6)
        L += setting("CanBusoffProcessing", "POLLING", I6)
        L += setting("CanWakeupProcessing", "POLLING", I6)
        L += setting("CanLoopBackMode", "false", I6)
        L += setting("CanAutoBusOffRecovery", "false", I6)
        L += setting("CanTrippleSamplingEnable", "false", I6)
        L += setting("CanControllerPrExcEn", "false", I6)
        L += setting("CanControllerEdgeFilter", "false", I6)
        L += setting("CanControllerFdISO", "false", I6)
        L += setting("CanLowestBufferTransmittedFirst", "false", I6)
        # Each controller's default-baudrate ref MUST point to a unique
        # baudrate-config instance. Suffix the name with the controller index
        # so the two controllers reference distinct nodes.
        baud_name = f"CanControllerBaudrateConfig_{idx}"
        L += setting("CanControllerDefaultBaudrate",
                     f"/Can_43_FLEXCAN/Can/CanConfigSet/{ctrl_name}/{baud_name}", I6)
        L += array_empty("CanControllerEcucPartitionRef", I6)
        # CanCpuClockRef - required ref to Mcu clock point
        L += setting("CanCpuClockRef",
                     "/Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/McuClockReferencePoint_0", I6)
        L += array_open("CanControllerBaudrateConfig", I6)
        L += array_elem_open("0", I7)
        L += setting("Name", baud_name, I8)
        L += setting("CanBaudrateTypeSuport", "NORMAL_CBT", I8)
        L += setting("CanAdvancedSetting", "false", I8)
        L += setting("CanBusLength", "40", I8)
        L += setting("CanPropDelayTranceiver", "150", I8)
        L += setting("CanTxArbitrationStartDelay", "12", I8)
        L += setting("CanControllerPrescaller", "6", I8)
        L += setting("CanControllerBaudRateConfigID", "0", I8)
        L += setting("CanControllerBaudRate", "500", I8)
        L += setting("CanControllerSyncSeg", "1", I8)
        L += setting("CanControllerPropSeg", "2", I8)
        L += setting("CanControllerSeg1", "3", I8)
        L += setting("CanControllerSeg2", "2", I8)
        L += setting("CanControllerSyncJumpWidth", "1", I8)
        L += array_empty("CanControllerFdBaudrateConfig", I8)
        L += array_elem_close(I7)
        L += array_close(I6)
        L += array_empty("CanRamBlock", I6)
        L += array_empty("CanRxFiFo", I6)
        L += array_empty("CanControllerTimeStamp", I6)
        # Sub-structs that the schema requires (need valid Names):
        L += struct_open("CanPartialNetwork", I6)
        L += setting("Name", "CanPartialNetwork", I7)
        L += setting("CanPnEnabled", "false", I7)
        L += struct_close(I6)
        L += struct_open("CanXLController", I6)
        L += setting("Name", "CanXLController", I7)
        L += struct_close(I6)
        L += array_elem_close(I5)
    L += array_close(I4)
    # CanHardwareObject array - one per controller (each needs CanHwFilter)
    L += array_open("CanHardwareObject", I4)
    for idx, ctrl_name in enumerate(controller_names):
        L += array_elem_open(str(idx), I5)
        L += setting("Name", f"CanHardwareObject_{idx}", I6)
        L += array_empty("CanFdPaddingValue", I6)
        L += setting("CanHandleType", "BASIC", I6)
        L += setting("CanIdType", "STANDARD", I6)
        L += setting("CanObjectId", str(idx), I6)
        L += setting("CanObjectType", "RECEIVE", I6)
        L += array_empty("CanObjectPayloadLength", I6)
        L += array_empty("CanHardwareObjectUsesPolling", I6)
        L += array_empty("CanTriggerTransmitEnable", I6)
        L += setting("CanControllerRef",
                     f"/Can_43_FLEXCAN/Can/CanConfigSet/{ctrl_name}", I6)
        L += array_empty("CanMainFunctionRWPeriodRef", I6)
        L += array_empty("CanHwObjectUsesBlock", I6)
        L += setting("CanHwObjectCount", "1", I6)
        L += array_open("CanHwFilter", I6)
        L += array_elem_open("0", I7)
        L += setting("Name", f"Can_aHwFilter_Object_{idx}", I8)
        L += setting("CanHwFilterCode", "0", I8)
        L += setting("CanHwFilterMask", "0", I8)
        L += setting("CanHwFilterIDE", "false", I8)
        L += array_elem_close(I7)
        L += array_close(I6)
        L += array_elem_close(I5)
    L += array_close(I4)
    L += struct_close(I3)

    L += common_published_info(module_id=80, vendor_api_infix="FLEXCAN")
    L += config_set_close()
    L += instance_close()
    return L


# ============================================================================
# 4) Lin_43_LPUART_FLEXIO - LPUART5 (LIN1) + LPUART2 (LIN2)
# ============================================================================
def build_lin():
    L = []
    L += instance_open("Lin_43_LPUART_FLEXIO", "Lin_43_LPUART_FLEXIO", "Lin_43_LPUART_FLEXIO", "autosar")
    L += config_set_open("Lin")
    L += setting("Name", "Lin")

    L += struct_open("ConfigTimeSupport")
    L += setting("POST_BUILD_VARIANT_USED", "false", I4)
    L += setting("IMPLEMENTATION_CONFIG_VARIANT", "VARIANT-PRE-COMPILE", I4)
    L += struct_close(I3)

    L += struct_open("LinGeneral")
    L += setting("Name", "LinGeneral", I4)
    L += setting("LinTimeoutDuration", "65535", I4)
    L += setting("LinDevErrorDetect", "false", I4)
    L += struct_close(I3)

    L += struct_open("AutosarExt")
    L += setting("Name", "AutosarExt", I4)
    L += setting("LinFrameTimeoutDisable", "true", I4)
    L += setting("LinDmaEnable", "false", I4)
    L += struct_close(I3)

    L += struct_open("LinGlobalConfig")
    L += setting("Name", "LinGlobalConfig_0", I4)
    L += array_open("LinChannel", I4)
    # From K344 reference example, the exact enum values are:
    #   LinNodeType = MASTER (not LIN_MASTER_NODE)
    #   BreakLength = BL_13, DetectedBreakLength = BL_11
    #   LinInteruptDmaMethod = LIN_IP_USING_INTERRUPTS
    #   LinClockRef cross-ref to LPUART_CLK (point at Mcu)
    for idx, (label, hw) in enumerate([
            ("LPUART_5", "LPUART_IP_5"),   # LIN1 -> TJA1022 LIN2 on PTB27/PTB28
            ("LPUART_2", "LPUART_IP_2"),   # LIN2 -> Arduino header
        ]):
        L += array_elem_open(str(idx), I5)
        L += setting("Name", f"LinChannel_{idx}_{label}", I6)
        L += setting("LinChannelId", str(idx), I6)
        L += setting("LinNodeType", "MASTER", I6)
        L += setting("LinChannelBaudRate", "19200", I6)
        L += setting("BreakLength", "BL_13", I6)
        L += setting("DetectedBreakLength", "BL_11", I6)
        L += setting("LinResponseTimeout", "14", I6)
        L += setting("LinHeaderTimeout", "44", I6)
        L += setting("LinHwChannel", hw, I6)
        # LinClockRef requires a McuClockReferencePoint that exists in the .mex.
        # The bundled template only has McuClockReferencePoint_0, so target that.
        L += setting("LinClockRef",
                     "/Mcu/Mcu/McuModuleConfiguration/McuClockSettingConfig_0/McuClockReferencePoint_0", I6)
        L += array_empty("LinClockRef_Alternate", I6)
        L += setting("LinChannelWakeupSupport", "false", I6)
        L += array_empty("LinChannelEcuMWakeupSource", I6)
        L += array_empty("LinChannelEcucPartitionRef", I6)
        L += setting("LinInteruptDmaMethod", "LIN_IP_USING_INTERRUPTS", I6)
        L += array_empty("LinDmaRxChannelRef", I6)
        L += array_empty("LinFlexioRxControllerRef", I6)
        L += array_empty("LinFlexioTxControllerRef", I6)
        L += array_elem_close(I5)
    L += array_close(I4)
    L += struct_close(I3)

    L += common_published_info(module_id=82, vendor_api_infix="LPUART_FLEXIO")
    L += config_set_close()
    L += instance_close()
    return L


# ============================================================================
# 5) Adc - ADC0 (channel AN_1 = PTD0) + ADC1 (channel AN_1 = PTA13)
# ============================================================================
def build_adc():
    L = []
    L += instance_open("Adc", "Adc", "Adc", "autosar")
    L += config_set_open("Adc")
    L += setting("Name", "Adc")

    L += struct_open("ConfigTimeSupport")
    L += setting("POST_BUILD_VARIANT_USED", "false", I4)
    L += setting("IMPLEMENTATION_CONFIG_VARIANT", "VARIANT-PRE-COMPILE", I4)
    L += struct_close(I3)

    L += struct_open("AdcGeneral")
    L += setting("Name", "AdcGeneral", I4)
    L += setting("AdcDeInitApi", "true", I4)
    L += setting("AdcDevErrorDetect", "false", I4)
    L += setting("AdcEnableLimitCheck", "true", I4)
    L += setting("AdcEnableQueuing", "true", I4)
    L += setting("AdcEnableStartStopGroupApi", "true", I4)
    L += setting("AdcGrpNotifCapability", "true", I4)
    L += setting("AdcPriorityImplementation", "ADC_PRIORITY_NONE", I4)
    L += setting("AdcResultAlignment", "ADC_ALIGN_RIGHT", I4)
    L += setting("AdcReadGroupApi", "true", I4)
    L += setting("AdcVersionInfoApi", "true", I4)
    L += struct_close(I3)

    L += struct_open("AutosarExt")
    L += setting("Name", "AutosarExt", I4)
    L += setting("AdcSarEnable", "true", I4)
    L += setting("AdcTimeoutVal", "100000", I4)
    L += setting("AdcEnableUserModeSupport", "false", I4)
    L += setting("AdcPreSamplingOnce", "true", I4)
    L += setting("AdcSarTempSenseVsupply", "53", I4)
    L += struct_close(I3)

    L += struct_open("AdcConfigSet")
    L += setting("Name", "AdcConfigSet", I4)
    L += array_open("AdcHwUnit", I4)
    # group_id must be GLOBALLY unique across all HwUnits (not per-unit).
    # logical_unit_id must also be unique. Use a running counter for both.
    group_counter = 0
    # ADC0_P1 (PTD0) and ADC1_P1 (PTA13). Channel name format from resource table:
    # P<N>_ChanNum<N>. AdcChannelId = logical id; AdcLogicalChannelId = group offset.
    for idx, (hw, ch_phys, ch_id) in enumerate([
            ("ADC0", "P1_ChanNum1", 1),
            ("ADC1", "P1_ChanNum1", 1)]):
        unit_name = f"AdcHwUnit_{idx}_{hw}"
        ch_full_name = f"AdcChannel_0_{hw}_P{ch_id}"
        L += array_elem_open(str(idx), I5)
        L += setting("Name", unit_name, I6)
        L += setting("AdcHwUnitId", hw, I6)
        L += setting("AdcLogicalUnitId", str(idx), I6)
        L += setting("AdcAltPrescale", "2", I6)
        L += setting("AdcCalibrationPrescale", "2", I6)
        # AdcChannel array (min_expr=1)
        L += array_open("AdcChannel", I6)
        L += array_elem_open("0", I7)
        L += setting("Name", ch_full_name, I8)
        L += setting("AdcChannelId", str(ch_id), I8)        # numeric id matching ChanNum
        L += setting("AdcChannelName", ch_phys, I8)         # exact value from resource table
        L += setting("AdcLogicalChannelId", "0", I8)
        L += setting("AdcEnablePresampling", "false", I8)
        L += setting("AdcEnableThresholds", "false", I8)
        L += array_elem_close(I7)
        L += array_close(I6)
        # AdcGroup array (min_expr=1) - unique GroupId globally
        L += array_open("AdcGroup", I6)
        L += array_elem_open("0", I7)
        L += setting("Name", f"AdcGroup_{group_counter}_{hw}", I8)
        L += setting("AdcGroupId", str(group_counter), I8)
        L += setting("AdcGroupAccessMode", "ADC_ACCESS_MODE_SINGLE", I8)
        L += setting("AdcGroupConversionMode", "ADC_CONV_MODE_ONESHOT", I8)
        L += setting("AdcGroupConversionType", "ADC_CONV_TYPE_NORMAL", I8)
        L += setting("AdcGroupTriggSrc", "ADC_TRIGG_SRC_SW", I8)
        L += setting("AdcStreamingBufferMode", "ADC_STREAM_BUFFER_LINEAR", I8)
        L += setting("AdcEnableHalfInterrupt", "false", I8)
        L += setting("AdcStreamingNumSamples", "1", I8)
        L += setting("AdcStreamResultGroup", "false", I8)
        L += setting("AdcEnableChDisableChGroup", "false", I8)
        L += setting("AdcWithoutInterrupts", "false", I8)
        L += setting("AdcWithoutDma", "false", I8)
        L += setting("AdcExtDMAChanEnable", "false", I8)
        # AdcGroupConversionConfiguration sub-struct (required, must have valid Name)
        L += struct_open("AdcGroupConversionConfiguration", I8)
        L += setting("Name", "AdcGroupConversionConfiguration", I8 + "   ")
        L += setting("AdcGroupHardwareAverageEnable", "false", I8 + "   ")
        L += setting("AdcSamplingDuration0", "22", I8 + "   ")
        L += setting("AdcSamplingDuration1", "12", I8 + "   ")
        L += struct_close(I8)
        # AdcAlternateGroupConvTimings sub-struct (required, must have valid Name)
        L += struct_open("AdcAlternateGroupConvTimings", I8)
        L += setting("Name", "AdcAlternateGroupConvTimings", I8 + "   ")
        L += setting("AdcGroupAltHardwareAverageEnable", "false", I8 + "   ")
        L += setting("AdcAltGroupSamplingDuration0", "11", I8 + "   ")
        L += setting("AdcAltGroupSamplingDuration1", "14", I8 + "   ")
        L += struct_close(I8)
        # AdcGroupDefinition - ref-array. <setting name="N" value="path"/>
        L += array_open("AdcGroupDefinition", I8)
        L += setting("0", f"/Adc/Adc/AdcConfigSet/{unit_name}/{ch_full_name}",
                     I8 + "   ")
        L += array_close(I8)
        L += array_empty("AdcGroupEcucPartitionRef", I8)
        L += array_elem_close(I7)
        L += array_close(I6)
        L += array_elem_close(I5)
        group_counter += 1
    L += array_close(I4)
    # AdcHwTrigger and BctuHwUnit arrays - leave empty so the validator
    # doesn't auto-create placeholder elements with empty Names.
    L += array_empty("AdcHwTrigger", I4)
    L += array_empty("BctuHwUnit", I4)
    # Close AdcConfigSet struct
    L += struct_close(I3)

    # AdcHwConfiguration - top-level array directly under <config_set name="Adc">
    L += array_open("AdcHwConfiguration", I3)
    for idx, hw in enumerate(["ADC0", "ADC1"]):
        L += array_elem_open(str(idx), I4)
        L += setting("Name", f"AdcHwConfiguration_{idx}", I5)
        L += setting("AdcHwConfiguredId", hw, I5)
        L += setting("AdcNormalInterruptEnable", "true", I5)
        L += setting("AdcInjectedInterruptEnable", "false", I5)
        L += setting("AdcFifoFullInterruptEnable", "false", I5)
        L += setting("CtuFifoOfInterruptEnable", "false", I5)
        L += setting("WdgThresholdEnable", "false", I5)
        L += setting("DmaTransferEnable", "false", I5)
        L += array_elem_close(I4)
    L += array_close(I3)

    # AdcPublishedInformation - required published info container
    L += struct_open("AdcPublishedInformation")
    L += setting("Name", "AdcPublishedInformation", I4)
    L += struct_close(I3)

    L += common_published_info(module_id=123)
    L += config_set_close()
    L += instance_close()
    return L


# ============================================================================
# 6) Pwm - single eMIOS_0 channel 4 (PTB4). Period in TICKS, value < 65535.
# ============================================================================
def build_pwm():
    L = []
    L += instance_open("Pwm", "Pwm", "Pwm", "autosar")
    L += config_set_open("Pwm")
    L += setting("Name", "Pwm")

    L += struct_open("ConfigTimeSupport")
    L += setting("POST_BUILD_VARIANT_USED", "true", I4)
    L += setting("IMPLEMENTATION_CONFIG_VARIANT", "VARIANT-POST-BUILD", I4)
    L += struct_close(I3)

    L += struct_open("PwmGeneral")
    L += setting("Name", "PwmGeneral", I4)
    L += setting("PwmMultipartitionEnabled", "false", I4)
    L += setting("PwmDevErrorDetect", "true", I4)
    L += setting("PwmDutycycleUpdatedEndperiod", "false", I4)
    L += setting("PwmPeriodUpdatedEndperiod", "false", I4)
    L += setting("PwmNotificationSupported", "false", I4)
    L += setting("PwmFaultNotificationSupported", "false", I4)
    L += setting("PwmEnableUserModeSupport", "false", I4)
    L += setting("PwmEnableDualClockMode", "false", I4)
    L += setting("PwmMultiChannelSync", "false", I4)
    L += setting("PwmIndex", "0", I4)
    L += struct_close(I3)

    L += struct_open("PwmChannelConfigSet")
    L += setting("Name", "PwmChannelConfigSet", I4)
    L += array_open("PwmChannel", I4)
    L += array_elem_open("0", I5)
    L += setting("Name", "PwmChannel_0", I6)
    # PERIOD must fit in uint16 (<=65534). Configure in ticks.
    L += setting("PwmPeriodInTicks", "true", I6)
    L += setting("PwmPeriodDefault", "60000", I6)     # ticks
    L += setting("PwmDutycycleDefault", "16384", I6)  # 25% of 0x8000 fixed-point
    L += setting("PwmPolarity", "PWM_HIGH", I6)
    L += setting("PwmIdleState", "PWM_LOW", I6)
    L += array_elem_close(I5)
    L += array_close(I4)
    # PwmEmios array
    L += array_open("PwmEmios", I4)
    L += array_elem_open("0", I5)
    L += setting("Name", "PwmEmios_0", I6)
    L += array_open("PwmEmiosChannels", I6)
    L += array_elem_open("0", I7)
    L += setting("Name", "PwmEmiosChannels_0_CH4", I8)
    L += setting("EmiosChCounterBus", "EMIOS_PWM_IP_BUS_INTERNAL", I8)
    L += setting("EmiosChFreeze", "false", I8)
    L += array_elem_close(I7)
    L += array_close(I6)
    L += array_elem_close(I5)
    L += array_close(I4)
    L += struct_close(I3)

    L += struct_open("PwmConfigurationOfOptApiServices")
    L += setting("Name", "PwmConfigurationOfOptApiServices", I4)
    L += setting("PwmDeInitApi", "true", I4)
    L += setting("PwmGetOutputState", "false", I4)
    L += setting("PwmSetDutyCycle", "true", I4)
    L += setting("PwmSetOutputToIdle", "false", I4)
    L += setting("PwmSetPeriodAndDuty", "false", I4)
    L += setting("PwmVersionInfoApi", "false", I4)
    L += setting("PwmGetChannelStateApi", "false", I4)
    L += struct_close(I3)

    L += common_published_info(module_id=121)
    L += config_set_close()
    L += instance_close()
    return L


# ============================================================================
# Emit
# ============================================================================
out = []
out += [INDENT + "<!-- ============================================================ -->"]
out += [INDENT + "<!-- Per-controller driver configuration (v2 - validator-driven)  -->"]
out += [INDENT + "<!-- All enum values verified against resource_tables/*.xml         -->"]
out += [INDENT + "<!-- Spi: LPSPI0+LPSPI1 (SpiPhyUnitMapping=LPSPI_0/_1)              -->"]
out += [INDENT + "<!-- Uart: LPUART6+LPUART3 (UartHwChannel=LPUART_6/_3)              -->"]
out += [INDENT + "<!-- Can: CAN1+CAN4 (CanHwChannel=FLEXCAN_1/_4)                     -->"]
out += [INDENT + "<!-- Adc: ADC0+ADC1 (AdcHwUnitId=ADC0/ADC1,                         -->"]
out += [INDENT + "<!--      AdcChannelName=P1_ChanNum1)                               -->"]
out += [INDENT + "<!-- Lin: LPUART5+LPUART2 (LinHwChannel=LPUART_IP_5/_2)             -->"]
out += [INDENT + "<!-- Pwm: eMIOS_0 CH4, period 60000 ticks (<=65534)                   -->"]
out += [INDENT + "<!-- ============================================================ -->"]
out += build_spi()
out += build_uart()
out += build_can()
out += build_lin()
out += build_adc()
out += build_pwm()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Emit the peripherals <instance> block fragment for the routed "
            "drivers to an XML file."
        ),
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Destination path for the generated peripherals block XML fragment.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the destination if it already exists.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    destination = args.out

    if destination.exists() and not args.force:
        print(
            f"error: {destination} already exists. Re-run with --force to "
            f"overwrite it.",
            file=sys.stderr,
        )
        return 1

    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(out)
    print(f"Destination : {destination}")
    if destination.exists():
        print("Note        : existing file will be overwritten (--force)")
    destination.write_text(payload, encoding="utf-8")
    print(f"Wrote {len(out)} lines ({len(payload)} bytes) to {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
