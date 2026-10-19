#!/usr/bin/env bash
# Final clean run of the HIL stand: Arduino button stage + managed Wi-Fi stage (including the slow OTA test).
# Replaces logs/hil/ with the output of this run. Run from the repo root on the Linux stand:
#
#   export SWM_PORT=/dev/ttyUSB1 BUTTON_STIM_PORT=/dev/ttyUSB0 HIL_UPSTREAM_CONNECTION=<upstream NetworkManager profile>
#   bash run_final_hil.sh
#
# Before the run: DUT on fw 2.3.0 connected to SENTRY-HIL, `distance reset` done, an object 20-50 cm in front of
# HC-SR04 (for HIL-GD-07), no serial monitors open, fw_7/tools/server_files/fw7 present
# (python fw_7/tools/ota_server.py --download). Takes about 20-25 minutes.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HIL_AP_CONNECTION="${HIL_AP_CONNECTION:-SENTRY-HIL}"
UPSTREAM_CON="${HIL_UPSTREAM_CONNECTION:?set HIL_UPSTREAM_CONNECTION (name of the upstream NetworkManager profile)}"
UPSTREAM_IF="${HIL_UPSTREAM_INTERFACE:-wlp0s21f0u2}"
AP_IF="${HIL_AP_INTERFACE:-wlp1s0}"
: "${SWM_PORT:?set SWM_PORT (ESP32 UART, e.g. /dev/ttyUSB1)}"
: "${BUTTON_STIM_PORT:?set BUTTON_STIM_PORT (Arduino Nano, e.g. /dev/ttyUSB0)}"

if [ ! -d "$ROOT/fw_7/tools/server_files/fw7" ]; then
  echo "No OTA server images: run  python fw_7/tools/ota_server.py --download  first" >&2
  exit 1
fi

OUT="$ROOT/logs/hil"
restore_network() {
  nmcli connection up "$UPSTREAM_CON" ifname "$UPSTREAM_IF" >/dev/null 2>&1
  nmcli connection up "$HIL_AP_CONNECTION" ifname "$AP_IF" >/dev/null 2>&1
  # wait until the upstream reaches the internet again
  for _ in $(seq 1 30); do ping -c1 -W1 -I "$UPSTREAM_IF" 1.1.1.1 >/dev/null 2>&1 && break; sleep 2; done
}
trap restore_network EXIT

cd "$ROOT/framework" || exit 1
rm -rf "$ROOT/logs/auto" "$OUT"
mkdir -p "$OUT/transcripts"

echo "=== 1/2: Arduino button stage ==="
python -m pytest tests/hil -m hil_stage --run-hil -v -rs 2>&1 | sed "s#/home/[^/]*#~#g" | tee "$OUT/hil_buttons.txt"

restore_network

echo "=== 2/2: managed Wi-Fi stage and slow OTA ==="
python -m pytest tests/wifi -m managed_wifi --run-managed-wifi --keep-logs -v -rs 2>&1 | sed "s#/home/[^/]*#~#g" | tee "$OUT/managed_wifi.txt"

# only the transcripts without Wi-Fi scan lists (no neighbouring network names)
cp "$ROOT"/logs/auto/v*/test_ap_loss_during_slow_ota*.log \
   "$ROOT"/logs/auto/v*/test_ap_loss_emits*.log \
   "$ROOT"/logs/auto/v*/test_ap_loss_makes_ota_check*.log \
   "$ROOT"/logs/auto/v*/test_upstream_loss*.log \
   "$OUT/transcripts/" 2>/dev/null

echo
echo "=== results ==="
tail -n 3 "$OUT/hil_buttons.txt" "$OUT/managed_wifi.txt"
echo
echo "Next:  git add -A logs/hil && git commit -m 'Final HIL stand run' && git push"
echo "Then tell me; run_final_hil.sh is a one-off and gets removed afterwards."
