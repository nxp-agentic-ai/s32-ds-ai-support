from __future__ import annotations

import sys
from pathlib import Path

import pytest


THIS_DIR = Path(__file__).resolve().parent
TEST_FILE = THIS_DIR / "test_action_handlers_pytest.py"

if __name__ == "__main__":
    sys.path.insert(0, str(THIS_DIR))
    raise SystemExit(pytest.main([str(TEST_FILE), "-q", "--import-mode=importlib"]))
