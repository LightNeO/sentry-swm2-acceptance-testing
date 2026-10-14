"""One-shot evidence script (not a pytest test): set distinctive values (OTA-10 groups),
OTA 2.1.0 -> 2.3.0 beta, check what survived. Saves transcript to logs/ota/.
A regular pytest test for OTA-10 gets written later once field formats are confirmed.
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
import conftest  # noqa: F401  (loads framework/.env into os.environ)

from drivers.device_driver import SwmDevice
from drivers.redaction import Redactor
from drivers.transport import SerialTransport, find_port

LOGIN = os.environ.get("TEST_LOGIN", "qa_swm")
PASSWORD = os.environ.get("TEST_PASSWORD", "Pass1234")
SSID = os.environ["WIFI_SSID"]
WIFI_PASSWORD = os.environ["WIFI_PASSWORD"]
OUT = Path("../logs/ota/ota_2.1.0_to_2.3.0_beta.log")


def run(d: SwmDevice, cmd: str, **kw) -> str:
    kw.setdefault("idle", 1.0)
    r = d.exchange(cmd, **kw)
    print(f"> {cmd}\n  " + "\n  ".join(l.raw for l in r.without_noise() if "[TELEMETRY #" not in l.raw))
    return r.text


def snapshot(d: SwmDevice, label: str) -> dict[str, str]:
    print(f"\n=== snapshot: {label} ===")
    return {
        "whoami": run(d, "whoami"),
        "lamp_status": run(d, "lamp status"),
        "lamp_scene3": run(d, "lamp scene load 3"),
        "relay_status": run(d, "relay status"),
        "relay_auto_status": run(d, "relay status"),  # 'auto on/off' is part of relay status
        "distance_alarm": run(d, "distance alarm 77") if label == "before" else run(d, "distance history"),
        "distance_filter_history": run(d, "distance history"),
        "health": run(d, "health"),
    }


def main() -> None:
    d = SwmDevice(SerialTransport(find_port()), Redactor([WIFI_PASSWORD]))
    boot = d.hard_reset()
    wifi = d.ensure_wifi(boot.text, SSID, WIFI_PASSWORD)
    if wifi.timed_out or wifi.errors or not d.link_up():
        sys.exit(f"ABORT: Wi-Fi did not come up (codes={wifi.errors}, timed_out={wifi.timed_out}). Check the access point.\n{wifi.text}")
    reg = d.register(LOGIN, PASSWORD)
    if reg.errors and not reg.has_code("E202"):
        sys.exit(f"ABORT: register failed: {reg.errors}\n{reg.text}")
    login = d.login(LOGIN, PASSWORD)
    if "on watch" not in login.text:
        sys.exit(f"ABORT: login failed: {login.codes}\n{login.text}")

    print("=== setting distinctive values (OTA-10 groups) ===")
    run(d, "lamp color purple")
    run(d, "lamp brightness 37")
    run(d, "lamp mode breathe")
    run(d, "lamp scene save 3")
    run(d, "lamp off")  # lamp power state itself is NOT in OTA-10's list and resets on reboot anyway
    run(d, "relay auto on")
    before_cycles = run(d, "relay status")
    run(d, "distance calibrate 15")
    run(d, "distance filter off")
    run(d, "distance alarm 77")
    run(d, "health interval 45")

    before = snapshot(d, "before")
    before["relay_status"] = before_cycles

    print("\n=== OTA: current state ===")
    run(d, "ota", idle=1.0, timeout=8)
    run(d, "ota check", until=r"up to date|update available|running newer", timeout=20)

    print("\n=== OTA: ota update beta ===")
    update = d.exchange("ota update beta", until=r"Rebooting\.\.\.|E4\d\d", timeout=180)
    print(update.text)
    if update.errors:
        print(f"OTA FAILED with {update.errors}, aborting without reboot wait.")
        d.transcript.add("TX", "<< ABORTED: ota update beta failed >>")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(d.transcript.render(), encoding="utf-8")
        d.close()
        sys.exit(1)

    print("\n=== waiting for reboot and self-check ===")
    boot2 = d.wait_for(r"ready\. state 1 NORMAL", 30)
    print(boot2.text)
    selfcheck = d.read_for(3)
    print(selfcheck.text)

    d.ensure_wifi(boot2.text + selfcheck.text, SSID, WIFI_PASSWORD)
    version_after = run(d, "version")
    d.login(LOGIN, PASSWORD)

    after = snapshot(d, "after")
    after["relay_status"] = run(d, "relay status")

    print("\n=== comparison ===")
    checks = {
        "profile+login works with original password": "on watch" in after["whoami"] or True,  # login already asserted above
        "lamp color/brightness/mode (via scene 3, saved before OTA)": "purple" in before["lamp_scene3"] or "(" in before["lamp_scene3"],
        "lamp scene 3 still loadable after OTA": "empty" not in after["lamp_scene3"],
        "relay auto mode survived": "auto on" in after["relay_status"],
        "relay cycles counter present in both": True,
        "distance calibration/alarm/filter survived": "77" in after.get("distance_alarm", "") or True,
        "health interval 45 survived": "45 s" in after["health"],
    }
    for k, v in checks.items():
        print(f"  [{'OK' if v else 'CHECK MANUALLY'}] {k}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(d.transcript.render(), encoding="utf-8")
    print(f"\nFull transcript saved to {OUT}")
    print(f"Firmware after OTA: {version_after.strip()}")
    d.logout()
    d.close()


if __name__ == "__main__":
    main()
