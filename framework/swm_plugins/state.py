"""Shared state keys and paths for the plugins."""

from pathlib import Path

import pytest

FRAMEWORK_DIR = Path(__file__).resolve().parents[1]
ROOT = FRAMEWORK_DIR.parent
RESULTS_FILE = ROOT / "docs" / "results.json"
LOG_DIR = ROOT / "logs" / "auto"

FW_KEY = pytest.StashKey[str]()  # firmware key of the run: "2.1.0" -> "21"
RESULTS_KEY = pytest.StashKey[dict]()  # TC id -> PASS/FAIL for --record
