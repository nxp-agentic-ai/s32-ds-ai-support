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

"""Canonical public manifest for compiler action executables.

Consumers should import the per-toolchain action tuples from this package
to build the active component action catalog. Individual action constants
remain module-level implementation details.

The catalog is split by toolchain family so that the registration layer
can include only the actions for toolchains that are actually installed.
"""

from .compiler_list_gcc_tools import LIST_GCC_TOOLS_ACTION
from .compiler_gcc_execute import GCC_EXECUTE_ACTION
from .compiler_list_lax_tools import LIST_LAX_TOOLS_ACTION
from .compiler_lax_execute import LAX_EXECUTE_ACTION
from .compiler_list_lax_simulator_tools import LIST_LAX_SIMULATOR_TOOLS_ACTION
from .compiler_lax_simulator_execute import LAX_SIMULATOR_EXECUTE_ACTION
from .compiler_list_spt_tools import LIST_SPT_TOOLS_ACTION
from .compiler_spt_execute import SPT_EXECUTE_ACTION


GCC_ACTIONS = (
    LIST_GCC_TOOLS_ACTION,
    GCC_EXECUTE_ACTION,
)

LAX_ACTIONS = (
    LIST_LAX_TOOLS_ACTION,
    LAX_EXECUTE_ACTION,
)

LAX_SIMULATOR_ACTIONS = (
    LIST_LAX_SIMULATOR_TOOLS_ACTION,
    LAX_SIMULATOR_EXECUTE_ACTION,
)

SPT_ACTIONS = (
    LIST_SPT_TOOLS_ACTION,
    SPT_EXECUTE_ACTION,
)

# Full manifest - all actions regardless of toolchain availability.
# Registration code should use the per-family tuples and only include
# families whose toolchain folders exist on the current host.
ACTIONS = GCC_ACTIONS + LAX_ACTIONS + LAX_SIMULATOR_ACTIONS + SPT_ACTIONS


__all__ = [
    "ACTIONS",
    "GCC_ACTIONS",
    "LAX_ACTIONS",
    "LAX_SIMULATOR_ACTIONS",
    "SPT_ACTIONS",
]
