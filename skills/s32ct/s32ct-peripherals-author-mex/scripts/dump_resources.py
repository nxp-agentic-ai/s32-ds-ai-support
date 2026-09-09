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

"""Dump the per-driver resource arrays we care about."""
import xml.etree.ElementTree as ET
import re
from pathlib import Path

ROOT = Path(r"C:\NXP\S32DS.3.6.6\eclipse\mcu_data\processors\S32K312\PlatformSDK_S32K3\S32K312_172HDQFP\resource_tables")
def strip_ns(t): return re.sub(r"\{[^}]+\}", "", t)

interesting = {
    "Spi": ("Spi.xml", ["SpiGeneral.SpiPhyUnit.SpiPhyUnitMapping"]),
    "RTD_Uart": ("RTD/Uart.xml", None),       # dump all
    "Can": ("Can.xml", None),
    "RTD_Lin": ("RTD/Lin.xml", None),
    "Adc": ("Adc.xml", None),
    "RTD_Pwm": ("RTD/Pwm.xml", None),
}

for label, (rel, filter_ids) in interesting.items():
    f = ROOT / rel
    print(f"\n{'='*70}\n## {label}: {rel}\n{'='*70}")
    if not f.exists():
        print("MISSING"); continue
    root = ET.parse(str(f)).getroot()
    # Find <data> arrays
    for arr in root.iter():
        if strip_ns(arr.tag) == "array" and "name" in arr.attrib:
            n = arr.attrib["name"]
            if filter_ids and not any(fid in n for fid in filter_ids):
                continue
            settings = []
            for s in arr:
                if strip_ns(s.tag) == "setting":
                    settings.append(s.attrib.get("value",""))
            if settings:
                vals = settings[:12]
                more = f" ... (+{len(settings)-12})" if len(settings)>12 else ""
                print(f"  [{n}] = {vals}{more}")
