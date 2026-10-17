"""Network fault cases around OTA; the OTA server remains a separate fixture."""

import pytest


pytestmark = pytest.mark.managed_wifi


@pytest.mark.tc("TC-OTA-23")
def test_unreachable_ota_server_returns_e402(dut, managed_ap):
    dut.exchange("ota server http://192.0.2.1:8000/fw7/")
    try:
        result = dut.exchange("ota check", timeout=15)
        assert result.has_code("E402"), result
    finally:
        dut.exchange("ota server default")


@pytest.mark.tc("TC-OTA-26")
def test_unreachable_ota_path_returns_e405(dut, managed_ap):
    result = dut.exchange("ota url http://192.0.2.1:8000/not-found.bin", timeout=15)
    assert result.has_code("E405"), result


@pytest.mark.tc("TC-OTA-31")
def test_custom_ota_server_is_saved_by_device(dut, managed_ap):
    result = dut.exchange("ota server http://10.42.0.1:8000/fw7/")
    try:
        assert not result.has_code("E001"), result
        status = dut.exchange("ota server")
        assert "10.42.0.1:8000" in status.text
    finally:
        dut.exchange("ota server default")
