"""Driver logic against a scripted FakeTransport, no hardware needed.

Lesson 19: the automation is a product too - prove prompts w/o newline, slow replies, timeouts
and password masking work before trusting it on the real DUT.
"""

import time

import pytest

from drivers.device_driver import SwmDevice
from drivers.redaction import Redactor
from drivers.transport import FakeTransport

pytestmark = pytest.mark.unit

WIFI_PASSWORD = "S3cretWifiPass"


def make(script, **kw) -> tuple[SwmDevice, FakeTransport]:
    t = FakeTransport(script)
    return SwmDevice(t, Redactor(), timeout=1.0, idle=0.05, **kw), t


def test_exchange_strips_echo_and_returns_reply():
    dev, _ = make({"whoami": "I (1) sentry: user: qa_swm, access: user\n"})
    r = dev.exchange("whoami")
    assert not r.timed_out
    assert r.search(r"user: (\w+), access: (\w+)").groups() == ("qa_swm", "user")
    assert "whoami" not in r.lines[0].raw  # echo removed


def test_exchange_extracts_error_code():
    dev, _ = make({"lamp brightness 101": "E (1) sentry: E504 brightness must be 0-100\n"})
    assert dev.exchange("lamp brightness 101").has_code("E504")


def test_no_reply_is_reported_as_timeout():
    dev, t = make({})
    t.write = lambda data: None  # the device swallows the command and prints nothing
    assert dev.exchange("silent", timeout=0.2).timed_out


def test_until_waits_for_slow_reply_across_pauses():
    """A pause longer than 'idle' mid-reply must not cut it off when 'until' is set."""
    dev, t = make({"ota check": "I (1) sentry: [V] GET stable.txt\n"})
    original_read = t.read
    t0 = time.monotonic()
    late = {"sent": False}

    def delayed_read(timeout):
        if not late["sent"] and time.monotonic() - t0 > 0.3:  # second half arrives 0.3 s later
            late["sent"] = True
            t._queue += b"I (2) sentry: [OTA] up to date (stable)\n"
        return original_read(timeout)

    t.read = delayed_read
    r = dev.exchange("ota check", until=r"up to date|update available", timeout=2)
    assert not r.timed_out
    assert r.has("up to date (stable)")


def test_connect_wifi_handles_prompts_without_newline_and_masks_password():
    script = {
        "connect": "I (1) sentry: [LINK] scanning...\nI (2) sentry:   [ 1] CMF   -28 dBm\nSSID or number: ",
        "CMF": "Password: ",
        WIFI_PASSWORD: "********\nI (9) sentry: [LINK] connected to 'CMF', rssi -28 dBm\nI (10) sentry: [LINK] network saved. Next time just type 'reconnect'\n",
    }
    dev, t = make(script)
    r = dev.connect_wifi("CMF", WIFI_PASSWORD)
    assert not r.timed_out
    assert r.has("network saved")
    # evidence must never contain the password, neither in the transcript nor in the response
    assert WIFI_PASSWORD not in dev.transcript.render()
    assert WIFI_PASSWORD not in r.text
    assert t.sent == ["connect", "CMF", WIFI_PASSWORD]  # but the device did receive it


def test_connect_wifi_reports_short_password_error():
    script = {
        "connect": "SSID or number: ",
        "CMF": "Password: ",
        "short": "E (1) sentry: E112 password too short (min 8 chars)\n",
    }
    dev, _ = make(script)
    r = dev.connect_wifi("CMF", "short")
    assert r.has_code("E112")


def test_login_waits_for_session_marker():
    dev, _ = make({"login qa_swm Pass1234": "I (1) sentry: [AUTH] operator qa_swm on watch, console 2\n"})
    assert dev.login("qa_swm", "Pass1234").has("on watch")


def test_wait_for_raises_with_captured_text_on_timeout():
    dev, _ = make({})
    with pytest.raises(TimeoutError, match="not seen"):
        dev.wait_for(r"never appears", 0.2)


def test_hard_reset_returns_boot_log():
    boot = "I (1) sentry: last reset: power on\nI (2) sentry: ready. state 1 NORMAL (patrol). Type 'help'\n"
    t = FakeTransport({}, boot_text=boot)
    dev = SwmDevice(t, timeout=1.0, idle=0.05)
    r = dev.hard_reset(timeout=2)
    assert r.has("last reset: power on")


def test_ensure_wifi_retries_reconnect_after_e101_and_logs_the_retry():
    script = {
        "reconnect": [
            "E (1) sentry: E101 wrong password for 'CMF'\n",
            "I (2) sentry: [LINK] connected to 'CMF', rssi -28 dBm\n",
        ]
    }
    dev, t = make(script)
    r = dev.ensure_wifi("known network 'CMF'. Type 'reconnect'", "CMF", WIFI_PASSWORD, settle=0.05)
    assert r.has("connected to")
    assert t.sent == ["reconnect", "reconnect"]
    assert "retry 2/3" in dev.transcript.render()  # the retry stays visible in the evidence


def test_blank_board_boot_text_is_not_a_saved_network():
    from drivers.device_driver import has_saved_network

    assert not has_saved_network("I (600) sentry: [LINK] no known network. Type 'connect'")
    assert has_saved_network("I (600) sentry: [LINK] known network 'CMF'. Type 'reconnect' to connect")


def test_ensure_wifi_uses_connect_when_boot_says_no_known_network():
    script = {
        "connect": "I (1) sentry: [LINK] scanning...\n  [ 1] CMF  -28 dBm\nEnter SSID or number:\n",
        "CMF": "Password:\n",
        WIFI_PASSWORD: "I (2) sentry: [LINK] connected to 'CMF', rssi -28 dBm\nnetwork saved\n",
    }
    dev, t = make(script)
    r = dev.ensure_wifi("I (600) sentry: [LINK] no known network. Type 'connect'", "CMF", WIFI_PASSWORD, settle=0.05)
    assert "reconnect" not in t.sent
    assert t.sent[0] == "connect"
    assert r.has("network saved") or r.has("connected to")


def test_ensure_wifi_gives_up_after_attempts_and_reports_e101():
    dev, t = make({"reconnect": "E (1) sentry: E101 wrong password for 'CMF'\n"})
    r = dev.ensure_wifi("known network 'CMF'", "CMF", WIFI_PASSWORD, attempts=3, settle=0.05)
    assert r.has_code("E101")
    assert t.sent.count("reconnect") == 3


def test_reply_split_in_the_middle_of_a_line_is_not_cut_and_does_not_leak():
    """Regression: 'until' matched E202 while the line was still arriving, so its tail ('r device)')
    leaked into the next command's reply. Found on real hardware."""
    dev, t = make({"register x y": "E (1) sentry: E202 profile 'qa_swm' already exists (one pe"})
    original_read = t.read
    pending = {"tail": b"r device)\n"}  # the second burst of the same line, delivered on the NEXT read

    def read_with_split(timeout):
        if pending["tail"] is not None and not t._queue and t.sent:
            tail, pending["tail"] = pending["tail"], None
            return tail
        return original_read(timeout)

    t.read = read_with_split
    r = dev.exchange("register x y", until=r"E\d{3}")
    assert r.has("(one per device)")
    t.script["whoami"] = "I (2) sentry: user: a, access: user\n"
    assert "device)" not in dev.exchange("whoami").text


def test_link_up_parses_status():
    up = "I (1) sentry:   link:     connected to 'CMF' rssi -28 dBm\n"
    down = "I (1) sentry:   link:     buoy link down (known: CMF)\n"
    dev, _ = make({"status": up})
    assert dev.link_up()
    dev, _ = make({"status": down})
    assert not dev.link_up()
