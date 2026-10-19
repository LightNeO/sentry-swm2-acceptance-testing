"""The evidence sanitizer keeps the test AP and hides every other network name."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from sanitize_logs import sanitize_text  # noqa: E402

pytestmark = pytest.mark.unit


def test_scan_lines_keep_only_the_test_ap():
    text = (
        "I (3440) sentry:   [ 1] SENTRY-HIL                        -27 dBm\n"
        "I (3440) sentry:   [ 2] TP-LINK_E6F2                      -69 dBm\n"
        "I (3440) sentry:   [ 3] NeO                               -48 dBm\n"
    )
    out = sanitize_text(text, ["NeO"])
    assert "SENTRY-HIL" in out
    assert "TP-LINK_E6F2" not in out
    assert "NeO" not in out
    assert out.count("<ssid>") == 2 or out.count("<upstream>") == 1


def test_upstream_name_is_masked_everywhere_and_the_call_is_idempotent():
    text = "wlp0s21f0u2     wifi      connected               NeO\n"
    once = sanitize_text(text, ["NeO"])
    assert "NeO" not in once
    assert sanitize_text(once, ["NeO"]) == once
