"""One-shot evidence script for AU-1b/1c (login and password limits in 'register').

A board that already has a profile answers E202 before it validates anything, so every case needs a blank NVS.
The script erases only the NVS partition (0x9000, 0x6000) with esptool, so the firmware stays, and repeats:
  round 1: invalid login/password values (must give E204/E205), then login 'abc' + password of 6 chars
  round 2: login of 16 chars + password of 32 chars
  round 3: restore the usual test profile.
Wi-Fi settings are wiped too, so the script runs 'connect' each time. Transcript: logs/v2.3.0/au1_register_bounds.log
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, ".")
import conftest  # noqa: F401  (loads framework/.env into os.environ)

from drivers.device_driver import SwmDevice
from drivers.redaction import Redactor
from drivers.transport import SerialTransport, find_port

SSID = os.environ["WIFI_SSID"]
WIFI_PASSWORD = os.environ["WIFI_PASSWORD"]
LOGIN = os.environ.get("TEST_LOGIN", "qa_swm")
PASSWORD = os.environ.get("TEST_PASSWORD", "Pass1234")
OUT = Path("../logs/v2.3.0/au1_register_bounds.log")

INVALID_LOGINS = [("ab", "E204"), ("a" * 17, "E204"), ("ab-c", "E204"), ("ab c", "E204"), ("abї", "E204"),
                  ("ab@c", "E204"), ("ab.c", "E204"), ("debug", "E203")]
INVALID_PASSWORDS = [("p" * 5, "E205"), ("p" * 33, "E205")]

results: list[tuple[str, str, bool]] = []


def check(label: str, r, expected: str | None) -> None:
    got = ",".join(r.codes) or ("registered" if "registered" in r.text else "-")
    ok = r.has_code(expected) if expected else ("registered" in r.text and not r.errors)
    results.append((label, got, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: expected {expected or 'success'}, got {got}")


def open_after_erase(port: str) -> SwmDevice:
    subprocess.run([sys.executable, "-m", "esptool", "--chip", "esp32s3", "--port", port,
                    "erase-region", "0x9000", "0x6000"], check=True)
    d = SwmDevice(SerialTransport(port), Redactor([WIFI_PASSWORD]))
    d.wait_for(r"ready\. state", 20)
    for attempt in range(1, 4):  # OBS-01: right after a hard reset the first attempt often gives E101
        wifi = d.connect_wifi(SSID, WIFI_PASSWORD)
        if not (wifi.timed_out or wifi.errors):
            break
        d.transcript.add("TX", f"<connect attempt {attempt}/3 failed: {wifi.errors}>")
    else:
        sys.exit(f"ABORT: Wi-Fi did not come up: {wifi.errors}")
    d._collect(8, 1.5, r"time: synced|W106|E105")
    return d


def main() -> None:
    port = find_port()
    transcripts = []

    print("=== round 1: invalid values on blank NVS, then login abc / password of 6 chars ===")
    d = open_after_erase(port)
    for login, code in INVALID_LOGINS:
        check(f"login {login!r}", d.register(login, "Pass1234"), code)
    for pw, code in INVALID_PASSWORDS:
        check(f"password length {len(pw)}", d.register("valid_user", pw), code)
    check("login 'abc' + password length 6", d.register("abc", "abcdef"), None)
    login = d.login("abc", "abcdef")
    results.append(("login abc/abcdef works", ",".join(login.codes) or "-", "on watch" in login.text))
    transcripts.append(d.transcript.render())
    d.close()

    print("=== round 2: login of 16 chars / password of 32 chars ===")
    d = open_after_erase(port)
    check("login length 16 + password length 32", d.register("l" * 16, "p" * 32), None)
    login = d.login("l" * 16, "p" * 32)
    results.append(("login 16/32 works", ",".join(login.codes) or "-", "on watch" in login.text))
    transcripts.append(d.transcript.render())
    d.close()

    print("=== round 3: restore the usual test profile ===")
    d = open_after_erase(port)
    check(f"restore {LOGIN}", d.register(LOGIN, PASSWORD), None)
    transcripts.append(d.transcript.render())
    d.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n\n".join(transcripts), encoding="utf-8")
    failed = [r for r in results if not r[2]]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS; transcript: {OUT}")
    for label, got, _ in failed:
        print(f"FAIL: {label}: got {got}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
