# Фреймворк автотестів SENTRY SWM-2

Автотести керують пристроєм через UART-консоль (115200 8N1) і перевіряють відповіді проти PRD.

## Структура

```
framework/
├── drivers/
│   ├── protocol.py            # парсер виводу пристрою (без I/O)
│   ├── redaction.py           # маскування паролів -> ***
│   ├── transport.py           # SerialTransport (реальний UART) + FakeTransport (для unit-тестів)
│   ├── device_driver.py       # SwmDevice: команди, промпти, перезавантаження, Wi-Fi, login
│   ├── button_stimulator.py   # керування Arduino Nano: press/hold/комбінації K1-K4
│   ├── managed_ap.py          # керований AP/upstream через NetworkManager
│   └── ota_server_process.py  # локальний OTA-сервер як підпроцес (повільний OTA)
├── tests/
│   ├── unit/                  # перевірка самого фреймворку, без заліза
│   ├── smoke/                 # пристрій живий і ідентифікований
│   ├── functional/            # межі діапазонів та інше за PRD
│   ├── hil/                   # Arduino-кнопки (потрібен --run-hil)
│   ├── wifi/                  # керований Wi-Fi і OTA fault-injection (потрібен --run-managed-wifi)
│   └── helpers.py             # спільні функції тестів
├── tools/                     # одноразові скрипти доказів і генератор трасабіліті
├── conftest.py                # fixtures, логи-докази, запис результатів
├── pytest.ini                 # маркери
└── requirements.txt
```

## Запуск

```bash
# налаштування: cp .env.example .env і заповнити
python -m pytest tests/unit                  # без пристрою
python -m pytest tests/smoke                 # потрібен DUT на UART
python -m pytest tests/functional -m boundary
python -m pytest --record                    # + записати результати в docs/results.json
python -m pytest --keep-logs                 # + транскрипт для кожного тесту
python ../framework/tools/gen_traceability.py # перегенерувати docs/traceability.md
python tools/register_bounds.py                # AU-1b/1c: межі register на чистому NVS (стирає лише NVS, потрібен DUT)
python -m pytest tests/hil -m hil_stage --run-hil              # Arduino-стимулятор кнопок (BUTTON_STIM_PORT, SWM_PORT)
python -m pytest tests/wifi -m managed_wifi --run-managed-wifi  # керований AP/WAN (HIL_AP_CONNECTION=SENTRY-HIL, Linux + NetworkManager)
# для tests/wifi потрібні: HIL_AP_CONNECTION=SENTRY-HIL, HIL_UPSTREAM_CONNECTION=<ім'я upstream-профілю>; TC-OTA-16 (test_slow_ota.py) сам піднімає OTA-сервер
```

Порт шукається за USB VID/PID (`SWM_VID`).

Тести, помічені `@pytest.mark.since_2_3_0`, на прошивці 2.1.0 пропускаються (версія визначається з самого пристрою).
Логи впалих тестів зберігаються в `logs/auto/v<версія>/`.

## Обмеження

Кнопки K1–K4 і мережеві відмови подає HIL-стенд (Arduino Nano, керований AP). Решта фізичних перевірок (RGB LED, діод, клацання реле, реальна відстань для HC-SR04) виконується вручну за `docs/test_cases.md` (тип `M` або `A+M`).
