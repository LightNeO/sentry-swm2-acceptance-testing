"""pytest glue: fixtures, evidence logs, results.json recording.

Fixture chain for hardware tests: device_session (once) -> dut_raw (baseline, per test) -> dut (+logged in).
Unit tests don't touch any of this.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import pytest

from drivers.device_driver import SwmDevice
from drivers.redaction import Redactor
from drivers.transport import SerialTransport, find_port

FRAMEWORK_DIR = Path(__file__).resolve().parent
ROOT = FRAMEWORK_DIR.parent
RESULTS_FILE = ROOT / "docs" / "results.json"
LOG_DIR = ROOT / "logs" / "auto"


def _load_env() -> None:
    """Load framework/.env into os.environ; real env vars still win."""
    path = FRAMEWORK_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_env()


# --------------------------------------------------------------------------- options and hooks
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--keep-logs", action="store_true", help="write a transcript for every test, not only failed ones")
    parser.addoption("--record", action="store_true", help="record PASS/FAIL per TC into docs/results.json (for traceability)")
    parser.addoption("--run-hil", action="store_true", help="run the physical Arduino/DUT HIL stage")
    parser.addoption("--run-managed-wifi", action="store_true", help="run the destructive NetworkManager Wi-Fi stage")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Keep physical HIL tests out of normal and CI-free pytest runs."""
    if config.getoption("--run-hil"):
        return
    skip_hil = pytest.mark.skip(reason="physical HIL stage requires --run-hil")
    for item in items:
        if item.get_closest_marker("hil_stage"):
            item.add_marker(skip_hil)
        if item.get_closest_marker("managed_wifi") and not config.getoption("--run-managed-wifi"):
            item.add_marker(pytest.mark.skip(reason="managed Wi-Fi stage requires --run-managed-wifi"))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Stash each phase's report on item.rep_<phase> (fixtures check this for pass/fail)."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
    if rep.when == "call" and item.config.getoption("--record"):
        fwkey = getattr(item.config, "_swm_fwkey", None)
        if fwkey:
            bucket = item.config.__dict__.setdefault("_swm_results", {})
            for marker in item.iter_markers("tc"):
                for tc in marker.args:
                    status = {"passed": "PASS", "failed": "FAIL"}.get(rep.outcome)
                    if status:
                        old = bucket.get(tc)
                        bucket[tc] = "FAIL" if "FAIL" in (old, status) else status


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Merge recorded statuses into docs/results.json (traceability.md gets regenerated from this later)."""
    config = session.config
    bucket = getattr(config, "_swm_results", None)
    fwkey = getattr(config, "_swm_fwkey", None)
    if not bucket or not fwkey:
        return
    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8")) if RESULTS_FILE.exists() else {}
    for tc, status in bucket.items():
        data.setdefault(tc, {})[fwkey] = status
    RESULTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- configuration
class Settings(dict):
    """Config dict with repr hidden - pytest dumps fixture args on failure and the Wi-Fi password can't leak that way."""

    def __repr__(self) -> str:
        return "<Settings: values hidden>"

    __str__ = __repr__


@pytest.fixture(scope="session")
def settings() -> dict[str, str]:
    return Settings({
        "login": os.environ.get("TEST_LOGIN", "qa_swm"),
        "password": os.environ.get("TEST_PASSWORD", "Pass1234"),
        "ssid": os.environ.get("WIFI_SSID", ""),
        "wifi_password": os.environ.get("WIFI_PASSWORD", ""),
    })


# --------------------------------------------------------------------------- hardware session
@pytest.fixture(scope="session")
def device_session(request: pytest.FixtureRequest, settings: dict[str, str]):
    """Open the DUT once per run, bring it to: Wi-Fi up, profile registered, logged out."""
    port = os.environ.get("SWM_PORT") or find_port()
    redactor = Redactor([settings["wifi_password"]])
    device = SwmDevice(SerialTransport(port), redactor)
    try:
        boot = device.hard_reset()
        version = device.version()
        request.config._swm_fwkey = "".join(version.split(".")[:2])  # "2.1.0" -> "21"
        if "known network" not in boot.text and not (settings["ssid"] and settings["wifi_password"]):
            pytest.fail("DUT has no saved Wi-Fi network: set WIFI_SSID and WIFI_PASSWORD in framework/.env")
        wifi = device.ensure_wifi(boot.text, settings["ssid"], settings["wifi_password"])
        transient_hil_e105 = (
            os.environ.get("HIL_AP_CONNECTION")
            and wifi.has_code("E105")
            and "got ip" in wifi.text
            and "connected to" in wifi.text
        )
        if wifi.timed_out or (wifi.errors and not transient_hil_e105):
            pytest.fail(f"Wi-Fi bring-up failed: {wifi.errors or 'timeout'}\n{wifi.text}")
        reg = device.register(settings["login"], settings["password"])
        if reg.errors and not reg.has_code("E202"):  # E202: profile already exists, which is fine
            pytest.fail(f"register failed: {reg.errors}\n{reg.text}")
        device.boot_text = boot.text  # type: ignore[attr-defined]
        device.fw_version = version  # type: ignore[attr-defined]
        yield device
    finally:
        try:
            device.logout()
        finally:
            device.close()


@pytest.fixture(scope="session")
def fw_version(device_session: SwmDevice) -> str:
    return device_session.fw_version  # type: ignore[attr-defined]


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def _restore_baseline(device: SwmDevice, settings: dict[str, str]) -> None:
    """Get back to baseline: logged out, NORMAL, lamp/relay off, Wi-Fi up. Reboot if stuck (EMERGENCY/hang)."""
    r = device.logout()
    stuck = r.timed_out or any(c in r.codes for c in ("E001", "E005", "E304"))
    if stuck:
        boot = device.reboot()
        device.ensure_wifi(boot.text, settings["ssid"], settings["wifi_password"])
    elif not device.link_up():  # test may have dropped Wi-Fi or rebooted the board
        device.ensure_wifi("known network", settings["ssid"], settings["wifi_password"])


def login_waiting_out_lockout(device: SwmDevice, login: str, password: str, max_wait: float = 40.0):
    """Login, waiting out a lockout (E207/E210, 30 s) if the account is locked - don't let it cascade into the next test."""
    r = device.login(login, password)
    deadline = time.monotonic() + max_wait
    while ("E207" in r.codes or "E210" in r.codes) and time.monotonic() < deadline:
        m = r.search(r"Try again in (\d+) s")
        time.sleep((int(m.group(1)) if m else 5) + 1)
        r = device.login(login, password)
    return r


@pytest.fixture
def dut_raw(request: pytest.FixtureRequest, device_session: SwmDevice, settings: dict[str, str]):
    """DUT at baseline, NOT logged in. For access-control and login tests."""
    version = _version_tuple(device_session.fw_version)  # type: ignore[attr-defined]
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
def reboot_dut(device_session: SwmDevice, settings: dict[str, str]):
    """Callable: soft-reboot (not RTS - keeps Wi-Fi reliable), bring Wi-Fi back up, return the boot log."""

    def _reboot():
        boot = device_session.reboot()
        device_session.ensure_wifi(boot.text, settings["ssid"], settings["wifi_password"])
        return boot

    return _reboot


@pytest.fixture
def dut(dut_raw: SwmDevice, settings: dict[str, str]):
    """dut_raw, but logged in as the test user."""
    r = login_waiting_out_lockout(dut_raw, settings["login"], settings["password"])
    if "on watch" not in r.text:
        pytest.fail(f"Cannot log in for the test: {r.codes}\n{r.text}")
    return dut_raw


# --------------------------------------------------------------------------- evidence
def _write_transcript(request: pytest.FixtureRequest, device: SwmDevice) -> None:
    failed = getattr(request.node, "rep_call", None) is not None and request.node.rep_call.failed
    if not (failed or request.config.getoption("--keep-logs")):
        return
    version = getattr(device, "fw_version", "unknown")
    folder = LOG_DIR / f"v{version}"
    folder.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^\w.-]+", "_", request.node.nodeid.split("::", 1)[-1])
    header = f"# {request.node.nodeid}\n# fw v{version}  {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    (folder / f"{name}.log").write_text(header + device.transcript.render(), encoding="utf-8")
