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

"""Canonical public manifest for S32Debugger action executables.

Consumers should import ``ACTIONS`` from this package to build the active
component action catalog. Individual action constants remain module-level
implementation details.

The active catalog is the final 14-action, 3-category surface:
  control (7): set_installation_path, start_gdb, stop_gdb, command, interrupt, transcript, run_ccs_tcl

  inspect (6): installation_path, debug_processes, gdb_client_status, gdb_server, installed_gdbs, compatible_version
  generate (1): gdb_config_file
"""


# --- Active catalog imports (control) -------------------------------------
from .control_set_installation_path import CONTROL_SET_INSTALLATION_PATH_ACTION
from .control_start_gdb import CONTROL_START_GDB_ACTION
from .control_stop_gdb import CONTROL_STOP_GDB_ACTION
from .control_command import CONTROL_COMMAND_ACTION
from .control_interrupt import CONTROL_INTERRUPT_ACTION
from .control_transcript import CONTROL_TRANSCRIPT_ACTION
from .control_run_ccs_tcl import CONTROL_RUN_CCS_TCL_ACTION


# --- Active catalog imports (inspect) -------------------------------------
from .inspect_installation_path import INSPECT_INSTALLATION_PATH_ACTION
from .inspect_debug_processes import INSPECT_DEBUG_PROCESSES_ACTION
from .inspect_gdb_client_status import INSPECT_GDB_CLIENT_STATUS_ACTION
from .inspect_gdb_server import INSPECT_GDB_SERVER_ACTION
from .inspect_installed_gdbs import INSPECT_INSTALLED_GDBS_ACTION
from .inspect_compatible_version import INSPECT_COMPATIBLE_VERSION_ACTION

# --- Active catalog imports (generate) ------------------------------------

from .generate_gdb_config_file import GENERATE_GDB_CONFIG_FILE_ACTION


ACTIONS = (
    # control
    CONTROL_SET_INSTALLATION_PATH_ACTION,

    CONTROL_START_GDB_ACTION,
    CONTROL_STOP_GDB_ACTION,
    CONTROL_COMMAND_ACTION,
    CONTROL_INTERRUPT_ACTION,
    CONTROL_TRANSCRIPT_ACTION,
    CONTROL_RUN_CCS_TCL_ACTION,
    # inspect

    INSPECT_INSTALLATION_PATH_ACTION,
    INSPECT_DEBUG_PROCESSES_ACTION,
    INSPECT_GDB_CLIENT_STATUS_ACTION,
    INSPECT_GDB_SERVER_ACTION,
    INSPECT_INSTALLED_GDBS_ACTION,
    INSPECT_COMPATIBLE_VERSION_ACTION,
    # generate
    GENERATE_GDB_CONFIG_FILE_ACTION,

)


__all__ = ["ACTIONS"]
