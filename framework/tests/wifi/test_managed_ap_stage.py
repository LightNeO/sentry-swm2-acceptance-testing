"""Stage 3: controlled AP/WAN faults using the local NetworkManager setup."""

from __future__ import annotations

import os
import time

import pytest

from drivers.managed_ap import ManagedAp


pytestmark = [
    pytest.mark.managed_wifi,
    pytest.mark.skipif(
        not os.environ.get("HIL_AP_CONNECTION"),
        reason="set HIL_AP_CONNECTION to run the destructive managed Wi-Fi stage",
    ),
]


@pytest.fixture
def managed_ap():
    controller = ManagedAp()
    controller.ensure_baseline()
    try:
        yield controller
    finally:
        controller.cleanup()


@pytest.mark.tc("TC-WF-18")
def test_ap_loss_emits_wifi_loss_and_recovers(dut, managed_ap):
    managed_ap.ap_down()
    try:
        loss = dut.wait_for(r"W110 wifi connection lost", timeout=15)
        assert "W110" in loss.text
    finally:
        managed_ap.ap_up()

    time.sleep(2)
    recovered = dut.exchange("reconnect", until=r"connected to|E1\d\d", timeout=30)
    assert recovered.search(r"connected to") or recovered.has_code("E101"), recovered


@pytest.mark.tc("TC-OTA-25")
def test_ap_loss_makes_ota_check_require_wifi(dut, managed_ap):
    managed_ap.ap_down()
    try:
        result = dut.exchange("ota check", idle=1.0)
        assert result.has_code("E002"), result
    finally:
        managed_ap.ap_up()


@pytest.mark.tc("TC-OTA-25")
def test_upstream_loss_keeps_test_ap_up(dut, managed_ap):
    managed_ap.upstream_down()
    try:
        status = dut.exchange("status")
        snapshot = managed_ap.snapshot()
        assert "SENTRY-HIL" in snapshot.devices
        assert "wlp1s0" in snapshot.wifi
        assert "link:" in status.text
        ota = dut.exchange("ota check", idle=2.0, timeout=15)
        assert ota.has_code("E402") or ota.has_code("E411"), ota
    finally:
        managed_ap.upstream_up()
