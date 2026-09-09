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

import sys

from .config import load_standalone_config
from .server import run_stdio


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    config = load_standalone_config(path)
    run_stdio(config)


if __name__ == "__main__":
    main()
