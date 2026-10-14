"""SENTRY Guard (perimeter watch), 2.3.0 only (GD-1..GD-5). Formats below from manual exploration (logs/research/guard_explore*.txt).

  guard status  -> "[WATCH] disarmed|arming|ARMED|INTRUSION|ALARM, zone N cm, last distance X cm"
  guard arm     -> "arming: clear the zone..." + 10s countdown
  guard disarm  -> "disarmed" / not armed W802 / wrong pin E803 "Attempts: N/3"
  guard pin     -> "PIN changed" / wrong old E803 / bad format E804 / while armed E807
  guard zone    -> "[WATCH] zone < N cm" / out of range E808

Only runs on fw >= 2.3.0 (since_2_3_0 marker skips on 2.1.0, where 'guard ...' should be E099).
"""

import time

import pytest

from conftest import login_waiting_out_lockout

pytestmark = [pytest.mark.functional, pytest.mark.since_2_3_0]

DEFAULT_PIN = "1234"


@pytest.fixture
def guard_clean(dut):
    """Guard disarmed, PIN back to the documented default, zone back to default 50 cm."""
    dut.exchange("guard disarm " + DEFAULT_PIN, idle=0.8)  # ignore result: may already be disarmed
    r = dut.exchange("guard status")
    if "disarmed" not in r.text:
        # PIN may not be the default from a previous test; try the two PINs this suite ever sets.
        for pin in ("4321", "0000", DEFAULT_PIN):
            dut.exchange(f"guard disarm {pin}", idle=0.8)
    dut.exchange(f"guard pin {DEFAULT_PIN} {DEFAULT_PIN}", idle=0.8)  # no-op if already default; ignore E803
    dut.exchange("guard zone 50")
    dut.exchange("alert ack all", idle=0.8)
    dut.exchange("alert clear", idle=0.8)  # isolate from CIC alerts left by earlier Guard/Alert tests
    yield dut
    dut.exchange("guard disarm " + DEFAULT_PIN, idle=0.8)


@pytest.mark.tc("TC-GD-01")
def test_guard_status_default(guard_clean):
    r = guard_clean.exchange("guard status")
    assert r.search(r"disarmed, zone 50 cm"), r


@pytest.mark.tc("TC-GD-05")
@pytest.mark.parametrize("cm,error", [(9, "E808"), (10, None), (200, None), (201, "E808")])
def test_guard_zone_range(guard_clean, cm, error):
    r = guard_clean.exchange(f"guard zone {cm}")
    if error:
        assert r.has_code(error), f"zone={cm}: expected {error}, got {r.codes}\n{r}"
    else:
        assert not r.errors, f"zone={cm} must be accepted:\n{r}"


@pytest.mark.tc("TC-GD-02")
def test_arm_has_10s_exit_delay_then_armed(guard_clean):
    r = guard_clean.exchange("guard arm", idle=1.5)
    assert r.has("arming") and r.has("10 s")
    time.sleep(11)
    status = guard_clean.exchange("guard status")
    assert "arming" not in status.text, f"must have left the arming countdown after 10 s:\n{status}"


@pytest.mark.tc("TC-GD-20")
def test_arm_while_already_arming_gives_w801(guard_clean):
    guard_clean.exchange("guard arm")
    r = guard_clean.exchange("guard arm")
    assert r.has_code("W801")


@pytest.mark.tc("TC-GD-21")
def test_disarm_when_not_armed_gives_w802(guard_clean):
    assert guard_clean.exchange("guard disarm " + DEFAULT_PIN).has_code("W802")


@pytest.mark.tc("TC-GD-22")
def test_disarm_during_arming_delay_cancels_it(guard_clean):
    guard_clean.exchange("guard arm")
    r = guard_clean.exchange(f"guard disarm {DEFAULT_PIN}")
    assert r.has("disarmed"), r
    assert "arming" not in guard_clean.exchange("guard status").text


@pytest.mark.tc("TC-GD-14")
@pytest.mark.parametrize("new_pin,error", [("123", "E804"), ("12345", "E804"), ("abcd", "E804"), ("0000", None)])
def test_pin_format_validation(guard_clean, new_pin, error):
    r = guard_clean.exchange(f"guard pin {DEFAULT_PIN} {new_pin}")
    try:
        if error:
            assert r.has_code(error), f"new_pin={new_pin!r}: expected {error}, got {r.codes}\n{r}"
        else:
            assert r.has("PIN changed"), r
    finally:
        if not error:
            restore = guard_clean.exchange(f"guard pin {new_pin} {DEFAULT_PIN}")
            assert restore.has("PIN changed"), f"could not restore default PIN:\n{restore}"


@pytest.mark.tc("TC-GD-13")
def test_wrong_old_pin_is_rejected_and_pin_unchanged(guard_clean):
    r = guard_clean.exchange("guard pin 9999 4321")
    assert r.has_code("E803"), r
    # the default PIN must still work afterwards
    guard_clean.exchange("guard arm")
    assert guard_clean.exchange(f"guard disarm {DEFAULT_PIN}").has("disarmed")


@pytest.mark.tc("TC-GD-15")
def test_pin_change_while_armed_gives_e807(guard_clean):
    guard_clean.exchange("guard arm")
    r = guard_clean.exchange(f"guard pin {DEFAULT_PIN} 4321")
    assert r.has_code("E807"), r
    guard_clean.exchange(f"guard disarm {DEFAULT_PIN}")


@pytest.mark.tc("TC-GD-03", "TC-GD-04")
@pytest.mark.slow
def test_intrusion_escalates_to_alarm_after_15s_without_disarm(guard_clean):
    """GD-2: no disarm within 15 s of INTRUSION -> ALARM, regardless of PIN attempts."""
    guard_clean.exchange("guard zone 300")  # widest zone: whatever is in front of the sensor counts as intrusion
    guard_clean.exchange("guard arm")
    time.sleep(11)
    status = guard_clean.exchange("guard status")
    assert status.has("INTRUSION"), f"expected INTRUSION after arming with a wide-open zone:\n{status}"
    time.sleep(16)
    status = guard_clean.exchange("guard status")
    assert status.has("ALARM"), f"expected ALARM 15 s after INTRUSION with no disarm:\n{status}"
    assert guard_clean.exchange(f"guard disarm {DEFAULT_PIN}").has("disarmed"), "must be able to disarm an active ALARM"


@pytest.mark.tc("TC-GD-06")
def test_panic_triggers_alarm_immediately(guard_clean):
    guard_clean.exchange("guard arm")
    time.sleep(11)
    r = guard_clean.exchange("guard panic", idle=1.0)
    status = guard_clean.exchange("guard status")
    assert status.has("ALARM"), f"'guard panic' must force ALARM:\n{r}\n{status}"
    guard_clean.exchange(f"guard disarm {DEFAULT_PIN}")


@pytest.mark.tc("TC-GD-16")
def test_guard_log_lists_recent_events(guard_clean):
    guard_clean.exchange("guard arm")
    guard_clean.exchange(f"guard disarm {DEFAULT_PIN}")
    r = guard_clean.exchange("guard log", idle=1.5)
    assert r.search(r"\d+\.\s+\S+\s+(arming|disarmed)"), r


@pytest.mark.tc("TC-GD-17")
def test_logout_does_not_disarm_guard(guard_clean, settings):
    guard_clean.exchange("guard arm")
    time.sleep(11)
    guard_clean.logout()
    guard_clean.login(settings["login"], settings["password"])
    status = guard_clean.exchange("guard status")
    assert "disarmed" not in status.text.split("\n")[0], f"logout must not disarm Guard (GD-5c):\n{status}"
    guard_clean.exchange(f"guard disarm {DEFAULT_PIN}")


@pytest.fixture
def guard_fresh(guard_clean, reboot_dut, settings):
    """Guard test that starts with a rebooted board, so the wrong-PIN counter does not carry over from earlier tests."""
    reboot_dut()
    login_waiting_out_lockout(guard_clean, settings["login"], settings["password"])
    return guard_clean


def _arm_and_wait(dev):
    """Arm and wait for ARMED. Needs a stand object 15-200 cm in front of the sensor: with nothing in front
    there is no echo (arm gives E805), with the object inside the zone the guard goes straight to INTRUSION."""
    dev.exchange("guard zone 10")  # smallest zone, so the stand object is outside it
    dev.exchange("distance", idle=1.5)  # no passive sonar monitoring: arm gives E805 until a reading exists
    r = dev.exchange("guard arm", idle=1.5)
    assert not r.has_code("E805"), r
    time.sleep(11)  # exit delay is 10 s
    status = dev.exchange("guard status")
    assert status.has("ARMED"), f"expected ARMED after the exit delay (is something in the zone?):\n{status}"


@pytest.mark.tc("TC-GD-12")
@pytest.mark.slow
def test_wrong_pin_counter_starts_from_zero_after_correct_pin_and_new_arm(guard_fresh):
    guard_clean = guard_fresh
    _arm_and_wait(guard_clean)
    assert guard_clean.exchange("guard disarm 0000").search(r"Attempts: 1/3")
    assert guard_clean.exchange("guard disarm 0000").search(r"Attempts: 2/3")
    assert guard_clean.exchange(f"guard disarm {DEFAULT_PIN}").has("disarmed")
    _arm_and_wait(guard_clean)
    r = guard_clean.exchange("guard disarm 0000")
    assert r.search(r"Attempts: 1/3"), f"counter must start from zero on a new arm:\n{r}"
    assert "ALARM" not in guard_clean.exchange("guard status").text


@pytest.mark.tc("TC-GD-11")
@pytest.mark.slow
def test_two_wrong_pins_twice_in_a_row_do_not_raise_alarm(guard_fresh):
    """Two wrong PINs, correct PIN, arm again, two more wrong PINs: still no ALARM (counter was reset)."""
    _arm_and_wait(guard_fresh)
    guard_fresh.exchange("guard disarm 0000")
    guard_fresh.exchange("guard disarm 0000")
    guard_fresh.exchange(f"guard disarm {DEFAULT_PIN}")
    _arm_and_wait(guard_fresh)
    first = guard_fresh.exchange("guard disarm 0000")
    second = guard_fresh.exchange("guard disarm 0000")
    assert first.search(r"Attempts: 1/3"), first
    assert second.search(r"Attempts: 2/3"), second
    assert "ALARM" not in guard_fresh.exchange("guard status").text
