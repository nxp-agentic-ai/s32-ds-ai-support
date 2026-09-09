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

"""S32SDAF (Volkano) action contracts.

Each ``ActionExecutable`` pairs a declarative ``ActionContract`` (name,
description, typed parameters -> JSON Schema, preconditions, related actions)
with a runtime handler from ``impl.handlers.action_handlers``. The shared
dispatcher validates params against the contract-derived schema before invoking
the handler, and shapes every result into the uniform ``ActionOutcome``
envelope.
"""

from nxp.mcp.shared import ActionContract, ActionExecutable, ActionParameter
from nxp.mcp.s32sdaf.impl.handlers import action_handlers as h

# Reusable parameter definitions ------------------------------------------------

_VOLKANO_FOLDER = ActionParameter(
    name="volkano_folder",
    required=False,
    schema={
        "type": "string",
        "description": (
            "Absolute path to the Volkano installation folder (contains volkano.exe). "
            "When omitted, the server config installation_path is used, else the newest "
            "installation under C:/NXP/S32DS*, C:/NXP/S32SDAF*, C:/NXP/SDAF*, or C:/NXP/S32DBG* is auto-discovered."

        ),
    },
)

_PASSWORD = ActionParameter(
    name="password",
    required=False,
    schema={
        "type": "string",
        "description": "Smart-card user password, when the operation requires it. Never guessed.",
    },
)

_UID = ActionParameter(
    name="uid",
    required=True,
    schema={
        "type": "string",
        "description": "Device UID as 16 hex chars (8 bytes) or 32 hex chars (16 bytes).",
    },
)

_NO_DEFAULTS_PRECONDITIONS = (
    "No hardware-specific defaults are applied; supply values explicitly.",
    "Use absolute paths for all file parameters.",
    "Discover registered UIDs with the 'discover' action before any key operation.",
)


FIND_INSTALLATION_ACTION = ActionExecutable(
    contract=ActionContract(
        name="find_installation",
        description=(
            "Search for Volkano installations under C:/NXP/S32DS*, C:/NXP/S32SDAF*, C:/NXP/SDAF*, and C:/NXP/S32DBG*. "

            "Returns all found installations sorted by version (newest first), each with its "
            "volkano_folder path, install root, and detected version, plus a 'recommended' folder. "
            "Call this first if you do not know where Volkano is installed."
        ),
        params=(),
        category="discovery",
        related_actions=("discover",),
    ),
    handler=h.find_installation,
)


DISCOVER_ACTION = ActionExecutable(
    contract=ActionContract(
        name="discover",
        description=(
            "Discover all UIDs and keys registered on the smart card. Run this first to see what is "
            "already stored before registering or deleting records."
        ),
        params=(_VOLKANO_FOLDER, _PASSWORD),
        category="discovery",
        preconditions=_NO_DEFAULTS_PRECONDITIONS,
        related_actions=("find_installation", "register_key", "delete_record"),
    ),
    handler=h.discover,
)


REGISTER_KEY_ACTION = ActionExecutable(
    contract=ActionContract(
        name="register_key",
        description=(
            "Register a key for a device UID using the appropriate Volkano register command. "
            "key_type selects the flow: ADKP (plain, key or keybin), ODAK/ADK1/ADK2 (wrapped, applet 1.5+), "
            "kUID/kUID_RF/kUID_PRE_FA (wrapped, applet 1.4+). ADK1/ADK2 need a 16-byte OID and key_index 0..15; "
            "ADK2 also needs adk2_key_type AES or ECC. The result includes an applet-version warning where relevant."
        ),
        params=(
            _UID,
            ActionParameter(
                name="key_type",
                required=True,
                schema={
                    "type": "string",
                    "enum": ["ADKP", "ODAK", "ADK1", "ADK2", "kUID", "kUID_RF", "kUID_PRE_FA"],
                    "description": "Key family to register (case-insensitive).",
                },
            ),
            ActionParameter(
                name="key",
                required=False,
                schema={"type": "string", "description": "Hex key. Plain for ADKP, or 512-hex wrapped key for wrapped families."},
            ),
            ActionParameter(
                name="keybin",
                required=False,
                schema={"type": "string", "description": "Absolute path to a binary key file (ADKP only)."},
            ),
            ActionParameter(
                name="oid",
                required=False,
                schema={"type": "string", "description": "16-byte OID as 32 hex chars (required for ADK1/ADK2)."},
            ),
            ActionParameter(
                name="key_index",
                required=False,
                schema={"type": "integer", "minimum": 0, "maximum": 15, "description": "Key index 0..15 (ADK1/ADK2)."},
            ),
            ActionParameter(
                name="adk2_key_type",
                required=False,
                schema={"type": "string", "enum": ["AES", "ECC"], "description": "ADK2 key type."},
            ),
            _VOLKANO_FOLDER,
            _PASSWORD,
        ),
        category="key_management",
        preconditions=_NO_DEFAULTS_PRECONDITIONS,
        related_actions=("discover", "export_wrapkey", "wrap_key"),
    ),
    handler=h.register_key,
)


DELETE_RECORD_ACTION = ActionExecutable(
    contract=ActionContract(
        name="delete_record",
        description=(
            "Delete a UID record and all its associated keys from the smart card. Requires applet v1.4+. "
            "This operation is IRREVERSIBLE: it is blocked unless confirmed_by_user=true after explicit user approval."
        ),
        params=(
            _UID,
            ActionParameter(
                name="confirmed_by_user",
                required=False,
                schema={"type": "boolean", "default": False, "description": "Must be true to actually delete."},
            ),
            _VOLKANO_FOLDER,
            _PASSWORD,
        ),
        category="key_management",
        preconditions=_NO_DEFAULTS_PRECONDITIONS + (
            "Deletion is irreversible; obtain explicit user confirmation and show the UID first.",
        ),
        related_actions=("discover",),
    ),
    handler=h.delete_record,
)


EXPORT_WRAPKEY_ACTION = ActionExecutable(
    contract=ActionContract(
        name="export_wrapkey",
        description=(
            "Export the public wrapping key from the smart card. Use the returned key with the 'wrap_key' "
            "action to wrap a plain key before registering it via 'register_key'."
        ),
        params=(_VOLKANO_FOLDER, _PASSWORD),
        category="key_management",
        preconditions=_NO_DEFAULTS_PRECONDITIONS,
        related_actions=("wrap_key", "register_key"),
    ),
    handler=h.export_wrapkey,
)


WRAP_KEY_ACTION = ActionExecutable(
    contract=ActionContract(
        name="wrap_key",
        description=(
            "Wrap a plain key using the smart card's public wrapping key (volkano_utils.exe -cmd wrap_key). "
            "Typical flow: export_wrapkey -> wrap_key -> register_key with the resulting 512-hex wrapped key."
        ),
        params=(
            ActionParameter(
                name="plain_key",
                required=True,
                schema={"type": "string", "description": "Plain key as a hex string."},
            ),
            ActionParameter(
                name="public_key",
                required=True,
                schema={"type": "string", "description": "Public wrapping key hex from export_wrapkey."},
            ),
            _VOLKANO_FOLDER,
        ),
        category="key_management",
        preconditions=_NO_DEFAULTS_PRECONDITIONS,
        related_actions=("export_wrapkey", "register_key"),
    ),
    handler=h.wrap_key,
)


GET_RESPONSE_ACTION = ActionExecutable(
    contract=ActionContract(
        name="get_response",
        description=(
            "Perform challenge-response authentication for a registered device UID. Provide the hex challenge "
            "from the target device. Optional key/key_name selector, oid, and scheme_id (1/2/3) support richer "
            "HSE2 / key-sensitive flows. ADK1-backed flows require an oid."
        ),
        params=(
            _UID,
            ActionParameter(
                name="challenge",
                required=True,
                schema={"type": "string", "description": "Hex challenge string received from the target device."},
            ),
            ActionParameter(
                name="key",
                required=False,
                schema={
                    "type": "string",
                    "description": "Symbolic key selector (ADKP/ADK1/ADK2/kUID/...) or discover-returned instance name (e.g. ADK1_1).",
                },
            ),
            ActionParameter(
                name="key_name",
                required=False,
                schema={"type": "string", "description": "Exact discover-returned key name (alternative to 'key')."},
            ),
            ActionParameter(
                name="oid",
                required=False,
                schema={"type": "string", "description": "OID hex, required for ADK1-backed flows."},
            ),
            ActionParameter(
                name="scheme_id",
                required=False,
                schema={"type": "integer", "enum": [1, 2, 3], "description": "Authentication scheme id."},
            ),
            _VOLKANO_FOLDER,
            _PASSWORD,
        ),
        category="authentication",
        preconditions=_NO_DEFAULTS_PRECONDITIONS + (
            "The UID must already be registered on the smart card.",
        ),
        related_actions=("discover", "register_key"),
    ),
    handler=h.get_response,
)


UPDATE_PWD_ACTION = ActionExecutable(
    contract=ActionContract(
        name="update_pwd",
        description=(
            "Set or update the smart-card user password (volkano.exe -cmd update_pwd). "
            "Provide 'new_password' (4..127 chars). For a first-password initialization on a "
            "newly initialized card, omit 'current_password'. To change an already-provisioned "
            "password, 'current_password' is mandatory and is passed as -pw. After a successful "
            "change, all future authenticated operations must use the new password."
        ),
        params=(
            ActionParameter(
                name="new_password",
                required=True,
                schema={
                    "type": "string",
                    "minLength": 4,
                    "maxLength": 127,
                    "description": "New smart-card user password (4..127 characters). Never guessed.",
                },
            ),
            ActionParameter(
                name="current_password",
                required=False,
                schema={
                    "type": "string",
                    "minLength": 4,
                    "maxLength": 127,
                    "description": (
                        "Current password (4..127 chars). Required only when updating an "
                        "already-provisioned card; omit for first-password initialization."
                    ),
                },
            ),
            _VOLKANO_FOLDER,
        ),
        category="credential_management",
        preconditions=_NO_DEFAULTS_PRECONDITIONS + (
            "Never guess the new or current password; require the user to supply them.",
            "Replacing the password causes operations with the old password to fail.",
        ),
        related_actions=("discover", "get_response"),
    ),
    handler=h.update_pwd,
)


STATIC_ACTIONS = (
    FIND_INSTALLATION_ACTION,
    DISCOVER_ACTION,
    REGISTER_KEY_ACTION,
    DELETE_RECORD_ACTION,
    EXPORT_WRAPKEY_ACTION,
    WRAP_KEY_ACTION,
    GET_RESPONSE_ACTION,
    UPDATE_PWD_ACTION,
)


