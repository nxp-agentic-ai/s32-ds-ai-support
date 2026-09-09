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

"""Canonical public manifest for S32CT action executables.

``ACTIONS`` is the single source of truth for the component's active action
catalog. It is assembled explicitly from the per-category tuples below rather
than discovered by scanning the filesystem, so the exposed surface is
reviewable in one place and helper modules (``_params``, ``_configure_factory``)
can live alongside the action modules without accidentally contributing
actions.

Categories:

* ``configure`` - write-side launcher actions: the full-surface CLI, the eight
  per-subsystem wrappers, and scoped code generation.
* ``gtm``       - GTM edit / use-case discovery / use-case bootstrap.
* ``inspect``   - read-only structural queries over a ``.mex``.
* ``lookup``    - read-only allowed-value queries against the MCU data package.
* ``validate``  - the Problems-View validation gate.
* ``sanitize``  - cross-reference repair for spliced projects.
* ``env``       - read-only environment / installation probes.
"""

from .configure_cli import CONFIGURE_CLI_ACTION
from .env import ENV_ACTIONS
from .generate_code import GENERATE_CODE_ACTION
from .gtm import GTM_ACTIONS
from .inspect import INSPECT_ACTIONS
from .lookup import LOOKUP_ACTIONS
from .sanitize import SANITIZE_ACTION
from .validate import VALIDATE_ACTION
from ._configure_factory import CONFIGURE_SUBSYSTEM_ACTIONS

CONFIGURE_ACTIONS: tuple = (
    CONFIGURE_CLI_ACTION,
    *CONFIGURE_SUBSYSTEM_ACTIONS,
    GENERATE_CODE_ACTION,
)

VALIDATE_ACTIONS: tuple = (VALIDATE_ACTION,)

SANITIZE_ACTIONS: tuple = (SANITIZE_ACTION,)

# The canonical manifest. Ordering is stable and groups related actions
# together, which keeps search results readable when a query matches a whole
# category.
ACTIONS: tuple = (
    *CONFIGURE_ACTIONS,
    *GTM_ACTIONS,
    *INSPECT_ACTIONS,
    *LOOKUP_ACTIONS,
    *VALIDATE_ACTIONS,
    *SANITIZE_ACTIONS,
    *ENV_ACTIONS,
)


__all__ = [
    "ACTIONS",
    "CONFIGURE_ACTIONS",
    "ENV_ACTIONS",
    "GTM_ACTIONS",
    "INSPECT_ACTIONS",
    "LOOKUP_ACTIONS",
    "SANITIZE_ACTIONS",
    "VALIDATE_ACTIONS",
]
