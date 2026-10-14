"""Relay: schedule (RL-4), auto mode (RL-5), health/wear report (RL-6)."""

import pytest

pytestmark = [pytest.mark.functional]


@pytest.mark.tc("TC-RL-12")
def test_schedule_starts_the_cycle_and_can_be_stopped(dut):
    r = dut.exchange("relay schedule 2 2")
    assert r.has("schedule: 2 s on / 2 s off")
    assert dut.exchange("relay schedule off").has("schedule stopped")


@pytest.mark.tc("TC-RL-12")
def test_schedule_off_when_not_running_gives_w605(dut):
    assert dut.exchange("relay schedule off").has_code("W605")


@pytest.mark.tc("TC-RL-13")
def test_relay_auto_toggle(dut):
    assert dut.exchange("relay auto on").has("auto on")
    assert dut.exchange("relay status").has("auto on")
    assert dut.exchange("relay auto off").has("auto off")
    assert dut.exchange("relay status").has("auto off")


@pytest.mark.tc("TC-RL-14")
def test_relay_health_report_format(dut):
    r = dut.exchange("relay health")
    assert r.search(r"seal: \d+ / 100000 cycles, wear [\d.]+% \(\w+\)"), r
    assert r.has("solenoid:") and r.has("contact resistance")
