"""Relay: schedule (RL-4), auto mode (RL-5), health/wear report (RL-6)."""

import pytest

from drivers.protocol import ErrorCode

pytestmark = [pytest.mark.functional]


@pytest.mark.tc("TC-RL-12")
def test_schedule_starts_the_cycle_and_can_be_stopped(dut):
    r = dut.relay.schedule(2, 2)
    assert r.has("schedule: 2 s on / 2 s off")
    assert dut.relay.stop_schedule().has("schedule stopped")


@pytest.mark.tc("TC-RL-12")
def test_schedule_off_when_not_running_gives_w605(dut):
    assert dut.relay.stop_schedule().has_code(ErrorCode.W605)


@pytest.mark.tc("TC-RL-13")
def test_relay_auto_toggle(dut):
    assert dut.relay.auto(True).has("auto on")
    assert dut.relay.status().has("auto on")
    assert dut.relay.auto(False).has("auto off")
    assert dut.relay.status().has("auto off")


@pytest.mark.tc("TC-RL-14")
def test_relay_health_report_format(dut):
    r = dut.relay.health()
    assert r.search(r"seal: \d+ / 100000 cycles, wear [\d.]+% \(\w+\)"), r
    assert r.has("solenoid:") and r.has("contact resistance")
