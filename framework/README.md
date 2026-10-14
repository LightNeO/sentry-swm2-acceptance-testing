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
```

Порт шукається за USB VID/PID (`SWM_VID`).

Тести, помічені `@pytest.mark.since_2_3_0`, на прошивці 2.1.0 пропускаються (версія визначається з самого пристрою).
Логи впалих тестів зберігаються в `logs/auto/v<версія>/`.

## Обмеження

Фізичні перевірки (LED, діод, реле, кнопки, HC-SR04) виконуються вручну за `docs/test_cases.md` (тип `M`).
