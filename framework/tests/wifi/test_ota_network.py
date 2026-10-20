"""Network fault cases around OTA."""

import pytest

from tests.helpers import wait_link


pytestmark = pytest.mark.managed_wifi

CUSTOM_OTA_PORT = 8000


def _restore_default_server(dut) -> None:
    """'ota server default' needs Wi-Fi: if the link dropped meanwhile (seen on the stand), bring it back and retry,
    so a custom server is never left saved on the board."""
    for _ in range(3):
        if not dut.exchange("ota server default").has_code("E002"):
            return
        wait_link(dut)


@pytest.mark.tc("TC-OTA-23")
def test_unreachable_ota_server_returns_e402(dut, managed_ap, stand):
    # Port 53317 is allowed by the test-interface firewall, but no server is
    # started for this case, so the DUT gets a quick connection refusal.
    wait_link(dut)
    dut.exchange(f"ota server http://{stand.ap_address}:{stand.ota_port}/fw7/")
    try:
        result = dut.exchange("ota check", timeout=15)
        assert result.has_code("E402"), result
    finally:
        _restore_default_server(dut)


@pytest.mark.tc("TC-OTA-26")
def test_unreachable_ota_path_returns_e405(dut, managed_ap, missing_ota_server):
    result = dut.exchange(f"ota url {missing_ota_server}/not-found.bin", timeout=15)
    assert result.has_code("E405"), result


@pytest.mark.tc("TC-OTA-31")
def test_custom_ota_server_is_saved_by_device(dut, managed_ap, stand):
    custom = f"{stand.ap_address}:{CUSTOM_OTA_PORT}"  # only saved by the board, nothing has to listen there
    status = None
    try:
        # The link can drop between the two commands (then the server is not saved and E002 is answered): retry.
        for _ in range(3):
            wait_link(dut)
            result = dut.exchange(f"ota server http://{custom}/fw7/")
            assert not result.has_code("E001"), result
            status = dut.exchange("ota server")
            if custom in status.text:
                break
        assert custom in status.text, status
    finally:
        _restore_default_server(dut)
