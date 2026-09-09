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

# This package intentionally contains only data files (*.md, *.json).
# The presence of this __init__.py makes setuptools treat the directory as a
# regular package so the [tool.setuptools.package-data] glob is honored and
# the resource files are shipped in the built wheel.