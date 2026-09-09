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

from pathlib import Path
from typing import Optional
import mimetypes
import base64

from nxp.mcp.s32flashtool.impl.constants import CLI_EXE_NAME


__all__ = [
    "guided_missing_parameter_error",
    "validate_hex_like",
    "validate_numeric_like",
    "validate_existing_file",
    "validate_existing_folder",
    "resolve_relative_to_installation",
    "validate_s32flashtool_installation",
    "list_files_by_extension",
    "list_available_test_blob_binaries",
    "list_pdfs_with_platform",
    "list_available_supported_devices_text_files",
]


def guided_missing_parameter_error(parameter: str, hint: str) -> str:
    return f"Missing required parameter '{parameter}'. Hint: {hint}"


def validate_hex_like(value: Optional[str], parameter: str) -> None:
    if value is None or value == "":
        return
    if not isinstance(value, str) or not value.lower().startswith("0x"):
        raise ValueError(
            f"Invalid '{parameter}' format: '{value}'. Expected hexadecimal string like 0x1000."
        )


def validate_numeric_like(value: Optional[str], parameter: str) -> None:
    if value is None or value == "":
        return
    if isinstance(value, str) and (value.isdigit() or value.lower().startswith("0x")):
        return
    raise ValueError(
        f"Invalid '{parameter}' format: '{value}'. Expected decimal digits or hexadecimal string like 0x1000."
    )


def validate_existing_file(path_value: Optional[str], parameter: str) -> None:
    if path_value is None or path_value == "":
        return
    p = Path(path_value)
    if not p.is_absolute():
        raise ValueError(f"'{parameter}' must be an absolute path. Got: {path_value}")
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"'{parameter}' file not found: {path_value}")


def validate_existing_folder(path_value: str, parameter: str) -> None:
    p = Path(path_value)
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"'{parameter}' folder not found: {path_value}")


def resolve_relative_to_installation(base_folder: str, value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    p = Path(value)
    if p.is_absolute():
        return str(p)
    return str((Path(base_folder) / p).resolve())


def validate_s32flashtool_installation(base_folder: str) -> None:
    validate_existing_folder(base_folder, "s32flashtool_folder")

    required_paths = [
        Path(base_folder) / "bin",
        Path(base_folder) / "targets",
        Path(base_folder) / "flash",
        Path(base_folder) / "bin" / CLI_EXE_NAME,
    ]
    missing = [str(p) for p in required_paths if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Invalid S32FlashTool installation folder. Missing: " + ", ".join(missing)
        )
    


def list_files_by_extension(
    base_folder: str,
    subfolder: str,
    extension: str,
) -> list[str]:
    """
    List files with a given extension from a subfolder inside a base folder.

    Args:
        base_folder: Base directory path
        subfolder: Subfolder relative to the base directory
        extension: File extension (e.g. ".bin", ".hex")

    Returns:
        List of absolute file paths as strings
    """
    base_path = Path(base_folder)
    target_path = base_path / subfolder

    if not target_path.exists():
        raise FileNotFoundError(f"Folder does not exist: {target_path}")

    if not target_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {target_path}")

    # Normalize extension (ensure it starts with ".")
    if not extension.startswith("."):
        extension = "." + extension

    files = [
        str(file.resolve())
        for file in target_path.iterdir()
        if file.is_file() and file.suffix.lower() == extension.lower()
    ]

    return sorted(files)


def list_available_test_blob_binaries(base_folder: str) -> list[str]:
    # allowed_flash_types = {"FLASH", "SD", "SRAM", "eMMC", "EEPROM", "RCON"}
    
    base = Path(base_folder)

    if not base.exists():
        raise FileNotFoundError(f"Examples folder not found: {base}")

    lines: list[str] = []

    for bin_file in base.rglob("*.bin"):
        rel_parts = bin_file.relative_to(base).parts
        if len(rel_parts) < 4:
            continue

        platform_name = rel_parts[0]
        board_name = rel_parts[1]
        flash_type = rel_parts[2]

        # if flash_type not in allowed_flash_types:
        #     continue

        lines.append(
            f"{platform_name} | {board_name} | {flash_type} | {bin_file}"
        )

    return sorted(lines)
    
    
def list_pdfs_with_platform(base_folder: str) -> list[str]:
    """
    Traverse the examples folder and extract PDFs with platform names.

    Returns a list where each entry is:
    <platform> | <pdf_filename> | <absolute_pdf_path>
    """
    base_path = Path(base_folder)

    if not base_path.exists():
        raise FileNotFoundError(f"Base folder does not exist: {base_path}")

    results: list[str] = []
                            
    # Expected structure: examples/<platform>/...
    for platform_dir in base_path.iterdir():
        if not platform_dir.is_dir():
            continue

        platform_name = platform_dir.name

        # Recursively search for PDFs inside the platform directory
        for pdf_file in platform_dir.rglob("*.pdf"):
            line = f"{platform_name} | {pdf_file.name} | {pdf_file.resolve()}"
            results.append(line)

    return sorted(results)

def list_available_supported_devices_text_files(
        base_folder: str
    ) -> list[str]:
        files = list_files_by_extension(
            base_folder, subfolder="doc", extension=".txt"
        )

        supported_files = [
            f for f in files if Path(f).name.lower().startswith("supported")
        ]

        return supported_files            

