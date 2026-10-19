#!/usr/bin/env bash
# TC-OTA-16: the test AP disappears in the middle of a slow OTA download. The test starts the local OTA server
# (fw_7/tools/ota_server.py --slow 20) by itself on the stand laptop and drops/restores SENTRY-HIL during the download.
# Usage (from the repo root, on the Linux stand):
#   export SWM_PORT=/dev/ttyUSB1 BUTTON_STIM_PORT=/dev/ttyUSB0 HIL_UPSTREAM_CONNECTION=<upstream profile>
#   bash run_hil_slow_ota.sh [runs]                              # default 3 runs
# Prerequisites: DUT on fw 2.3.0 connected to SENTRY-HIL; the firewall lets the DUT reach HIL_OTA_PORT (default 53317)
# on the AP address (HIL_AP_ADDRESS, default 10.42.0.1); server images exist (downloaded automatically below if not).
# Results: logs/hil/slow_ota/
set -u

RUNS="${1:-3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$ROOT/logs/hil/slow_ota"
export HIL_AP_CONNECTION="${HIL_AP_CONNECTION:-SENTRY-HIL}"
UPSTREAM_CON="${HIL_UPSTREAM_CONNECTION:?set HIL_UPSTREAM_CONNECTION (name of the upstream NetworkManager profile)}"
UPSTREAM_IF="${HIL_UPSTREAM_INTERFACE:-wlp0s21f0u2}"
AP_IF="${HIL_AP_INTERFACE:-wlp1s0}"

: "${SWM_PORT:?set SWM_PORT (ESP32 UART, e.g. /dev/ttyUSB1)}"
: "${BUTTON_STIM_PORT:?set BUTTON_STIM_PORT (Arduino Nano, e.g. /dev/ttyUSB0)}"

# The server images are not in git; fetch them once (needs internet on the laptop).
if [ ! -d "$ROOT/fw_7/tools/server_files/fw7" ]; then
  echo "No server images yet - downloading with ota_server.py --download"
  python "$ROOT/fw_7/tools/ota_server.py" --download || exit 1
fi

mkdir -p "$OUT"
cd "$ROOT/framework" || exit 1

{
  echo "date: $(date -Is)"
  echo "commit: $(git -C "$ROOT" rev-parse HEAD)"
  echo "python: $(python --version 2>&1)"
  echo "ota port: ${HIL_OTA_PORT:-53317}  ap address: ${HIL_AP_ADDRESS:-10.42.0.1}"
  echo "--- nmcli device status"
  nmcli device status 2>&1
} > "$OUT/ENVIRONMENT.txt"

restore_network() {
  nmcli connection up "$UPSTREAM_CON" ifname "$UPSTREAM_IF" >/dev/null 2>&1
  nmcli connection up "$HIL_AP_CONNECTION" ifname "$AP_IF" >/dev/null 2>&1
}
trap restore_network EXIT

for i in $(seq 1 "$RUNS"); do
  echo "=== slow OTA run $i/$RUNS ==="
  rm -rf "$ROOT/logs/auto"
  python -m pytest tests/wifi/test_slow_ota.py -m managed_wifi --run-managed-wifi --keep-logs -v -rs 2>&1 | tee "$OUT/slow_ota_run$i.txt"
  mkdir -p "$OUT/transcripts_run$i"
  cp -r "$ROOT/logs/auto/." "$OUT/transcripts_run$i/" 2>/dev/null
  restore_network
done

python tools/sanitize_logs.py "$OUT"

if [ -f .env ]; then
  value="$(grep -E "^WIFI_PASSWORD=" .env | head -n1 | cut -d= -f2-)"
  if [ -n "$value" ] && grep -rqF -- "$value" "$OUT"; then
    echo "WARNING: WIFI_PASSWORD from .env was found in $OUT - redact before committing!" >&2
  fi
fi

echo "Done. Evidence is in $OUT. Next:"
echo "  git add logs/hil run_hil_slow_ota.sh && git commit -m 'Add slow OTA evidence' && git push"
