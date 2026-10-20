"""Fixtures for the managed Wi-Fi stage: the NetworkManager-controlled AP/upstream and the OTA servers."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from drivers.config import Settings, StandConfig
from drivers.managed_ap import ManagedAp
from drivers.ota_server_process import OtaServerProcess, firmware_available

SLOW_KB_S = 20  # speed of the slow OTA server, KB/s


@pytest.fixture(scope="session")
def stand() -> StandConfig:
    return StandConfig.from_env()


@pytest.fixture(autouse=True)
def wifi_baseline(device_session, settings: Settings) -> ManagedAp:
    controller = ManagedAp()
    controller.ensure_baseline()
    if not device_session.link_up():
        device_session.ensure_wifi("known network", settings.ssid, settings.wifi_password)
    try:
        yield controller
    finally:
        controller.cleanup()
        if not device_session.link_up():
            device_session.ensure_wifi("known network", settings.ssid, settings.wifi_password)


@pytest.fixture
def managed_ap(wifi_baseline: ManagedAp) -> ManagedAp:
    return wifi_baseline


class _NotFoundHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib handler API
        self.send_response(404)
        self.end_headers()

    def log_message(self, *_args):
        pass


@pytest.fixture
def missing_ota_server(stand: StandConfig):
    """An HTTP server that answers 404 to everything (a reachable server without the requested file)."""
    # UFW already permits the OTA port on the test interface; avoid changing firewall rules just to allocate one.
    server = ThreadingHTTPServer((stand.ap_address, stand.ota_port), _NotFoundHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{stand.ap_address}:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def slow_ota_server(dut, stand: StandConfig):
    """The local OTA server throttled to SLOW_KB_S; ``image_url`` is the image the board already runs (never a downgrade)."""
    version = dut.fw_version
    if not firmware_available(version):
        pytest.skip(f"no server image for v{version}: run `python fw_7/tools/ota_server.py --download` first")
    with OtaServerProcess(stand.ota_port, slow_kb_s=SLOW_KB_S) as server:
        server.image_url = f"http://{stand.ap_address}:{stand.ota_port}/fw7/v{version}/sentry_fw7.bin"
        yield server
