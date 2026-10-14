"""Active sonar HC-SR04: calibration, alarm, filter, stats/history (DS-3..DS-6)."""

import pytest

pytestmark = [pytest.mark.functional]


@pytest.mark.tc("TC-DS-07")
@pytest.mark.parametrize("ref,error", [(4, "E706"), (5, None), (300, None), (301, "E706")])
def test_calibrate_range(dut, ref, error):
    r = dut.exchange(f"distance calibrate {ref}", idle=1.0)
    if error:
        assert r.has_code(error), f"ref={ref}: expected {error}, got {r.codes}\n{r}"
    else:
        assert not r.errors, f"ref={ref} must be accepted:\n{r}"
    dut.exchange("distance calibrate reset")


@pytest.mark.tc("TC-DS-07")
def test_calibrate_computes_an_offset_against_the_reference(dut):
    r = dut.exchange("distance calibrate 20", idle=1.5)
    assert r.has("calibrating") and r.has("20.0 cm")
    assert r.search(r"calibrated: measured [\d.]+ cm, offset [+-][\d.]+ cm"), r
    dut.exchange("distance calibrate reset")


@pytest.mark.tc("TC-DS-09")
def test_alarm_set_and_cleared(dut):
    assert dut.exchange("distance alarm 30").has("alarm at 30 cm")
    assert dut.exchange("distance alarm off").has("alarm off")


@pytest.mark.tc("TC-DS-05a", "TC-DS-05b")
def test_filter_toggle_and_stats_history_are_consistent_when_empty(dut):
    assert dut.exchange("distance filter off").has("filter off")
    assert dut.exchange("distance filter on").has("filter on (median of 5)")
    # A freshly logged-in session (new 'dut' fixture instance) has not measured yet.
    assert dut.exchange("distance stats").has("no measurements yet")
    assert dut.exchange("distance history").has("history is empty")


@pytest.mark.tc("TC-DS-12", "TC-DS-13")
def test_stats_and_history_after_measurements(dut):
    dut.exchange("distance 6", idle=1.5, timeout=20)
    stats = dut.exchange("distance stats")
    assert stats.search(r"measurements \d+, errors \d+"), f"'distance stats' must report counts after 6 measurements:\n{stats}"
    history = dut.exchange("distance history")
    assert not history.has("history is empty"), history
