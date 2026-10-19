"""Mask network names in saved evidence logs before they are committed.

The Wi-Fi scan in the DUT console lists every access point in range, and the stand's own upstream network name
shows up in nmcli output and boot logs. This keeps only the test AP name (SENTRY-HIL) and replaces the rest.

  python tools/sanitize_logs.py ../logs/hil                  # in place
  python tools/sanitize_logs.py ../logs/hil --mask <upstream profile> --mask <other name>

Safe to run more than once. Passwords are not handled here: the driver already masks them while recording.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

KEEP = {"SENTRY-HIL"}
SCAN_LINE = re.compile(r"^(?P<head>.*sentry:\s+\[\s*\d+\]\s+)(?P<name>.+?)(?P<tail>\s{2,}-?\d+ dBm.*)$")


def sanitize_text(text: str, masks: list[str]) -> str:
    out = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        end = line[len(body):]
        m = SCAN_LINE.match(body)
        if m and m.group("name").strip() not in KEEP:
            body = f"{m.group('head')}<ssid>{m.group('tail')}"
        for name in masks:
            body = body.replace(name, "<upstream>")
        out.append(body + end)
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--mask", action="append", default=[], help="extra network name to replace (repeatable)")
    args = parser.parse_args()

    masks = list(args.mask)
    upstream = os.environ.get("HIL_UPSTREAM_CONNECTION", "")
    if upstream and upstream not in masks:
        masks.append(upstream)

    changed = 0
    for path in sorted(args.folder.rglob("*")):
        if not path.is_file() or path.suffix not in {".txt", ".log"}:
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        cleaned = sanitize_text(original, masks)
        if cleaned != original:
            path.write_text(cleaned, encoding="utf-8", newline="")
            changed += 1
    print(f"sanitized {changed} file(s) in {args.folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
