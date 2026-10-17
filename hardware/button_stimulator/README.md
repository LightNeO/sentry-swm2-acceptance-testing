# Arduino Nano K1-K4 Stimulator

This board replaces a human pressing the SENTRY SWM-2 buttons. It is a hardware-in-the-loop (HIL) stimulus source, not a replacement for the ESP32 UART driver.

## Electrical safety

The ESP32-S3 button inputs are 3.3 V GPIOs with internal pull-ups. The Nano is a 5 V board, so its pins must **not** be driven HIGH into GPIO38-41. With the current 1 kOhm series resistors, this project uses a software open-drain interface: pressed is `OUTPUT/LOW`, released is `INPUT` (high impedance). An optocoupler or NPN/open-collector stage is still the preferred final hardware solution.

| Nano output | Channel | ESP32 side |
|---|---|---|
| A2 | K1 | GPIO41 through 1 kOhm |
| A3 | K2 | GPIO40 through 1 kOhm |
| A4 | K3 | GPIO39 through 1 kOhm |
| A5 | K4 | GPIO38 through 1 kOhm |

Keep the ESP32 3.3 V and Nano 5 V supplies separate when using optocouplers. Connect grounds only if the chosen transistor board explicitly requires a common ground. Add a physical emergency stop and verify continuity with both boards unpowered.

## Firmware

The sketch uses 115200 baud and accepts newline-terminated commands:

```text
PING
STATUS
PRESS K1 150
HOLD K4 1500
HOLD K3+K4 2000
STOP
```

Each action holds the selected channels simultaneously, releases them to high impedance, and returns an `OK ...` acknowledgement. Durations are limited to 1-10000 ms to avoid an accidental permanent press.

Build/upload with PlatformIO:

```bash
cd hardware/button_stimulator
pio run --target upload --upload-port /dev/ttyUSB0
```

Replace `/dev/ttyUSB0` with the actual Nano port. The command above intentionally has no hidden ESP32 assumptions; test the Nano with `STATUS` before connecting the DUT.
For Nano clones with the old bootloader, use the `nanoatmega328old` environment:

```bash
pio run -e nanoatmega328old --target upload --upload-port /dev/ttyUSB0
```

This particular CH340 Nano reported the `ATmega328P` signature but required the newer avrdude package. Its working upload environment is `nanoatmega328avrdude8`:

```bash
pio run -e nanoatmega328avrdude8 --target upload --upload-port /dev/ttyUSB0
```

## Pytest HIL tests

Set the Nano port and run only the new tests:

```bash
export BUTTON_STIM_PORT=/dev/ttyUSB0
cd framework
python -m pytest tests/hil -m hil_stage --run-hil
```

The existing UART DUT port remains configured by `SWM_PORT` or the existing VID discovery. The test logs therefore contain both the ESP32 response and deterministic stimulus timing.
