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

"""Dump enum allowed values and required (lower bound > 0 array) fields for the
specific schema points that the validator complained about."""
import xml.etree.ElementTree as ET
import re, sys
from pathlib import Path

ROOT = Path(r"C:\NXP\S32DS.3.6.6\eclipse\mcu_data\components\PlatformSDK_S32K3")
def strip_ns(t): return re.sub(r"\{[^}]+\}", "", t)

# What I want to discover for each driver
queries = {
    "Spi": ["SpiPhyUnitMapping", "SpiPhyUnit"],
    "Uart": ["UartHwChannel", "DesireBaudrate", "UartInteruptDmaMethod"],
    "Can_43_FLEXCAN": ["CanControllerHwChannel", "CanControllerBaudRate", "CanController", "CanHwObject", "CanHwFilter", "CanControllerRef"],
    "Lin_43_LPUART_FLEXIO": ["LinChannelId", "LinHwChannel", "LinChannel"],
    "Adc": ["AdcHwUnitId", "AdcLogicalUnitId", "AdcChannelName", "AdcGroupId", "AdcChannel", "AdcGroup"],
    "Pwm": ["PwmPeriodDefault", "EmiosChannelId", "PwmEmiosChannels", "PwmEmiosBusRef"],
}

def find_element_def(root, target_id):
    """Find the element (struct/enum/array/bool/int) with id==target_id and dump its details."""
    for el in root.iter():
        tag = strip_ns(el.tag)
        if tag in {"enum","int","string","bool","array","struct","ref"} and el.attrib.get("id") == target_id:
            print(f"\n  [{tag}] id={target_id!r}  label={el.attrib.get('label','')!r}")
            for a, v in el.attrib.items():
                if a not in ("id","label"):
                    print(f"      attr {a}={v}")
            # For enum: print children <value> entries
            if tag == "enum":
                for child in el:
                    ct = strip_ns(child.tag)
                    if ct == "value":
                        print(f"      value id={child.attrib.get('id')!r}")
                    if ct == "value_provider":
                        print(f"      value_provider id={child.attrib.get('id')!r} type={child.attrib.get('type','')}")
            # For struct: list immediate child param names
            if tag == "struct":
                for child in el:
                    ct = strip_ns(child.tag)
                    cid = child.attrib.get("id","")
                    if ct in {"enum","int","string","bool","array","struct","ref"} and cid:
                        print(f"      child [{ct}] id={cid!r}")
            return True
    return False

for drv, ids in queries.items():
    print("\n" + "="*72)
    print(f"## {drv}")
    print("="*72)
    f = ROOT / drv / f"{drv}.component"
    root = ET.parse(str(f)).getroot()
    for tid in ids:
        if not find_element_def(root, tid):
            print(f"\n  [!!] id={tid!r} NOT FOUND in {drv}.component")
