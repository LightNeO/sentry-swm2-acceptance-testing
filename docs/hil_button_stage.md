# HIL Stage: автоматизація K1-K4

## Мета

Це окрема стадія acceptance testing для SENTRY SWM-2. Вона додає фізичний стимул кнопок через Arduino Nano до вже існуючих UART-тестів. Arduino не підміняє `SwmDevice` і не оголошує фізичний результат перевіреним сам по собі: він лише детерміновано натискає K1-K4, а Python/pytest збирає відповідь DUT через UART.

Стадія створена на основі ручних прогонів:

- `logs/v2.1.0/manual/group1_buttons.log`;
- `logs/v2.3.0/manual/partA_guard_alert.log`;
- `logs/v2.3.0/manual/partB_alert.log`;
- `logs/v2.3.0/manual/partC_buttons.log`;
- `logs/v2.3.0/manual/partD_regression.log`.

Вони містять важливі фактичні результати: K1/K2/K3, чотири комбінації по 2 секунди, K4 acknowledge, K4 PANIC, блокування кнопок у EMERGENCY, 30-секундний sonar run і точні тексти подій.

## Архітектура

```text
pytest HIL stage
    | USB serial: BUTTON_STIM_PORT, 115200
    v
Arduino Nano ATmega328P
    | A2/A3/A4/A5, 1 kOhm, open-drain LOW/high-Z
    v
ESP32 GPIO41/40/39/38 (K1/K2/K3/K4)
    ^
    | USB UART: SWM_PORT, 115200 8N1
    |
SwmDevice + transcript + pytest asserts
```

Поточна робоча плата має `ATmega328P` signature `1E 95 0F`, CH340 і порт `/dev/ttyUSB0`. ESP32 підключається через FTDI, у поточному стенді зазвичай `/dev/ttyUSB1`. Не покладатися на номер порту в CI: використовувати `/dev/serial/by-id` або змінні середовища.

## Електричний контракт

| Arduino | DUT | Функція |
|---|---|---|
| A2 | GPIO41 | K1 / beacon |
| A3 | GPIO40 | K2 / valve |
| A4 | GPIO39 | K3 / sonar |
| A5 | GPIO38 | K4 / Guard/Alert |
| GND | GND | спільна земля |

Між кожною парою сигналів встановлено резистор 1 кОм. Прошивка Nano не подає `HIGH` на лінії ESP32:

- press/hold: `OUTPUT` + `LOW`;
- release: `INPUT` / high impedance.

Це обмежує ризик 5-вольтового HIGH на ESP32. Для фінального стенду рекомендовані оптопари або NPN/open-collector канали. Перед зміною проводки перевіряти continuity без живлення.

## Протокол стимулятора

Arduino працює на `115200 8N1` і приймає newline-команди:

```text
PING
STATUS
PRESS K1 150
HOLD K4 1500
HOLD K3+K4 2000
STOP
```

Тривалість обмежена 1–10000 мс. Після дії Arduino відпускає всі канали і повертає, наприклад, `OK K3+K4 2000`. `STOP` відпускає всі канали між діями. Поточний `HOLD` є блокуючим: команда не перериває вже запущений `delay()`, тому аварійне відпускання в межах одного hold забезпечується верхньою межею 10 секунд.

Для комбінацій HIL-тести фізично утримують кнопки 2200 мс. DUT класифікує це як `held 2 s`; запас 200 мс потрібен, щоб release не відбувся раніше за polling/hold-threshold прошивки на точній межі 2000 мс. Окремий boundary-тест рівно 2000 мс залишається навмисно невизначеним і має фіксувати фактичну поведінку.

Прошивка:

```bash
cd hardware/button_stimulator
pio run -e nanoatmega328avrdude8 --target upload --upload-port /dev/ttyUSB0
```

Перевірка без DUT:

```bash
pio device monitor -p /dev/ttyUSB0 -b 115200
```

## Запуск стадії

Поточна окрема стадія знаходиться в `framework/tests/hil/`. Вона не запускається звичайним `python -m pytest tests/unit` або `tests/functional`.

```bash
export BUTTON_STIM_PORT=/dev/ttyUSB0
export SWM_PORT=/dev/ttyUSB1

cd framework
python -m pytest tests/hil -m hil_stage --run-hil --keep-logs
```

Smoke окремого кейса:

```bash
python -m pytest tests/hil/test_button_stage.py -m hil_stage --run-hil -k k3_k4
```

Тести вимагають реального DUT, login/Wi-Fi fixture з `framework/.env` і прошивки відповідної версії. K4 Alert-тест позначений `since_2_3_0`, тому на 2.1.0 він пропускається.

## Карта manual -> HIL

| Існуючий кейс | Поточний статус | HIL-покриття |
|---|---|---|
| `TC-BTN-01` | частково автоматизується | K1 press і UART beacon event; колір LED не доводиться |
| `TC-BTN-02` | автоматизується частково | K2 press і valve event; фізичне реле/діод потребують GPIO-аналізатора |
| `TC-BTN-03` | автоматизується частково | K3 start/stop і UART sonar; відстань і фізичні collision потребують distance stimulator |
| `TC-BTN-04` | частково автоматизується | 2.1.0 `E099`, 2.3.0 K4 ack; PANIC потребує Guard/sonar передумови |
| `TC-BTN-05` | автоматизується | K1+K2, K2+K3, K3+K4, K4+K1 з перевіркою стану |
| `TC-BTN-06` | автоматизується | K4+K1 з NORMAL і DEBUG дає `E302`; з VERBOSE має входити в EMERGENCY |
| `TC-BTN-07` | автоматизується | кнопки без login дають `E003`; реалізовано як `HIL-BTN-07` |
| `TC-BTN-08` | частково автоматизується | точні press/hold/debounce boundary; поріг 1.5 с треба підтвердити на DUT перед жорстким assert |
| `TC-BTN-09` | автоматизується для 2.1.0 | K1–K3 в EMERGENCY дають `E005`; K4 має окрему Guard/Alert поведінку |
| `TC-GD-02/03/04/06/09` | не лише кнопковий stage | UART timing можна автоматизувати, але потрібен distance stimulator |
| `TC-GD-07` | частково автоматизується | K4 hold точний, але INTRUSION/ARMED потребують sonar stimulus |
| `TC-GD-11/12` | окремий regression gate | Guard PIN counter; повинен відтворювати/підтверджувати `BUG-010` |
| `TC-LM-04/10/22` | manual | потрібна камера/фотодатчик для RGB та патернів |
| `TC-RL-01/08/15`, `TC-AL-11` | частково | UART + Arduino; фізичний GPIO8/діод потребують logic analyzer |
| `TC-DS-08/10/14/15/16/17` | manual/окремий HIL | потрібен керований стимулятор HC-SR04 |
| `TC-WF-18`, `TC-OTA-16/25` | окрема managed Wi-Fi stage | керування AP/WAN описане в `docs/managed_ap.md`, Arduino для цих кейсів не потрібен |

Статус `автоматизується` означає, що stimulus і DUT assertion можуть бути машинними. Він не означає, що LED, звук реле або геометрія відстані перевірені.

## Окремі HIL TC

| HIL ID | Призначення |
|---|---|
| `HIL-BTN-01` | K1 press -> `[BEACON] ... (K1)` |
| `HIL-BTN-02` | K2 press -> `[VALVE] ... (K2)` |
| `HIL-BTN-03` | K3 запускає і другим press зупиняє pinging |
| `HIL-BTN-04` | K4 коротко підтверджує щойно створений Alert на 2.3.0 |
| `HIL-BTN-05` | K3+K4 2 с -> `1 NORMAL -> 3 VERBOSE` |
| `HIL-BTN-06` | K4+K1 2 с з NORMAL/DEBUG -> `E302`, state unchanged |
| `HIL-BTN-09` | **2.1.0**: K1–K3 у EMERGENCY -> `E005 buttons blocked in EMERGENCY` |
| `HIL-BTN-10` | K4+K1 2 с з VERBOSE -> EMERGENCY |
| `HIL-GD-07` | Guard ARMED через UART/sonar precondition, K4 hold -> PANIC/ALARM; object placement remains physical precondition |

Ці ID навмисно окремі й не записуються в основний `docs/results.json`. Генератор трасабіліті працює з 220 кейсами, а HIL має власні докази виконання і не повинен створювати «осиротілі» TC.

## Межі та наступні кроки

Поточний набір не приховує відомі дефекти:

- `BUG-010` — NO-GO: лічильник неправильних Guard PIN не скидається після правильного PIN і нового `guard arm`; потрібен окремий HIL regression test після додавання distance stimulus;
- `BUG-002` — `distance 20` все ще FAIL;
- `BUG-003` — `relay pulse 99` все ще проходить;
- `BUG-007` — `state` відповідає в EMERGENCY поза allowlist;
- `BUG-008` — перший Alert не підтверджується через `alert ack <id>`.

Наступний технічний крок після кнопкової стадії — додати timestamp/event ID у протокол Arduino, щоб у доказах корелювати момент фізичного stimulus із UART-подією. Потім додавати logic analyzer для GPIO4/GPIO8 і окремий distance stimulus, не називаючи неповне UART-покриття повною фізичною автоматизацією.

## Результати прогонів

Підсумок усіх запусків HIL-стадії та керованого Wi-Fi на Linux-стенді: [`logs/hil/SUMMARY.md`](../logs/hil/SUMMARY.md). Станом на останній прогін усі 14 тестів кнопок і HIL-GD-07 проходять на 2.3.0; `HIL-BTN-09` вимагає прошивки 2.1.0.
