"""Physical K1-K4 stimulus with UART observation.

These tests are separate from the normal UART suite. They require both DUT and
the Arduino controller and need --run-hil to execute.
"""

from __future__ import annotations

import re
import time

import pytest

pytestmark = [pytest.mark.hil_stage]


MIN_OBJECT_CM = 15.0  # the stand object must be clearly outside the 10 cm guard zone (readings vary by a few cm)


def _event(dut, pattern: str, timeout: float = 3.0) -> str:
    """Wait for one asynchronous button event and return its evidence text."""
    return dut.wait_for(pattern, timeout).text


@pytest.mark.hil_tc("HIL-BTN-01")
def test_k1_press_reaches_beacon_logic(dut, stimulator):
    stimulator.press("K1", 150)
    text = _event(dut, r"\[BEACON\] (?:on|off) \(K1\)")
    assert "(K1)" in text


@pytest.mark.hil_tc("HIL-BTN-02")
def test_k2_press_reaches_valve_logic(dut, stimulator):
    stimulator.press("K2", 150)
    text = _event(dut, r"\[VALVE\] (?:OPEN|CLOSED) \(K2\)")
    assert "(K2)" in text


@pytest.mark.hil_tc("HIL-BTN-02-PULSE")
def test_k2_hold_runs_one_second_pulse(dut, stimulator):
    stimulator.hold("K2", 1700)
    opened = _event(dut, r"\[VALVE\] OPEN \(K2 pulse\)")
    closed = _event(dut, r"\[VALVE\] CLOSED \(pulse end\)", timeout=3.0)
    assert "pulse" in opened
    assert "pulse end" in closed


@pytest.mark.hil_tc("HIL-BTN-03")
def test_k3_starts_and_stops_active_pinging(dut, stimulator):
    stimulator.press("K3", 150)
    _event(dut, r"\[SONAR\]")
    stimulator.press("K3", 150)
    text = _event(dut, r"pinging stopped \(K3\)")
    assert "K3" in text


@pytest.mark.hil_tc("HIL-BTN-04")
@pytest.mark.since_2_3_0
def test_k4_acknowledges_newest_alert(dut, stimulator):
    created = dut.exchange("alert test info")
    assert "[CIC" in created.text
    stimulator.press("K4", 150)
    text = _event(dut, r"acknowledged \(K4\)")
    assert "Unacked:" in text


@pytest.mark.hil_tc("HIL-GD-07")
@pytest.mark.since_2_3_0
def test_k4_long_press_triggers_guard_panic(guard_clean, stimulator):
    """Automates the K4 part; the physical object/sonar setup remains a HIL precondition."""
    guard_clean.exchange("guard zone 10")
    reading = guard_clean.exchange("distance", idle=1.5)
    echo = re.search(r"echo ([\d.]+) cm", reading.text)
    if not echo or float(echo.group(1)) < MIN_OBJECT_CM:
        pytest.skip(
            f"precondition: an object {MIN_OBJECT_CM:.0f}-200 cm in front of HC-SR04 is needed "
            f"(sonar reading: {echo.group(1) + ' cm' if echo else 'no echo'}); with the zone at 10 cm anything closer is INTRUSION"
        )
    armed = guard_clean.exchange("guard arm", idle=1.5)
    assert not armed.has_code("E805"), armed
    time.sleep(11)
    assert guard_clean.exchange("guard status").has("ARMED")

    stimulator.hold("K4", 2200)
    text = _event(guard_clean, r"\[WATCH\] PANIC button \(K4\)", timeout=4.0)
    assert "PANIC" in text
    assert guard_clean.exchange("guard status").has("ALARM")
    guard_clean.exchange("guard disarm 1234")


@pytest.mark.hil_tc("HIL-BTN-05")
def test_k3_k4_combo_enters_verbose(dut, stimulator):
    dut.exchange("state 1")
    stimulator.combo(("K3", "K4"), 2200)
    text = _event(dut, r"\[STATE\] 1 NORMAL -> 3 VERBOSE \(by buttons\)")
    assert "3 VERBOSE" in text


@pytest.mark.hil_tc("HIL-BTN-07")
@pytest.mark.parametrize("button", ("K1", "K2", "K3", "K4"))
def test_buttons_require_login(dut_raw, stimulator, button):
    stimulator.press(button, 150)
    text = _event(dut_raw, r"E003 .*login required")
    assert "E003" in text


@pytest.mark.hil_tc("HIL-BTN-06")
@pytest.mark.parametrize("start_state", [("1", "NORMAL"), ("2", "DEBUG")])
def test_k4_k1_combo_is_refused_outside_verbose(dut, stimulator, start_state):
    number, name = start_state
    dut.exchange(f"state {number}")
    stimulator.combo(("K4", "K1"), 2200)
    text = _event(dut, rf"E302 EMERGENCY can be entered only from 3 VERBOSE \(now {number} {name}\)")
    assert "E302" in text


@pytest.mark.hil_tc("HIL-BTN-10")
def test_k4_k1_combo_enters_emergency_from_verbose(dut, stimulator):
    dut.exchange("state 3")
    stimulator.combo(("K4", "K1"), 2200)
    text = _event(dut, r"\[EMERGENCY\] EMERGENCY SURFACING")
    assert "Module locked" in text


@pytest.mark.hil_tc("HIL-BTN-09")
@pytest.mark.only_2_1_0
def test_k1_k2_k3_are_blocked_in_emergency(dut, stimulator):
    dut.exchange("state 3")
    stimulator.combo(("K4", "K1"), 2200)
    _event(dut, r"\[EMERGENCY\] EMERGENCY SURFACING")
    # ST-3e explicitly covers K1-K3; K4 has Guard/Alert-specific behavior.
    for button in ("K1", "K2", "K3"):
        stimulator.press(button, 150)
        text = _event(dut, r"E005 buttons blocked in EMERGENCY")
        assert "E005" in text
