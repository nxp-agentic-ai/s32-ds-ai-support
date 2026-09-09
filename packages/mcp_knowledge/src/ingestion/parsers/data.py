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

"""Data file parser for JSON and YAML — normalises to readable indented text."""
import json
from pathlib import Path

from .base import Parser


class DataParser(Parser):
    """Parses ``.json``, ``.yaml``, and ``.yml`` files.

    The parsed data structure is serialised back to a consistently indented
    text representation so that the chunker and embedder see human-readable
    key-value pairs rather than compressed single-line source.

    - JSON files are re-serialised with ``json.dumps(..., indent=2)``.
    - YAML files are loaded with ``pyyaml`` and re-serialised to JSON-style
      indented text (avoids adding a YAML serialisation dependency).
    """

    extensions: frozenset[str] = frozenset({".json", ".yaml", ".yml"})

    def parse(self, path: Path) -> str:
        suffix = path.suffix.lower()
        raw = path.read_text(encoding="utf-8", errors="replace")

        if suffix == ".json":
            return self._parse_json(raw)
        else:
            return self._parse_yaml(raw)

    @staticmethod
    def _parse_json(raw: str) -> str:
        try:
            data = json.loads(raw)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # Fall back to raw text if the file is not valid JSON
            return raw

    @staticmethod
    def _parse_yaml(raw: str) -> str:
        try:
            import yaml  # pyyaml — already a project dependency

            data = yaml.safe_load(raw)
            if data is None:
                return ""
            # Re-serialise via JSON for a consistent readable format
            return json.dumps(data, indent=2, ensure_ascii=False, default=str)
        except Exception:
            return raw
