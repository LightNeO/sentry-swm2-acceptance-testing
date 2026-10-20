"""Relay switch counter (RL-2) and automatic telemetry intervals (HL-1a)."""

import time

import pytest

from tests.helpers import relay_cycles, telemetry_intervals_ms
from tests.functional.test_states import to_emergency

pytestmark = [pytest.mark.functional]

RATE_LIMIT_PAUSE = 1.1  # PRD RL-1: at most 2 switches per second (E602), so keep clear of it


@pytest.mark.tc("TC-RL-05")
def test_each_relay_switch_adds_exactly_one_to_cycles(dut):
    """RL-2: one switch on OR off = +1."""
    start = relay_cycles(dut)
    dut.exchange("relay on")
    after_on = relay_cycles(dut)
    time.sleep(RATE_LIMIT_PAUSE)
    dut.exchange("relay off")
    after_off = relay_cycles(dut)
    assert after_on - start == 1, f"'relay on' must add 1 to cycles, added {after_on - start} ({start} -> {after_on})"
    assert after_off - after_on == 1, f"'relay off' must add 1 to cycles, added {after_off - after_on} ({after_on} -> {after_off})"


@pytest.mark.tc("TC-RL-06")
@pytest.mark.persistence
def test_cycles_counter_survives_reboot(dut, reboot_dut, settings):
    before = relay_cycles(dut)
    reboot_dut()
    assert dut.login(settings.login, settings.password).has("on watch")
    assert relay_cycles(dut) == before


@pytest.mark.tc("TC-RL-02")
def test_relay_status_format(dut):
    assert dut.exchange("relay status").search(r"\[VALVE\] (closed|OPEN), auto (on|off), cycles \d+")


@pytest.mark.tc("TC-RL-02")
def test_relay_switch_rate_limit_gives_e602(dut):
    codes = []
    for cmd in ("relay on", "relay off", "relay on"):  # three switches within a fraction of a second
        codes += dut.exchange(cmd, idle=0.15, timeout=1.5).codes
    assert "E602" in codes, f"third switch within 1 s must give E602, got {codes}"


@pytest.mark.tc("TC-HL-01")
@pytest.mark.slow
def test_health_report_interval_in_normal_is_30_s(dut):
    ticks = telemetry_intervals_ms(dut.read_for(70))
    assert len(ticks) >= 1, "fewer than 2 reports in 70 s"
    assert all(28000 <= t <= 32000 for t in ticks), f"NORMAL interval must be 30 s, got {ticks} ms"


@pytest.mark.tc("TC-HL-02")
@pytest.mark.slow
def test_health_report_interval_in_verbose_is_10_s(dut):
    dut.exchange("state 3")
    ticks = telemetry_intervals_ms(dut.read_for(35))
    assert len(ticks) >= 2, "fewer than 3 reports in 35 s"
    assert all(9000 <= t <= 11000 for t in ticks), f"VERBOSE interval must be 10 s, got {ticks} ms"


@pytest.mark.tc("TC-HL-03")
@pytest.mark.slow
def test_health_report_interval_in_emergency_is_5_s(dut):
    to_emergency(dut)
    ticks = telemetry_intervals_ms(dut.read_for(25))
    assert len(ticks) >= 2, "fewer than 3 reports in 25 s"
    assert all(4000 <= t <= 6000 for t in ticks), f"EMERGENCY interval must be 5 s, got {ticks} ms"
