"""CIC Alert center, 2.3.0 only (AL-1..AL-5).

  alert list    -> "no alerts" | "N alerts, M unacknowledged:" + rows, '*' = unacked
  alert test    -> "[CIC #id LEVEL] test: test alert"; critical also opens valve + forces VERBOSE
  alert ack     -> "#id acknowledged. Unacked: N" (no id = last one)
  alert clear   -> E855 if anything unacked, else "cleared"
"""

import pytest

pytestmark = [pytest.mark.functional, pytest.mark.since_2_3_0]


@pytest.mark.tc("TC-AL-10")
@pytest.mark.parametrize("level,error", [("info", None), ("warning", None), ("critical", None), ("foo", "E854"), ("", "E854")])
def test_alert_test_levels(alerts_clean, level, error):
    r = alerts_clean.exchange(f"alert test {level}".rstrip(), idle=1.5)
    if error:
        assert r.has_code(error), f"level={level!r}: expected {error}, got {r.codes}\n{r}"
    else:
        assert r.search(rf"\[CIC #\d+ {level.upper()}\] test: test alert"), r


def alert_id(response) -> str:
    """The '#id' from an 'alert test ...' response. IDs just keep counting, never reset - don't assume 1/2/3."""
    m = response.search(r"\[CIC #(\d+)")
    assert m, f"could not find an alert id in:\n{response}"
    return m.group(1)


@pytest.mark.tc("TC-AL-01", "TC-AL-03")
def test_alert_format_and_unacked_marker(alerts_clean):
    created = alerts_clean.exchange("alert test info")
    aid = alert_id(created)
    r = alerts_clean.exchange("alert list")
    assert r.search(r"1 alerts, 1 unacknowledged:")
    assert r.search(rf"#{aid}\s+\S+\s+INFO\s+\*\s+test\s+test alert"), r


@pytest.mark.tc("TC-AL-04")
def test_ack_without_id_acknowledges_the_last_one(alerts_clean):
    id1 = alert_id(alerts_clean.exchange("alert test info"))
    id2 = alert_id(alerts_clean.exchange("alert test warning"))
    r = alerts_clean.exchange("alert ack")
    assert r.has(f"#{id2} acknowledged") and r.has("Unacked: 1"), r
    listing = alerts_clean.exchange("alert list").text
    row1 = next(l for l in listing.split("\n") if f"#{id1}" in l)
    assert "*" in row1, f"#{id1} must still be unacked:\n{listing}"


@pytest.mark.tc("TC-AL-05")
def test_ack_by_id_acknowledges_exactly_that_one(alerts_clean):
    id1 = alert_id(alerts_clean.exchange("alert test info"))
    alerts_clean.exchange("alert test warning")  # id2, left unacked on purpose
    alerts_clean.exchange("alert test info")  # id3, left unacked on purpose
    r = alerts_clean.exchange(f"alert ack {id1}")
    assert r.has(f"#{id1} acknowledged") and r.has("Unacked: 2"), r
    listing = alerts_clean.exchange("alert list").text
    row1 = next(l for l in listing.split("\n") if f"#{id1}" in l)
    assert "*" not in row1, f"#{id1} must be acknowledged (no '*'):\n{listing}"


@pytest.mark.tc("TC-AL-06")
def test_ack_unknown_id_gives_e851(alerts_clean):
    id1 = alert_id(alerts_clean.exchange("alert test info"))
    never_used_id = str(int(id1) + 10_000)
    assert alerts_clean.exchange(f"alert ack {never_used_id}").has_code("E851")


@pytest.mark.tc("TC-AL-06")
def test_ack_already_acknowledged_gives_w852(alerts_clean):
    """Uses the SECOND alert, not the first: the first position hits BUG-008 (see test above) and would
    make this test fail for an unrelated reason."""
    alerts_clean.exchange("alert test info")  # position 0 - left alone, see BUG-008
    id2 = alert_id(alerts_clean.exchange("alert test warning"))  # position 1 - ack works here
    ack1 = alerts_clean.exchange(f"alert ack {id2}")
    assert ack1.has(f"#{id2} acknowledged"), ack1
    assert alerts_clean.exchange(f"alert ack {id2}").has_code("W852")


@pytest.mark.tc("TC-AL-07")
def test_ack_all(alerts_clean):
    alerts_clean.exchange("alert test info")
    alerts_clean.exchange("alert test warning")
    r = alerts_clean.exchange("alert ack all")
    assert "Unacked: 0" in r.text or r.has("acknowledged"), r
    assert alerts_clean.exchange("alert ack all").has_code("W853")


@pytest.mark.tc("TC-AL-08")
def test_clear_with_unacked_alerts_gives_e855(alerts_clean):
    alerts_clean.exchange("alert test info")
    r = alerts_clean.exchange("alert clear")
    assert r.has_code("E855"), r
    assert r.has("Use 'alert ack all' first")


@pytest.mark.tc("TC-AL-09")
def test_clear_after_ack_all_succeeds(alerts_clean):
    alerts_clean.exchange("alert test info")
    alerts_clean.exchange("alert ack all")
    r = alerts_clean.exchange("alert clear")
    assert r.has("cleared"), r
    assert alerts_clean.exchange("alert list").has("no alerts")


@pytest.mark.tc("TC-AL-11", "TC-RL-01")
def test_critical_alert_opens_valve_and_forces_verbose(alerts_clean):
    before_state = alerts_clean.exchange("status").search(r"state:\s+(\d \w+)").group(1)
    assert "NORMAL" in before_state or "DEBUG" in before_state, f"test needs to start outside VERBOSE: {before_state}"
    r = alerts_clean.exchange("alert test critical", idle=1.0)
    assert r.has("NORMAL -> 3 VERBOSE") or r.has("DEBUG -> 3 VERBOSE"), r
    assert r.has("[VALVE] OPEN"), r
    assert alerts_clean.exchange("status").search(r"state:\s+3 VERBOSE")
    alerts_clean.exchange("relay off", idle=0.8)  # restore baseline; the AL-5 valve-open is not part of RL-7's logout exemptions
