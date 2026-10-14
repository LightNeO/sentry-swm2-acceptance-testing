"""BVA (min-1/min/max/max+1) for every numeric range in the PRD.

One parametrised function = one TC, rows are (value, expected error or None). In-range rows just
assert no error code - inclusive-boundary bugs show up as those failing.
"""

import time

import pytest

pytestmark = [pytest.mark.functional, pytest.mark.boundary]


def check(dut, command: str, expected_error: str | None, **kw):
    """Assert the command gets rejected with ``expected_error``, or accepted (no error code)."""
    r = dut.exchange(command, **kw)
    if expected_error:
        assert r.has_code(expected_error), f"'{command}': expected {expected_error}, got {r.codes}\n{r}"
    else:
        assert not r.errors, f"'{command}': expected acceptance, got {r.errors}\n{r}"
    return r


@pytest.mark.tc("TC-LM-08")
@pytest.mark.parametrize("value,error", [(-1, "E504"), (0, None), (1, None), (99, None), (100, None), (101, "E504")])
def test_lamp_brightness_range(dut, value, error):
    check(dut, f"lamp brightness {value}", error)
    if not error:  # accepted value must really be applied
        assert dut.exchange("lamp status").has(f"brightness {value}%")


@pytest.mark.tc("TC-LM-05")
@pytest.mark.parametrize(
    "rgb,error",
    [("-1 0 0", "E502"), ("0 0 0", None), ("255 255 255", None), ("256 0 0", "E502"), ("0 256 0", "E502"), ("0 0 256", "E502")],
)
def test_lamp_rgb_range(dut, rgb, error):
    check(dut, f"lamp color {rgb}", error)


@pytest.mark.tc("TC-LM-12")
@pytest.mark.parametrize("seconds,error", [(0, None), (1, None), (3600, None), (3601, "E506"), (-1, "E506")])
def test_lamp_timer_range(dut, seconds, error):
    dut.exchange("lamp on")
    check(dut, f"lamp timer {seconds}", error)
    dut.exchange("lamp timer 0")  # do not leave a running timer behind


@pytest.mark.tc("TC-LM-18")
@pytest.mark.parametrize("slot,error", [(0, "E508"), (1, None), (3, None), (4, "E508")])
def test_lamp_scene_slot_range(dut, slot, error):
    check(dut, f"lamp scene save {slot}", error)


@pytest.mark.tc("TC-HL-09")
@pytest.mark.parametrize("seconds,error", [(9, "E902"), (10, None), (300, None), (301, "E902")])
def test_health_interval_range(dut, seconds, error):
    """PRD HL-3: 10 and 300 are INCLUDED in the valid range."""
    check(dut, f"health interval {seconds}", error)
    dut.exchange("health interval 30")


@pytest.mark.tc("TC-DS-02")
@pytest.mark.parametrize("n,error", [(0, "E704"), (1, None), (20, None), (21, "E704")])
def test_distance_count_range(dut, n, error):
    """PRD DS-1: N = 1..20 inclusive. Valid rows only assert 'not E704' (no echo -> E701 is a separate matter)."""
    r = dut.exchange(f"distance {n}", idle=1.5, timeout=30)
    if error:
        assert r.has_code(error), f"expected {error}, got {r.codes}\n{r}"
    else:
        assert not r.has_code("E704"), f"N={n} must be accepted:\n{r}"


@pytest.mark.tc("TC-DS-04")
@pytest.mark.parametrize("ms,error", [(99, "E705"), (5001, "E705")])
def test_distance_log_interval_rejected_outside_range(dut, ms, error):
    check(dut, f"distance log {ms}", error)


@pytest.mark.tc("TC-DS-04")
@pytest.mark.parametrize("ms", [100, 5000])
def test_distance_log_interval_accepted_at_edges(dut, ms):
    check(dut, f"distance log {ms}", None, idle=0.5)
    dut.exchange("distance stop")


@pytest.mark.tc("TC-DS-09")
@pytest.mark.parametrize("cm,error", [(4, "E708"), (5, None), (300, None), (301, "E708")])
def test_distance_alarm_range(dut, cm, error):
    check(dut, f"distance alarm {cm}", error)
    dut.exchange("distance alarm off")


@pytest.mark.tc("TC-RL-07")
@pytest.mark.parametrize("ms,error", [(99, "E603"), (100, None), (10000, None), (10001, "E603")])
def test_relay_pulse_range(dut, ms, error):
    r = check(dut, f"relay pulse {ms}", error)
    if not error:
        time.sleep(ms / 1000 + 0.5)  # let the pulse finish so the next row starts from relay OFF
    else:
        assert r.has("100-10000"), "E603 text should state the valid range"


@pytest.mark.tc("TC-RL-11")
@pytest.mark.parametrize(
    "args,error",
    [("1 5", "E606"), ("5 1", "E606"), ("3601 5", "E606"), ("5 3601", "E606"), ("2 2", None), ("3600 3600", None)],
)
def test_relay_schedule_range(dut, args, error):
    check(dut, f"relay schedule {args}", error)
    dut.exchange("relay schedule off")


@pytest.mark.tc("TC-ST-02")
@pytest.mark.parametrize("arg", ["0", "5", "-1", "abc"])
def test_state_invalid_argument_does_not_change_state(dut, arg):
    r = dut.exchange(f"state {arg}")
    assert r.errors or r.codes, f"'state {arg}' must be rejected with a code:\n{r}"
    assert dut.exchange("state").search(r"1 NORMAL"), "state must stay NORMAL after a rejected value"
