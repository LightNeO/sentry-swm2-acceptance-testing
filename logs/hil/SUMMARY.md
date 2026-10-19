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
| TC-OTA-25 (а) AP down → `ota check` | FAIL | FAIL | PASS | до `W110` — `E402`, після — `E002` |
| TC-OTA-25 (б) upstream down → `ota check` | FAIL | PASS | PASS | AP blip при вимкненні upstream; run 1: відповідь не дочекались |
| TC-OTA-23 недоступний OTA-сервер → `E402` | ERROR | PASS | PASS | каскад: Wi-Fi ще не відновився |
| TC-OTA-31 кастомний OTA-сервер збережено | PASS | PASS | FAIL | випадковий розрив Wi-Fi під час тесту |

Після аналізу тести TC-WF-12, TC-OTA-25, TC-OTA-23, TC-OTA-31 і HIL-GD-07 виправлено; їх треба перевірити
повторним прогоном: `bash run_hil_recheck.sh` (результати потраплять у `logs/hil/recheck/`).

## Повторний прогін виправлених тестів (`run_hil_recheck.sh`, коміт `e99eaa2`, 3 прогони)

| Тест | Run 1 | Run 2 | Run 3 | Висновок |
|---|---|---|---|---|
| TC-WF-12 forget → reboot → `reconnect` → `E113` | PASS | PASS | PASS | закрито |
| TC-OTA-25 (а) AP down → `E002` після `W110` | PASS | PASS | PASS | закрито |
| TC-OTA-23 недоступний сервер → `E402` | PASS | PASS | PASS | закрито |
| TC-OTA-25 (б) upstream down → `E402` | FAIL | FAIL | PASS | `E002`: AP blip через кілька секунд після вимкнення upstream |
| TC-OTA-31 кастомний OTA-сервер | FAIL | PASS | FAIL | випадкові розриви Wi-Fi; у run 3 сервер не збережено |
| HIL-GD-07 K4 hold → PANIC | SKIP | SKIP | SKIP | об'єкт на 8–9 см (потрібно 15–200 см) |

Причина решти нестабільності знайдена в самому стенді: фікстура `wifi_baseline` перед кожним тестом
викликала `nmcli connection up` для вже активних профілів, а це перезапускає AP і розриває Wi-Fi плати
(`W110 reason 7` через ~1 с після старту тесту). `ManagedAp.ensure_baseline` тепер піднімає лише неактивні профілі,
тести 25(б) і 31 повторюють спробу при розриві. Потрібен ще один прогін `run_hil_recheck.sh`.

## Другий повторний прогін (`run_hil_recheck.sh`, коміт `8dbd7ab`, 3 прогони)

| Тест | Run 1 | Run 2 | Run 3 | Статус |
|---|---|---|---|---|
| TC-WF-12, TC-OTA-23, TC-OTA-25 (а), TC-OTA-31 | PASS | PASS | PASS | закрито |
| TC-OTA-25 (б) upstream down | `E411` | `E402` | `E402` | закрито: код залежить від прапорця internet (OBS-06) |
| HIL-GD-07 K4 hold → PANIC | SKIP | SKIP | SKIP | об'єкт на 8,3–8,5 см (потрібно 15–200 см) |

`ensure_baseline` без перезапуску активних профілів прибрав випадкові розриви Wi-Fi: з 15 запусків тестів (5 тестів x 3) один
тест (25 б) очікував `E402`, а прошивка дала `E411`. Це не збій тесту, а друга гілка поведінки: `E411` виникає, коли
`status` уже показує `internet: NO`. Оракул тесту розширено до `E402` або `E411` (не `E002`).

## Третій повторний прогін (коміт `3d58091`, 1 прогін)

| Тест | Результат |
|---|---|
| TC-WF-12, TC-OTA-23, TC-OTA-25 (а), TC-OTA-25 (б) з оракулом `E402` або `E411`, TC-OTA-31 | PASS (5 із 5) |
| HIL-GD-07 K4 hold → PANIC | SKIP: `distance` дав `E702 sonar: out of range (2-400 cm)`, тобто перед датчиком немає придатного об'єкта |

Увага: у `logs/hil/recheck/` лише `*_run1.txt` і `transcripts_run1/` походять із цього прогону (коміт `3d58091`);
`*_run2.txt` і `*_run3.txt` залишились від попереднього прогону (коміт `8dbd7ab`) і не перезаписувались.

## Четвертий повторний прогін (коміт `43a2b45`, після скидання калібрування сонара)

| Тест | Результат |
|---|---|
| HIL-GD-07 K4 hold → PANIC | **PASS**: `distance` → `echo 21.0 cm`, `ARMED`, K4 hold 2,2 с → `PANIC button (K4)` → `GENERAL ALARM`, `guard status` = `ALARM`, `guard disarm 1234` знімає |

Причина попередніх SKIP/FAIL: збите калібрування сонара (показував 8–9 см або `E702`). Після `distance reset` показання
коректні. Тобто нестабільність HIL-GD-07 у першому прогоні (9,4 см) теж могла бути не лише положенням об'єкта.
Файли `*_run2.txt` і `*_run3.txt` у `recheck/` лишаються від попередніх прогонів.
