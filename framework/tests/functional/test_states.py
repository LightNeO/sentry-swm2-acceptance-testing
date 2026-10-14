"""System states (ST-1..ST-4) and EMERGENCY lock-down."""

import re

import pytest

from tests.helpers import current_state

pytestmark = [pytest.mark.functional]


def to_emergency(dut):
    """The only legal route (ST-2): NORMAL -> VERBOSE -> EMERGENCY."""
    dut.exchange("state 3")
    r = dut.exchange("state 4")
    assert "EMERGENCY" in r.text, f"cannot enter EMERGENCY via VERBOSE:\n{r}"


@pytest.mark.tc("TC-ST-01")
@pytest.mark.parametrize("arg,expected", [("2", "DEBUG"), ("3", "VERBOSE"), ("debug", "DEBUG"), ("verbose", "VERBOSE"), ("1", "NORMAL")])
def test_state_change_by_number_and_name(dut, arg, expected):
    dut.exchange("state 2" if expected == "NORMAL" else "state 1")  # start from a different state
    dut.exchange(f"state {arg}")
    assert current_state(dut) == expected


@pytest.mark.tc("TC-ST-03")
def test_debug_state_prints_parser_diagnostics(dut):
    dut.exchange("state 2")
    assert dut.exchange("whoami").has("[DBG]")


@pytest.mark.tc("TC-ST-04")
def test_verbose_state_adds_logs_and_did_you_mean_hint(dut):
    dut.exchange("state 3")
    r = dut.exchange("lamp2")
    assert r.has("[V]") or r.has("Did you mean"), r
    assert r.has("Did you mean"), f"VERBOSE must hint a similar command for an unknown one:\n{r}"


@pytest.mark.tc("TC-ST-05")
@pytest.mark.parametrize("start,start_name", [("1", "NORMAL"), ("2", "DEBUG")])
def test_emergency_only_from_verbose(dut, start, start_name):
    """ST-2: from any state except VERBOSE -> E302 and the state must not change."""
    dut.exchange(f"state {start}")
    r = dut.exchange("state 4")
    assert r.has_code("E302"), f"EMERGENCY must be refused from {start_name}, got codes {r.codes}\n{r}"
    assert current_state(dut) == start_name, "state changed despite E302"


@pytest.mark.tc("TC-ST-05")
def test_emergency_refused_from_debug_when_requested_by_name(dut):
    dut.exchange("state debug")
    r = dut.exchange("state emergency")
    assert r.has_code("E302"), f"codes {r.codes}\n{r}"


@pytest.mark.tc("TC-ST-06")
def test_emergency_entered_from_verbose(dut):
    dut.exchange("state 3")
    r = dut.exchange("state 4")
    assert r.has("EMERGENCY")
    assert current_state(dut) == "EMERGENCY"


@pytest.mark.tc("TC-ST-08")
@pytest.mark.parametrize("command", ["help", "status", "whoami", "version", "health now"])
def test_emergency_allows_only_listed_commands(dut, command):
    to_emergency(dut)
    r = dut.exchange(command, idle=1.5)
    assert not r.has_code("E005") and not r.has_code("E001"), f"'{command}' is allowed in EMERGENCY (ST-3):\n{r}"


@pytest.mark.tc("TC-ST-10")
@pytest.mark.parametrize("command", ["lamp on", "relay on", "distance", "scan", "logout", "passwd a b"])
def test_emergency_blocks_other_commands_and_driver_heats_up(dut, command):
    to_emergency(dut)
    r = dut.exchange(command)
    assert r.has_code("E005") or r.has_code("E001"), f"'{command}' must be blocked in EMERGENCY:\n{r}"
    assert r.search(r"temp rising: [\d.]+ C -> [\d.]+ C"), f"blocked command must raise driver temperature:\n{r}"


@pytest.mark.tc("TC-ST-10")
def test_emergency_state_query_without_argument_is_blocked(dut):
    """ST-3 lists the ONLY allowed commands; 'state' is not among them, so it must not answer normally."""
    to_emergency(dut)
    r = dut.exchange("state")
    assert r.has_code("E005") or r.has_code("E001"), f"'state' is not allowed in EMERGENCY but answered:\n{r}"


@pytest.mark.tc("TC-ST-11")
@pytest.mark.slow
def test_emergency_overheat_causes_emergency_reboot(dut, reboot_dut):
    """ST-3: every blocked command heats the transducer driver; at 95 C the module reboots."""
    to_emergency(dut)
    rebooted, last_temp = False, None
    for _ in range(25):
        r = dut.exchange("lamp on", idle=0.8, timeout=4)
        m = re.findall(r"-> ([\d.]+) C", r.text)
        if m:
            last_temp = float(m[-1])
        if "ESP-ROM" in r.text or "ready. state 1 NORMAL" in r.text or "SENTRY SWM-2 sonar watch module" in r.text:
            rebooted = True
            break
    assert rebooted, f"no emergency reboot after 25 blocked commands (last temperature {last_temp} C)"
    dut.wait_for(r"ready\. state 1 NORMAL", 20) if "ready. state 1 NORMAL" not in r.text else None


@pytest.mark.tc("TC-ST-12")
@pytest.mark.parametrize("command", ["state 1", "state 3", "state normal"])
def test_emergency_can_only_be_left_by_reboot(dut, command):
    to_emergency(dut)
    r = dut.exchange(command)
    assert r.has_code("E304"), f"codes {r.codes}\n{r}"


@pytest.mark.tc("TC-ST-14")
def test_repeated_transition_gives_w303(dut):
    assert dut.exchange("state 1").has_code("W303")  # already NORMAL
    dut.exchange("state 2")
    assert dut.exchange("state 2").has_code("W303")


@pytest.mark.tc("TC-ST-15", "TC-AU-15")
@pytest.mark.parametrize("start", ["2", "3"])
def test_logout_returns_to_normal_and_switches_outputs_off(dut, settings, start):
    dut.exchange(f"state {start}")
    dut.exchange("lamp on")
    dut.exchange("relay on")
    r = dut.exchange("logout")
    assert r.has("(by logout)") and r.has("[BEACON] off") and r.has("CLOSED"), f"logout must reset state, lamp and relay:\n{r}"
    assert dut.exchange("status").search(r"state:\s+1 NORMAL")
    assert dut.exchange("status").search(r"valve:\s+closed")


@pytest.mark.tc("TC-ST-16")
def test_state_after_reboot_is_always_normal(dut, reboot_dut, settings):
    dut.exchange("state 3")
    boot = reboot_dut()
    assert "ready. state 1 NORMAL" in boot.text
