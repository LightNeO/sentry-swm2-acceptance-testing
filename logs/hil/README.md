# HIL-стенд: фінальний прогін

Результати остаточної збірки стенда на прошивці **2.3.0** (дата прогону: 2026-10-19). Це один чистий прогін усіх стендових тестів.
Опис архітектури: [`docs/hil_stand.md`](../../docs/hil_stand.md); кнопки: [`docs/hil_button_stage.md`](../../docs/hil_button_stage.md); керований Wi-Fi: [`docs/managed_ap.md`](../../docs/managed_ap.md).

## Стенд

| Вузол | Реалізація |
|---|---|
| Контролер | ноутбук, Linux, Python 3.14, pytest 9.1, pyserial |
| DUT | ESP32-S3 DevKit, прошивка 2.3.0 (UART через FTDI FT232R, 115200 8N1) |
| Стимулятор кнопок | Arduino Nano (ATmega328P, CH340), A2–A5 через 1 кОм на GPIO41/40/39/38, open-drain |
| Мережа | два Wi-Fi адаптери: вбудований роздає AP `SENTRY-HIL`, USB-донгл дає upstream; NetworkManager + dnsmasq |
| OTA-сервер | `fw_7/tools/ota_server.py`, для повільного OTA запускається тестом (`--slow 20`) |
| Сонар | об'єкт перед HC-SR04 на 20–50 см (для Guard) |

## Як запустити

```text
export SWM_PORT=/dev/ttyUSB1 BUTTON_STIM_PORT=/dev/ttyUSB0 HIL_AP_CONNECTION=SENTRY-HIL HIL_UPSTREAM_CONNECTION=<профіль upstream>
cd framework
python -m pytest tests/hil -m hil_stage --run-hil -v -rs
python -m pytest tests/wifi -m managed_wifi --run-managed-wifi --keep-logs -v -rs
```

Умови: плата на 2.3.0 у `SENTRY-HIL`, профіль `qa_swm` зареєстрований, монітори портів закриті; для повільного OTA потрібні образи
(`python fw_7/tools/ota_server.py --download`, одноразово). Подробиці змінних: [`docs/managed_ap.md`](../../docs/managed_ap.md).

## Результати

### Arduino-кнопки (`hil_buttons.txt`): 14 passed, 1 skipped, 2 хв 27 с

| Тест | Що перевіряє | Результат |
|---|---|---|
| K1 press | `[BEACON] on/off (K1)` | PASS |
| K2 press / hold 1,7 с | `[VALVE] OPEN/CLOSED (K2)`, імпульс 1 с з автозавершенням | PASS ×2 |
| K3 press ×2 | старт і зупинка активного пінгування | PASS |
| K4 press після `alert test info` | підтвердження алерту `acknowledged (K4)` | PASS |
| K4 hold 2,2 с під охороною | PANIC → GENERAL ALARM (HIL-GD-07) | PASS |
| K3+K4 2,2 с | `1 NORMAL -> 3 VERBOSE (by buttons)` | PASS |
| K1–K4 без login | `E003` | PASS ×4 |
| K4+K1 2,2 с з NORMAL і DEBUG | `E302`, стан не змінюється | PASS ×2 |
| K4+K1 2,2 с з VERBOSE | `EMERGENCY SURFACING` | PASS |
| K1–K3 в EMERGENCY | `E005 buttons blocked in EMERGENCY` | SKIP: тест лише для прошивки 2.1.0 |

### Керований Wi-Fi і OTA (`managed_wifi.txt`): 21 passed, 11 хв 12 с

| Тест (TC) | Що перевіряє | Результат |
|---|---|---|
| TC-WF-01, 02 | `connect` за номером і за назвою через `SENTRY-HIL` | PASS ×2 |
| TC-WF-03, 04, 06, 07 | пароль <8 символів `E112`, порожній SSID `E111`, неправильний пароль `E101`, невідомий SSID `E102` | PASS ×4 |
| TC-WF-05, 10, 12 | мережа зберігається після reboot; `reconnect` без мережі `E113`; `forget` стирає мережу | PASS ×3 |
| TC-WF-11, 13 | `reconnect` після `disconnect` повертає зв'язок; другий `disconnect` `W115` | PASS ×2 |
| TC-WF-14, 16, 17 | `scan` бачить AP, `ping` до upstream, `time` | PASS ×3 |
| TC-WF-18 | вимкнення AP: `W110`, `retry 1/3`; після повернення AP `reconnect` дає `connected to` | PASS |
| TC-OTA-25 (а) | AP вимкнена: після `W110` `ota check` дає `E002` | PASS |
| TC-OTA-25 (б) | upstream вимкнений, AP жива: `ota check` дає `E402` (або `E411`, якщо `internet: NO`) | PASS |
| TC-OTA-23, 26, 31 | недоступний сервер `E402`, хибний шлях `E405`, збереження кастомного сервера | PASS ×3 |
| TC-OTA-16 | обрив AP на 10% повільного завантаження | PASS |

### Спостереження з транскриптів (`transcripts/`)

- **Повільний OTA** (`..._slow_ota_download_is_survived`): `[OTA] 10%` → вимкнення AP → `W110 wifi connection lost (reason 200)` → `[LINK] retry 1/3` → `E410 download interrupted`.
  Версія `v2.3.0` і слот `ota_1 @ 0x1a0000, state: valid` після відновлення такі самі; `ota check` працює, `internet: OK`.
- **AP loss** (`..._ap_loss_emits_wifi_loss_and_recovers`): `W110` → `reconnect` → `connected to 'SENTRY-HIL', rssi -26 dBm`.
- **`ota check` без AP** (`..._ap_loss_makes_ota_check_require_wifi`): після `W110` відповідь `E002 Wi-Fi required`, далі `retry 2/3`, `retry 3/3`, після повернення AP зв'язок відновлюється.
- **Upstream down** (`..._upstream_loss_keeps_test_ap_up`): AP жива, `ota check` через ~10 с дає `E402 cannot reach OTA server (stable.txt)`.

## Файли

| Файл | Зміст |
|---|---|
| `hil_buttons.txt` | повний вивід pytest для HIL-кнопок |
| `managed_wifi.txt` | повний вивід pytest для керованого Wi-Fi і повільного OTA |
| `transcripts/` | UART-транскрипти чотирьох ключових мережевих тестів |
