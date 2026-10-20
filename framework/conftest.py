"""pytest glue: fixtures, evidence logs, results.json recording.

Fixture chain for hardware tests: device_session (once) -> dut_raw (baseline, per test) -> dut (+logged in).
Unit tests don't touch any of this.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

import pytest

from drivers.config import Settings, load_env
from drivers.device_driver import SwmDevice, has_saved_network
from drivers.redaction import Redactor
from drivers.transport import SerialTransport, find_port
from tests.helpers import wait_internet

FRAMEWORK_DIR = Path(__file__).resolve().parent
ROOT = FRAMEWORK_DIR.parent
RESULTS_FILE = ROOT / "docs" / "results.json"
LOG_DIR = ROOT / "logs" / "auto"


load_env()

# what the session learned about the DUT, shared with the reporting hooks
FW_KEY = pytest.StashKey[str]()  # firmware key of the run: "2.1.0" -> "21"
RESULTS_KEY = pytest.StashKey[dict]()  # TC id -> PASS/FAIL for --record


# --------------------------------------------------------------------------- options and hooks
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--keep-logs", action="store_true", help="write a transcript for every test, not only failed ones")
    parser.addoption("--record", action="store_true", help="record PASS/FAIL per TC into docs/results.json (for traceability)")
    parser.addoption("--run-hil", action="store_true", help="run the physical Arduino/DUT HIL stage")
    parser.addoption("--run-managed-wifi", action="store_true", help="run the destructive NetworkManager Wi-Fi stage")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Stand stages are opt-in: they drive real hardware (Arduino) or toggle the laptop's network."""
    run_hil = config.getoption("--run-hil")
    run_wifi = config.getoption("--run-managed-wifi") and os.environ.get("HIL_AP_CONNECTION")
    skip_hil = pytest.mark.skip(reason="physical HIL stage requires --run-hil")
    skip_wifi = pytest.mark.skip(reason="managed Wi-Fi stage requires --run-managed-wifi and HIL_AP_CONNECTION")
    for item in items:
        if not run_hil and item.get_closest_marker("hil_stage"):
            item.add_marker(skip_hil)
        if not run_wifi and item.get_closest_marker("managed_wifi"):
            item.add_marker(skip_wifi)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Stash each phase's report on item.rep_<phase> (fixtures check this for pass/fail)."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
    if rep.when == "call" and item.config.getoption("--record"):
        if item.config.stash.get(FW_KEY, None):
            bucket = item.config.stash.setdefault(RESULTS_KEY, {})
            for marker in item.iter_markers("tc"):
                for tc in marker.args:
                    status = {"passed": "PASS", "failed": "FAIL"}.get(rep.outcome)
                    if status:
                        old = bucket.get(tc)
                        bucket[tc] = "FAIL" if "FAIL" in (old, status) else status


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Merge recorded statuses into docs/results.json (traceability.md gets regenerated from this later)."""
    config = session.config
    bucket = config.stash.get(RESULTS_KEY, None)
    fwkey = config.stash.get(FW_KEY, None)
    if not bucket or not fwkey:
        return
    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8")) if RESULTS_FILE.exists() else {}
    for tc, status in bucket.items():
        data.setdefault(tc, {})[fwkey] = status
    RESULTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- configuration
@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_env()


# --------------------------------------------------------------------------- hardware session
INTERNET_WAIT_S = 40.0


@pytest.fixture(scope="session")
def device_session(request: pytest.FixtureRequest, settings: Settings):
    """Open the DUT once per run, bring it to: Wi-Fi up, profile registered, logged out."""
    port = os.environ.get("SWM_PORT") or find_port()
    redactor = Redactor([settings.wifi_password])
    device = SwmDevice(SerialTransport(port), redactor)
    try:
        boot = device.hard_reset()
        version = device.version()
        request.config.stash[FW_KEY] = "".join(version.split(".")[:2])  # "2.1.0" -> "21"
        if not has_saved_network(boot.text) and not (settings.ssid and settings.wifi_password):
            pytest.fail("DUT has no saved Wi-Fi network: set WIFI_SSID and WIFI_PASSWORD in framework/.env")
        wifi = device.ensure_wifi(boot.text, settings.ssid, settings.wifi_password)
        if set(wifi.errors) == {"E105"} and "connected to" in wifi.text:
            # E105 right after 'connected' is the internet check not finished yet: wait for it instead of ignoring it.
            if not wait_internet(device, INTERNET_WAIT_S):
                pytest.fail(f"Wi-Fi is up but there is no internet for {INTERNET_WAIT_S:.0f} s (E105)\n{wifi.text}")
        elif wifi.timed_out or wifi.errors:
            pytest.fail(f"Wi-Fi bring-up failed: {wifi.errors or 'timeout'}\n{wifi.text}")
        reg = device.register(settings.login, settings.password)
        if reg.errors and not reg.has_code("E202"):  # E202: profile already exists, which is fine
            pytest.fail(f"register failed: {reg.errors}\n{reg.text}")
        device.boot_text = boot.text
        device.fw_version = version
        yield device
    finally:
        try:
            device.logout()
        finally:
            device.close()


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def _restore_baseline(device: SwmDevice, settings: Settings) -> None:
    """Get back to baseline: logged out, NORMAL, lamp/relay off, Wi-Fi up. Reboot if stuck (EMERGENCY/hang)."""
    r = device.logout()
    stuck = r.timed_out or any(c in r.codes for c in ("E001", "E005", "E304"))
    if stuck:
        boot = device.reboot()
        device.ensure_wifi(boot.text, settings.ssid, settings.wifi_password)
    elif not device.link_up():  # test may have dropped Wi-Fi or rebooted the board
        device.ensure_wifi("known network", settings.ssid, settings.wifi_password)


@pytest.fixture
def dut_raw(request: pytest.FixtureRequest, device_session: SwmDevice, settings: Settings):
    """DUT at baseline, NOT logged in. For access-control and login tests."""
    version = _version_tuple(device_session.fw_version)
    if request.node.get_closest_marker("since_2_3_0") and version < (2, 3, 0):
        pytest.skip("requires firmware >= 2.3.0")
    if request.node.get_closest_marker("only_2_1_0") and version != (2, 1, 0):
        pytest.skip("applies to firmware 2.1.0 only")
    _restore_baseline(device_session, settings)
    device_session.transcript.clear()
    yield device_session
    _write_transcript(request, device_session)
    _restore_baseline(device_session, settings)  # safe state for the next test: lamp/relay off, logged out


@pytest.fixture
def reboot_dut(device_session: SwmDevice, settings: Settings):
    """Callable: soft-reboot (not RTS - keeps Wi-Fi reliable), bring Wi-Fi back up, return the boot log."""

    def _reboot():
        boot = device_session.reboot()
        device_session.ensure_wifi(boot.text, settings.ssid, settings.wifi_password)
        return boot

    return _reboot


@pytest.fixture
def dut(dut_raw: SwmDevice, settings: Settings):
    """dut_raw, but logged in as the test user."""
    r = dut_raw.login_waiting_out_lockout(settings.login, settings.password)
    if "on watch" not in r.text:
        pytest.fail(f"Cannot log in for the test: {r.codes}\n{r.text}")
    return dut_raw


# --------------------------------------------------------------------------- evidence
def _write_transcript(request: pytest.FixtureRequest, device: SwmDevice) -> None:
    failed = getattr(request.node, "rep_call", None) is not None and request.node.rep_call.failed
    if not (failed or request.config.getoption("--keep-logs")):
        return
    version = device.fw_version
    folder = LOG_DIR / f"v{version}"
    folder.mkdir(parents=True, exist_ok=True)
    raw_name = re.sub(r"[^\w.-]+", "_", request.node.nodeid.split("::", 1)[-1])
    digest = hashlib.sha1(raw_name.encode(), usedforsecurity=False).hexdigest()[:10]
    name = f"{raw_name[:100].rstrip('_')}_{digest}"
    header = f"# {request.node.nodeid}\n# fw v{version}  {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    (folder / f"{name}.log").write_text(header + device.transcript.render(), encoding="utf-8")
