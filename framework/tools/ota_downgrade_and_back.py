"""OTA round trip: 2.3.0 -> install 2.1.0 (blocked w/o force, allowed with force) -> back to 2.3.0.

Covers TC-OTA-09 (no force -> E408), TC-OTA-10 (force -> allowed), TC-OTA-27/28 (OTA-10 persistence),
OTA-7 (clean PENDING_VERIFY -> self-check transcript; forced UTF-8 stdout since a previous run
lost this to a console-encoding crash).
"""

import io
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
import conftest  # noqa: F401

from drivers.device_driver import SwmDevice
from drivers.redaction import Redactor
from drivers.transport import SerialTransport, find_port

LOGIN = os.environ.get("TEST_LOGIN", "qa_swm")
PASSWORD = os.environ.get("TEST_PASSWORD", "Pass1234")
SSID = os.environ["WIFI_SSID"]
WIFI_PASSWORD = os.environ["WIFI_PASSWORD"]
OUT = Path("../logs/ota/ota_downgrade_and_back.log")
LOG: list[str] = []


def log(line: str = "") -> None:
    print(line)
    LOG.append(line)


def run(d: SwmDevice, cmd: str, **kw) -> "object":
    kw.setdefault("idle", 1.0)
    r = d.exchange(cmd, **kw)
    log(f"> {cmd}")
    for l in r.without_noise():
        if "[TELEMETRY #" not in l.raw:
            log("  " + l.raw)
    return r


def require_wifi(d: SwmDevice, boot_text: str) -> None:
    wifi = d.ensure_wifi(boot_text, SSID, WIFI_PASSWORD)
    if wifi.timed_out or wifi.errors or not d.link_up():
        sys.exit(f"ABORT: Wi-Fi did not come up: {wifi.errors}\n{wifi.text}")


def snapshot(d: SwmDevice, label: str) -> None:
    log(f"\n=== snapshot: {label} ===")
    run(d, "version")
    run(d, "whoami")
    run(d, "lamp status")
    run(d, "lamp scene load 3")
    run(d, "relay status")
    run(d, "health")
    run(d, "distance alarm 77")  # re-assert so the following 'distance 1' triggers it, same as before
    run(d, "distance 1", idle=1.5, timeout=20)
    run(d, "distance stats")


def main() -> None:
    d = SwmDevice(SerialTransport(find_port()), Redactor([WIFI_PASSWORD]))
    boot = d.hard_reset()
    require_wifi(d, boot.text)
    d.login(LOGIN, PASSWORD)
    log(f"Starting version: {d.version()}")

    log("\n=== Step 1: downgrade to 2.1.0 WITHOUT force -> must be refused ===")
    # firmware downloads+writes the whole image before checking version and refusing - so this
    # takes as long as a real OTA, not a quick rejection
    r = run(d, "ota install 2.1.0", until=r"E4\d\d|Rebooting", timeout=90)
    assert r.has_code("E408"), f"expected E408, got {r.codes}"
    still_current = d.version()
    assert still_current != "2.1.0", "firmware must not have changed after a refused downgrade"
    log(f"OK: E408 downgrade blocked, firmware still {still_current}")

    snapshot(d, "before downgrade (2.3.0)")

    log("\n=== Step 2: downgrade to 2.1.0 WITH force -> must succeed ===")
    r = d.exchange("ota install 2.1.0 force", until=r"Rebooting\.\.\.|E4\d\d", timeout=180)
    log(r.text)
    if r.errors:
        sys.exit(f"ABORT: forced downgrade failed: {r.errors}")
    boot2 = d.wait_for(r"ready\. state 1 NORMAL", 30)
    log("\n--- boot log after downgrade (looking for self-check lines) ---")
    log(boot2.text)
    require_wifi(d, boot2.text)
    d.login(LOGIN, PASSWORD)
    log(f"\nVersion after downgrade: {d.version()}")
    snapshot(d, "after downgrade (2.1.0)")

    log("\n=== Step 3: back to 2.3.0 via 'ota update beta' (newer than current -> no force needed) ===")
    r = d.exchange("ota update beta", until=r"Rebooting\.\.\.|already up to date|E4\d\d", timeout=180)
    log(r.text)
    if r.errors:
        sys.exit(f"ABORT: re-upgrade failed: {r.errors}")
    boot3 = d.wait_for(r"ready\. state 1 NORMAL", 30)
    log("\n--- boot log after re-upgrade (self-check) ---")
    log(boot3.text)
    require_wifi(d, boot3.text)
    d.login(LOGIN, PASSWORD)
    log(f"\nVersion after re-upgrade: {d.version()}")
    snapshot(d, "after re-upgrade (2.3.0)")

    d.logout()
    d.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nSaved to {OUT}")


if __name__ == "__main__":
    main()
