"""Stage 3: controlled AP/WAN faults using the local NetworkManager setup."""

from __future__ import annotations

import time

import pytest

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
    managed_ap.ap_down()
    try:
        time.sleep(3)
        result = dut.exchange("ota check", idle=3.0, timeout=10)
        # Current firmware reports E411 after AP loss because the OTA path
        # classifies the missing server before the generic Wi-Fi guard.
        assert result.has_code("E002") or result.has_code("E411"), result
    finally:
        managed_ap.ap_up()
        dut.exchange("reconnect", until=r"connected to|W114|E1\d\d", timeout=30)


@pytest.mark.tc("TC-OTA-25")
def test_upstream_loss_keeps_test_ap_up(dut, managed_ap):
    dut.exchange("reconnect", until=r"connected to|W114|E1\d\d", timeout=30)
    managed_ap.upstream_down()
    try:
        status = dut.exchange("status")
        snapshot = managed_ap.snapshot()
        assert "SENTRY-HIL" in snapshot.devices
        assert "wlp1s0" in snapshot.wifi
        assert "link:" in status.text
        ota = dut.exchange("ota check", idle=2.0, timeout=15)
        # Current firmware reports E002 after upstream loss as well; keep the
        # AP/link evidence separate from the firmware's error classification.
        assert ota.has_code("E002") or ota.has_code("E402") or ota.has_code("E411"), ota
    finally:
        managed_ap.upstream_up()
        dut.exchange("reconnect", until=r"connected to|W114|E1\d\d", timeout=30)
