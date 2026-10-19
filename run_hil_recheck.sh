#!/usr/bin/env bash
# Re-runs only the HIL / managed Wi-Fi tests that were fixed after the first evidence run (logs/hil/).
# Usage (from the repo root, on the Linux stand):
#   export SWM_PORT=/dev/ttyUSB1 BUTTON_STIM_PORT=/dev/ttyUSB0   # adjust to your ports
#   bash run_hil_recheck.sh [runs]                               # default 3 runs
# Results go to logs/hil/recheck/. Prerequisites are the same as for run_hil_evidence.sh; for HIL-GD-07 leave an
# object 15-200 cm in front of HC-SR04 (otherwise that test is skipped with the reason written in the output).
set -u

RUNS="${1:-3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$ROOT/logs/hil/recheck"
export HIL_AP_CONNECTION="${HIL_AP_CONNECTION:-SENTRY-HIL}"
UPSTREAM_CON="${HIL_UPSTREAM_CONNECTION:?set HIL_UPSTREAM_CONNECTION (name of the upstream NetworkManager profile)}"
UPSTREAM_IF="${HIL_UPSTREAM_INTERFACE:-wlp0s21f0u2}"
AP_IF="${HIL_AP_INTERFACE:-wlp1s0}"

: "${SWM_PORT:?set SWM_PORT (ESP32 UART, e.g. /dev/ttyUSB1)}"
: "${BUTTON_STIM_PORT:?set BUTTON_STIM_PORT (Arduino Nano, e.g. /dev/ttyUSB0)}"

# Tests changed after the first run:
#   TC-WF-12   test_forget_removes_saved_network_from_next_boot
#   TC-OTA-25  test_ap_loss_makes_ota_check_require_wifi, test_upstream_loss_keeps_test_ap_up
#   TC-OTA-23  test_unreachable_ota_server_returns_e402
#   TC-OTA-31  test_custom_ota_server_is_saved_by_device
#   HIL-GD-07  test_k4_long_press_triggers_guard_panic
WIFI_TESTS="forget_removes_saved_network or ap_loss_makes_ota_check or upstream_loss_keeps_test_ap_up or unreachable_ota_server_returns_e402 or custom_ota_server_is_saved_by_device"
HIL_TESTS="k4_long_press_triggers_guard_panic"

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
  # Wait until the upstream really reaches the internet again, so the next run does not start without it.
  for _ in $(seq 1 30); do ping -c1 -W1 -I "$UPSTREAM_IF" 1.1.1.1 >/dev/null 2>&1 && break; sleep 2; done
}
trap restore_network EXIT

for i in $(seq 1 "$RUNS"); do
  echo "=== recheck $i/$RUNS: managed Wi-Fi tests ==="
  rm -rf "$ROOT/logs/auto"
  python -m pytest tests/wifi -m managed_wifi --run-managed-wifi --keep-logs -v -k "$WIFI_TESTS" 2>&1 | tee "$OUT/managed_wifi_recheck_run$i.txt"

  echo "=== recheck $i/$RUNS: HIL button test ==="
  python -m pytest tests/hil -m hil_stage --run-hil --keep-logs -v -rs -k "$HIL_TESTS" 2>&1 | tee "$OUT/hil_recheck_run$i.txt"

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
echo "  git add logs/hil run_hil_recheck.sh && git commit -m 'Add recheck evidence for the fixed HIL tests' && git push"
