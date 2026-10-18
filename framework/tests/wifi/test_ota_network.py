"""Network fault cases around OTA."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest


pytestmark = pytest.mark.managed_wifi


class NotFoundHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib handler API
        self.send_response(404)
        self.end_headers()

    def log_message(self, *_args):
        pass


@pytest.fixture
def missing_ota_server():
    # UFW already permits 53317 on the test interface; avoid changing firewall
    # rules just to allocate a temporary high port.
    server = ThreadingHTTPServer(("10.42.0.1", 53317), NotFoundHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://10.42.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.tc("TC-OTA-23")
def test_unreachable_ota_server_returns_e402(dut, managed_ap):
    # Port 53317 is allowed by the test-interface firewall, but no server is
    # started for this case, so the DUT gets a quick connection refusal.
    dut.exchange("ota server http://10.42.0.1:53317/fw7/")
    try:
        result = dut.exchange("ota check", timeout=15)
        assert result.has_code("E402"), result
    finally:
        dut.exchange("ota server default")


@pytest.mark.tc("TC-OTA-26")
def test_unreachable_ota_path_returns_e405(dut, managed_ap, missing_ota_server):
    result = dut.exchange(f"ota url {missing_ota_server}/not-found.bin", timeout=15)
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
