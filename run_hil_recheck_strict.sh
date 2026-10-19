#!/usr/bin/env bash
# Re-runs the tests whose weak checks were tightened: TC-WF-11, TC-WF-18 (E101 no longer counts as success,
# reconnect is retried and must really connect) and the session start in conftest.py (E105 is no longer ignored:
# the framework waits until the DUT reports "internet: OK"). Plus TC-WF-12 and TC-OTA-25 as a quick sanity pair.
# Usage (from the repo root, on the Linux stand):
#   export SWM_PORT=/dev/ttyUSB1 BUTTON_STIM_PORT=/dev/ttyUSB0   # adjust to your ports
#   bash run_hil_recheck_strict.sh [runs]                        # default 3 runs
# Results go to logs/hil/recheck_strict/. DUT: fw 2.3.0, connected to SENTRY-HIL (see run_hil_evidence.sh).
set -u

RUNS="${1:-3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$ROOT/logs/hil/recheck_strict"
export HIL_AP_CONNECTION="${HIL_AP_CONNECTION:-SENTRY-HIL}"
UPSTREAM_CON="${HIL_UPSTREAM_CONNECTION:?set HIL_UPSTREAM_CONNECTION (name of the upstream NetworkManager profile)}"
UPSTREAM_IF="${HIL_UPSTREAM_INTERFACE:-wlp0s21f0u2}"
AP_IF="${HIL_AP_INTERFACE:-wlp1s0}"

: "${SWM_PORT:?set SWM_PORT (ESP32 UART, e.g. /dev/ttyUSB1)}"
: "${BUTTON_STIM_PORT:?set BUTTON_STIM_PORT (Arduino Nano, e.g. /dev/ttyUSB0)}"

TESTS="reconnect_after_disconnect_restores_link or ap_loss_emits_wifi_loss_and_recovers or forget_removes_saved_network_from_next_boot or ap_loss_makes_ota_check_require_wifi"

mkdir -p "$OUT"
cd "$ROOT/framework" || exit 1

{
  echo "date: $(date -Is)"
  echo "commit: $(git -C "$ROOT" rev-parse HEAD)"
  echo "python: $(python --version 2>&1)"
  echo "--- nmcli device status"
  nmcli device status 2>&1
} > "$OUT/ENVIRONMENT.txt"

restore_network() {
  nmcli connection up "$UPSTREAM_CON" ifname "$UPSTREAM_IF" >/dev/null 2>&1
  nmcli connection up "$HIL_AP_CONNECTION" ifname "$AP_IF" >/dev/null 2>&1
}
trap restore_network EXIT

for i in $(seq 1 "$RUNS"); do
  echo "=== strict recheck $i/$RUNS ==="
  rm -rf "$ROOT/logs/auto"
  python -m pytest tests/wifi -m managed_wifi --run-managed-wifi --keep-logs -v -k "$TESTS" 2>&1 | tee "$OUT/strict_run$i.txt"
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
echo "  git add logs/hil run_hil_recheck_strict.sh && git commit -m 'Add strict recheck evidence' && git push"
