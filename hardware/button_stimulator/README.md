# Arduino Nano: стимулятор кнопок K1–K4

Ця плата замінює ручне натискання кнопок SENTRY SWM-2. Це фізичне джерело стимулів для HIL, а не заміна UART-драйвера ESP32.

## Безпека підключення

Входи кнопок ESP32-S3 — це GPIO 3.3 V із внутрішньою підтяжкою. Nano працює з 5 V, тому його піни не можна переводити в `HIGH` і подавати цей рівень на GPIO38–41. Зараз використовуються послідовні резистори 1 кОм і програмний open-drain: натиснуто — `OUTPUT/LOW`, відпущено — `INPUT` (high impedance). Для фінального стенду краще використати оптопари або NPN/open-collector каскади.

| Nano output | Channel | ESP32 side |
|---|---|---|
| A2 | K1 | GPIO41 through 1 kOhm |
| A3 | K2 | GPIO40 through 1 kOhm |
| A4 | K3 | GPIO39 through 1 kOhm |
| A5 | K4 | GPIO38 through 1 kOhm |

При використанні оптопар живлення ESP32 3.3 V і Nano 5 V залишаються окремими. Спільний GND потрібен для поточної транзисторної схеми. Перед подачею живлення перевірити continuity на вимкнених платах. Для стенду бажано мати окрему фізичну кнопку аварійної зупинки.

## Прошивка

Прошивка працює на 115200 baud і приймає команди, завершені переводом рядка:

```text
PING
STATUS
PRESS K1 150
HOLD K4 1500
HOLD K3+K4 2000
STOP
```

Кожна команда одночасно утримує вибрані канали, потім переводить їх у high impedance і повертає підтвердження `OK ...`. Тривалість обмежена 1–10000 мс, щоб випадково не залишити кнопку натиснутою.

Build/upload with PlatformIO:

```bash
cd hardware/button_stimulator
pio run --target upload --upload-port /dev/ttyUSB0
```

Заміни `/dev/ttyUSB0` на фактичний порт Nano. Перед підключенням DUT перевір Nano командою `STATUS`.
Для Nano-клонів зі старим bootloader використовується середовище `nanoatmega328old`:

```bash
pio run -e nanoatmega328old --target upload --upload-port /dev/ttyUSB0
```

Цей Nano з CH340 повернув signature `ATmega328P`, але для upload йому знадобився новий пакет avrdude. Робоче середовище — `nanoatmega328avrdude8`:

```bash
pio run -e nanoatmega328avrdude8 --target upload --upload-port /dev/ttyUSB0
```

## HIL-тести

Вкажи порт Nano і запусти окрему HIL-стадію:

```bash
export BUTTON_STIM_PORT=/dev/ttyUSB0
cd framework
python -m pytest tests/hil -m hil_stage --run-hil
```

Порт ESP32 задається через `SWM_PORT` або знаходиться наявним VID-механізмом. У логах зберігаються відповіді ESP32 і результати детермінованих натискань.
