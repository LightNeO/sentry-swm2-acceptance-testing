"""Unit tests for the parser and the redactor. They use real lines captured from the DUT (logs/v2.1.0)."""

import pytest

from drivers.protocol import Response, parse_line
from drivers.redaction import Redactor

pytestmark = pytest.mark.unit


def test_parse_plain_log_line():
    line = parse_line("W (231769) sentry: [STATE] 1 NORMAL -> 3 VERBOSE (by command)")
    assert (line.level, line.tick, line.tag) == ("W", 231769, "sentry")
    assert line.msg.startswith("[STATE]")
    assert line.codes == ()


def test_parse_error_code():
    line = parse_line("E (35519) sentry: E112 password too short (min 8 chars)")
    assert line.level == "E"
    assert line.codes == ("E112",)


def test_parse_log_glued_into_echo():
    """Real case: telemetry interrupted the echo of 'relay on' -> 'reI (205039) ...'."""
    line = parse_line("reI (205039) sentry: [TELEMETRY #2] 17:40:11 up 00:03:24 heap 257KB")
    assert line.tick == 205039
    assert line.msg.startswith("[TELEMETRY #2]")


def test_prompt_without_log_header():
    line = parse_line("SSID or number: ")
    assert line.level is None
    assert line.msg == "SSID or number:"


def test_noise_lines_are_flagged():
    assert parse_line("I (1) sentry: [NAV] depth 41.6 m, heading 274").is_noise
    assert not parse_line("I (1) sentry: [VALVE] OPEN (command)").is_noise


def test_response_helpers():
    r = Response.from_text(
        "relay on",
        "W (1) sentry: W601 relay already on\nI (2) sentry: [NAV] depth 41.6 m\n",
    )
    assert r.codes == ["W601"]
    assert r.errors == []
    assert r.has_code("W601")
    assert len(r.without_noise()) == 1
    assert r.search(r"relay already (\w+)").group(1) == "on"


def test_warning_level_marker_is_not_a_code():
    """'W (1234)' and 'E (1234)' log headers must not be read as W123/E123 codes."""
    assert parse_line("E (1234) sentry: something failed").codes == ()


def test_redactor_masks_secret_everywhere():
    red = Redactor(["hunter2pass"])
    assert red.clean("Password: hunter2pass ok hunter2pass") == "Password: *** ok ***"


def test_redactor_ignores_too_short_secret():
    assert Redactor(["ab"]).clean("abc ab") == "abc ab"
