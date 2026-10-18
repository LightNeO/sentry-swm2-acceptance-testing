#!/usr/bin/env bash
# Runs the HIL button stage and the managed Wi-Fi stage 3 times and saves the evidence to logs/hil/.
# Usage (from the repo root, on the Linux stand):
#   export SWM_PORT=/dev/ttyUSB1 BUTTON_STIM_PORT=/dev/ttyUSB0   # adjust to your ports
#   bash run_hil_evidence.sh [runs]                              # default 3 runs
# It does not edit code or docs and does not use --record (docs/results.json stays untouched).
# Prerequisites: DUT on fw 2.3.0 with profile qa_swm registered, dnsmasq and the NetworkManager profiles
# SENTRY-HIL / NeO present, an object 15-200 cm in front of HC-SR04 (for HIL-GD-07).
set -u

RUNS="${1:-3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$ROOT/logs/hil"
export HIL_AP_CONNECTION="${HIL_AP_CONNECTION:-SENTRY-HIL}"
UPSTREAM_CON="${HIL_UPSTREAM_CONNECTION:-NeO}"
UPSTREAM_IF="${HIL_UPSTREAM_INTERFACE:-wlp0s21f0u2}"
AP_IF="${HIL_AP_INTERFACE:-wlp1s0}"

: "${SWM_PORT:?set SWM_PORT (ESP32 UART, e.g. /dev/ttyUSB1)}"
: "${BUTTON_STIM_PORT:?set BUTTON_STIM_PORT (Arduino Nano, e.g. /dev/ttyUSB0)}"

mkdir -p "$OUT"
cd "$ROOT/framework" || exit 1

{
  echo "date: $(date -Is)"
  echo "commit: $(git -C "$ROOT" rev-parse HEAD)"
  echo "python: $(python --version 2>&1)"
  echo "pytest: $(python -m pytest --version 2>&1)"
  echo "SWM_PORT=$SWM_PORT BUTTON_STIM_PORT=$BUTTON_STIM_PORT HIL_AP_CONNECTION=$HIL_AP_CONNECTION"
  echo "--- nmcli device status"
  nmcli device status 2>&1
} > "$OUT/ENVIRONMENT.txt"

restore_network() {
  nmcli connection up "$UPSTREAM_CON" ifname "$UPSTREAM_IF" >/dev/null 2>&1
  nmcli connection up "$HIL_AP_CONNECTION" ifname "$AP_IF" >/dev/null 2>&1
}
trap restore_network EXIT

for i in $(seq 1 "$RUNS"); do
  echo "=== run $i/$RUNS: HIL button stage ==="
  rm -rf "$ROOT/logs/auto"
  python -m pytest tests/hil -m hil_stage --run-hil --keep-logs -v 2>&1 | tee "$OUT/hil_stage_run$i.txt"

  echo "=== run $i/$RUNS: managed Wi-Fi stage ==="
  python -m pytest tests/wifi -m managed_wifi --run-managed-wifi --keep-logs -v 2>&1 | tee "$OUT/managed_wifi_run$i.txt"

  mkdir -p "$OUT/transcripts_run$i"
  cp -r "$ROOT/logs/auto/." "$OUT/transcripts_run$i/" 2>/dev/null
  restore_network
done

# Fail the script (not the evidence) if a secret slipped into the saved files: the AP/Wi-Fi password from .env.
if [ -f .env ]; then
  for key in WIFI_PASSWORD; do
    value="$(grep -E "^$key=" .env | head -n1 | cut -d= -f2-)"
    if [ -n "$value" ] && grep -rqF -- "$value" "$OUT"; then
      echo "WARNING: the value of $key from .env was found in $OUT - redact before committing!" >&2
    fi
  done
fi

echo "Done. Evidence is in $OUT. Next:"
echo "  git add logs/hil run_hil_evidence.sh && git commit -m 'Add HIL and managed Wi-Fi run evidence' && git push"
