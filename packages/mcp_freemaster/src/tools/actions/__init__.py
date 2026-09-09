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

from .server_connection import WS_CONNECT, WS_DISCONNECT
from .utils import GET_APP_VERSION, STOP_SERVER
from .embedded_symbols import READ_ELF, READ_TSA
from .board_connection import START_COMM, STOP_COMM, IS_COMM_PORT_OPEN, IS_BOARD_CONNECTED, GET_BOARD_INFO
from .project_variables import DEFINE_VARIABLE, GET_VARIABLE_INFO, READ_VARIABLE, WRITE_VARIABLE

ACTIONS = (
    WS_CONNECT,
    WS_DISCONNECT,
    GET_APP_VERSION,
    STOP_SERVER,
    START_COMM,
    STOP_COMM,
    IS_COMM_PORT_OPEN,
    IS_BOARD_CONNECTED,
    GET_BOARD_INFO,
    READ_ELF,
    READ_TSA,
    DEFINE_VARIABLE,
    GET_VARIABLE_INFO,
    READ_VARIABLE,
    WRITE_VARIABLE
)