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

from .config.loader import load_gateway_config
from .runtime.stdio import run_stdio
from .runtime.http import run_http


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    config = load_gateway_config(path)

    # Transport is determined by the config: if the top-level http block is
    # present (not None), use HTTP (streamable-http); otherwise use stdio.
    if config.http is not None:
        run_http(config)
    else:
        run_stdio(config)


if __name__ == "__main__":
    main()
