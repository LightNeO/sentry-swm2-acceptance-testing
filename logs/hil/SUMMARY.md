# Підсумок прогонів HIL і керованого Wi-Fi (Linux-стенд, прошивка 2.3.0)

Три прогони (`run_hil_evidence.sh`), коміт `3a92552`. Сирі виводи: `hil_stage_run*.txt`, `managed_wifi_run*.txt`,
транскрипти: `transcripts_run*/`. Імена чужих мереж у файлах замасковано (`framework/tools/sanitize_logs.py`).

## Arduino HIL (кнопки K1–K4)

| Тест | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| K1, K2 (press, hold 1.7 с), K3 (start/stop), K4 (ack) | PASS | PASS | PASS |
| K3+K4 → VERBOSE; K4+K1 з NORMAL/DEBUG → `E302`; K4+K1 з VERBOSE → EMERGENCY | PASS | PASS | PASS |
| кнопки без login → `E003` (K1–K4) | PASS | PASS | PASS |
| HIL-GD-07: K4 hold → PANIC/ALARM | PASS | PASS | FAIL |
| кнопки в EMERGENCY → `E005` (лише 2.1.0) | SKIP | SKIP | SKIP |

HIL-GD-07 у run 3: об'єкт перед датчиком опинився на 9,4 см (у run 1–2 було 37–41 см), тобто всередині зони 10 см,
і Guard пішов в `INTRUSION`. Це нестабільна фізична передумова; у тест додано перевірку відстані ≥ 15 см (інакше `skip` з причиною).

## Керований Wi-Fi

| Тест (TC) | Run 1 | Run 2 | Run 3 | Діагноз |
|---|---|---|---|---|
| TC-WF-01…07, 10, 11, 13, 14, 16, 17, 18, TC-OTA-26 | PASS | PASS | PASS | — |
| TC-WF-12 forget → reboot → `reconnect` | FAIL | FAIL | FAIL | помилка тесту: `reboot_dut` сам повертав Wi-Fi |
| TC-OTA-25 (а) AP down → `ota check` | FAIL | FAIL | PASS | до `W110` — `E402`, після — `E002`; `E411` ніколи |
| TC-OTA-25 (б) upstream down → `ota check` | FAIL | PASS | PASS | AP blip при вимкненні upstream; run 1: відповідь не дочекались |
| TC-OTA-23 недоступний OTA-сервер → `E402` | ERROR | PASS | PASS | каскад: Wi-Fi ще не відновився |
| TC-OTA-31 кастомний OTA-сервер збережено | PASS | PASS | FAIL | випадковий розрив Wi-Fi під час тесту |

Після аналізу тести TC-WF-12, TC-OTA-25, TC-OTA-23, TC-OTA-31 і HIL-GD-07 виправлено; їх треба перевірити
повторним прогоном: `bash run_hil_recheck.sh` (результати потраплять у `logs/hil/recheck/`).
