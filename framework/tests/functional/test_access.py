"""Access levels (AC-1) and unknown/odd input (AC-2, NFR-4)."""

import pytest

from tests.helpers import uptime_seconds

pytestmark = [pytest.mark.functional]

# Commands without a [wifi]/[login] mark in 'help': must work with no Wi-Fi-dependent session at all.
ALWAYS_AVAILABLE = ["help", "status", "version", "uptime", "sysinfo", "temp", "whoami", "logout", "scan"]
# [login] commands: Wi-Fi + login required, otherwise E003.
LOGIN_ONLY = ["lamp on", "lamp status", "relay on", "relay status", "distance", "state", "ota", "health now", "passwd a b", "sudo x"]


@pytest.mark.tc("TC-AC-01")
@pytest.mark.parametrize("command", ALWAYS_AVAILABLE)
def test_unmarked_commands_work_without_login(dut_raw, command):
    r = dut_raw.exchange(command, idle=1.5)
    assert not r.has_code("E002") and not r.has_code("E003") and not r.has_code("E004"), f"'{command}' must be always available:\n{r}"
    assert not r.has_code("E001"), f"'{command}' unknown:\n{r}"


@pytest.mark.tc("TC-AC-03")
@pytest.mark.parametrize("command", LOGIN_ONLY)
def test_login_commands_rejected_without_login_with_e003(dut_raw, command):
    r = dut_raw.exchange(command)
    assert r.has_code("E003"), f"'{command}' without login must give E003, got {r.codes}\n{r}"


@pytest.mark.tc("TC-AC-02")
@pytest.mark.parametrize("command", ["net", "ping", "time", "register abc Pass1234"])
def test_wifi_commands_rejected_without_wifi_with_e002(dut_raw, command):
    dut_raw.exchange("disconnect", idle=1.5)  # baseline fixture restores Wi-Fi afterwards
    r = dut_raw.exchange(command)
    assert r.has_code("E002"), f"'{command}' without Wi-Fi must give E002, got {r.codes}\n{r}"


@pytest.mark.tc("TC-AC-04")
def test_login_command_without_wifi_is_rejected_with_a_known_access_code(dut_raw):
    """PRD doesn't say which error wins when both Wi-Fi and login are missing. DUT picks E002 - fine,
    accept either; flagged as a PRD gap, not a bug."""
    dut_raw.exchange("disconnect", idle=1.5)
    r = dut_raw.exchange("lamp on")
    assert r.has_code("E002") or r.has_code("E003"), f"got {r.codes}\n{r}"
    assert not r.has("[BEACON] on"), "the command must not be executed"


@pytest.mark.tc("TC-AC-06")
@pytest.mark.parametrize("command", ["foo", "lamp2", "statuss"])
def test_unknown_command_gives_e001_with_the_typed_text(dut_raw, command):
    r = dut_raw.exchange(command)
    assert r.has_code("E001"), r
    assert r.has(f"unknown command '{command}'") and r.has("Type 'help'")


@pytest.mark.tc("TC-AC-07")
@pytest.mark.parametrize("command", ["HELP", "Help", "STATUS", "Version", "WHOAMI"])
def test_first_word_is_case_insensitive(dut_raw, command):
    r = dut_raw.exchange(command, idle=1.0)
    assert not r.has_code("E001"), f"'{command}' must work like its lower-case form:\n{r}"


@pytest.mark.tc("TC-AC-08")
@pytest.mark.parametrize("text", ["привіт", "status ї", "команда"])
def test_non_latin_input_is_ignored_with_w006(dut_raw, text):
    assert dut_raw.exchange(text).has_code("W006")
    assert dut_raw.exchange("version").has("fw v")  # still alive


@pytest.mark.tc("TC-AC-09", "TC-NFR-03")
@pytest.mark.parametrize("payload", ["", "   ", "x" * 300, "x" * 1000, "status " + "A" * 500, "\x01\x02\x03"])
def test_odd_input_does_not_hang_or_reboot_the_device(dut_raw, payload):
    """NFR-4: bad input must not reboot or freeze the DUT. Uptime must keep growing and commands must still answer."""
    before = uptime_seconds(dut_raw)
    dut_raw.exchange(payload, idle=1.5, timeout=6)
    assert dut_raw.exchange("version").has("fw v"), "DUT stopped answering after odd input"
    assert uptime_seconds(dut_raw) >= before, "uptime went backwards: the DUT rebooted"
