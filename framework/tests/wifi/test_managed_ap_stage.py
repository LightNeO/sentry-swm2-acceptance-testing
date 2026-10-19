"""Stage 3: controlled AP/WAN faults using the local NetworkManager setup."""

from __future__ import annotations

import time

import pytest

from tests.helpers import wait_link

pytestmark = pytest.mark.managed_wifi


@pytest.mark.tc("TC-WF-18")
def test_ap_loss_emits_wifi_loss_and_recovers(dut, managed_ap):
    recovered = None
    managed_ap.ap_down()
    try:
        loss = dut.wait_for(r"W110 wifi connection lost", timeout=15)
        assert "W110" in loss.text
    finally:
        managed_ap.ap_up()
        recovered = dut.exchange("reconnect", until=r"connected to|W114|E1\d\d", timeout=30)

    assert recovered.search(r"connected to|fleet network reachable|already connected") or recovered.has_code("E101"), recovered


@pytest.mark.tc("TC-OTA-25")
def test_ap_loss_makes_ota_check_require_wifi(dut, managed_ap):
    """AP down: until the firmware notices (W110) it still thinks it is connected and answers E402 on 'ota check';
    once the loss is reported the Wi-Fi guard must answer E002 (AC-1b)."""
    managed_ap.ap_down()
    try:
        dut.wait_for(r"W110 wifi connection lost", timeout=30)
        result = dut.exchange("ota check", idle=3.0, timeout=15)
        assert result.has_code("E002"), result
    finally:
        managed_ap.ap_up()
        wait_link(dut)


@pytest.mark.tc("TC-OTA-25")
def test_upstream_loss_keeps_test_ap_up(dut, managed_ap):
    """Upstream (WAN) down with the test AP up. Observed on the stand: NetworkManager's shared AP blips when the
    upstream goes down, so the DUT may log W110 and re-associate. Wait for the link to settle first, then
    'ota check' has to report the server as unreachable (E402), not E002 (the Wi-Fi link is up)."""
    wait_link(dut)
    managed_ap.upstream_down()
    try:
        snapshot = managed_ap.snapshot()
        assert "SENTRY-HIL" in snapshot.devices
        assert "wlp1s0" in snapshot.wifi
        time.sleep(5)  # let the AP blip (if any) and the DUT's re-association pass
        assert wait_link(dut), "DUT did not get its Wi-Fi link back after the upstream went down"
        ota = dut.exchange("ota check", until=r"E\d{3}|\[OTA\] stable", timeout=30)
        assert ota.has_code("E402"), ota
    finally:
        managed_ap.upstream_up()
        wait_link(dut)
