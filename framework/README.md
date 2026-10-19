# Фреймворк автотестів SENTRY SWM-2

Автотести керують пристроєм через UART-консоль (115200 8N1) і перевіряють відповіді проти PRD.

## Структура

```
framework/
├── drivers/
│   ├── protocol.py       # парсер виводу пристрою (без I/O)
│   ├── redaction.py      # маскування паролів -> ***
│   ├── transport.py      # SerialTransport (реальний UART) + FakeTransport (для unit-тестів)
│   └── device_driver.py  # SwmDevice: команди, промпти, перезавантаження, Wi-Fi, login
├── tests/
│   ├── unit/             # перевірка самого фреймворку, без залізa
│   ├── smoke/            # пристрій живий і ідентифікований
│   └── functional/       # межі діапазонів та інше за PRD
├── conftest.py           # fixtures, логи-докази, запис результатів
├── pytest.ini            # маркери
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
python tools/sanitize_logs.py ../logs/hil      # сховати імена чужих мереж перед комітом
# з кореня репозиторію: bash run_hil_evidence.sh (повний прогін x3), bash run_hil_recheck.sh (лише виправлені тести)
# bash run_hil_recheck_strict.sh (TC-WF-11/12/18, TC-OTA-25 після посилення перевірок; потрібна HIL_UPSTREAM_CONNECTION)
```

Порт шукається за USB VID/PID (`SWM_VID`).

Тести, помічені `@pytest.mark.since_2_3_0`, на прошивці 2.1.0 пропускаються (версія визначається з самого пристрою).
Логи впалих тестів зберігаються в `logs/auto/v<версія>/`.

## Обмеження

Фізичні перевірки (LED, діод, реле, кнопки, HC-SR04) виконуються вручну за `docs/test_cases.md` (тип `M`).
