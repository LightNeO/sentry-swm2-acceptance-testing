"""Active sonar HC-SR04: calibration, alarm, filter, stats/history (DS-3..DS-6)."""

import pytest

from drivers.protocol import ErrorCode

pytestmark = [pytest.mark.functional]


@pytest.mark.tc("TC-DS-07")
@pytest.mark.parametrize("ref,error", [(4, ErrorCode.E706), (5, None), (300, None), (301, ErrorCode.E706)])
def test_calibrate_range(dut, ref, error):
    r = dut.sonar.calibrate(ref, idle=1.0)
    if error:
        assert r.has_code(error), f"ref={ref}: expected {error}, got {r.codes}\n{r}"
    else:
        assert not r.errors, f"ref={ref} must be accepted:\n{r}"
    dut.sonar.calibrate_reset()


@pytest.mark.tc("TC-DS-07")
def test_calibrate_computes_an_offset_against_the_reference(dut):
    r = dut.sonar.calibrate(20, idle=1.5)
    assert r.has("calibrating") and r.has("20.0 cm")
    assert r.search(r"calibrated: measured [\d.]+ cm, offset [+-][\d.]+ cm"), r
    dut.sonar.calibrate_reset()


@pytest.mark.tc("TC-DS-09")
def test_alarm_set_and_cleared(dut):
    assert dut.sonar.set_alarm(30).has("alarm at 30 cm")
    assert dut.sonar.alarm_off().has("alarm off")


@pytest.mark.tc("TC-DS-05a", "TC-DS-05b")
def test_filter_toggle_and_stats_history_are_consistent_when_empty(dut):
    assert dut.sonar.set_filter(False).has("filter off")
    assert dut.sonar.set_filter(True).has("filter on (median of 5)")
    # A freshly logged-in session (new 'dut' fixture instance) has not measured yet.
    assert dut.sonar.stats().has("no measurements yet")
    assert dut.sonar.history().has("history is empty")


@pytest.mark.tc("TC-DS-12", "TC-DS-13")
def test_stats_and_history_after_measurements(dut):
    dut.sonar.measure(6, idle=1.5, timeout=20)
    stats = dut.sonar.stats()
    assert stats.search(r"measurements \d+, errors \d+"), f"'distance stats' must report counts after 6 measurements:\n{stats}"
    history = dut.sonar.history()
    assert not history.has("history is empty"), history
