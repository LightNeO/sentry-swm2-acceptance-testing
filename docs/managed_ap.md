# Керований Wi-Fi стенд

## Топологія

У v3 ноутбук використовує два Wi-Fi адаптери:

```text
USB dongle wlp0s21f0u2 -> NeO -> upstream/internet

built-in wlp1s0 -> SENTRY-HIL -> ESP32 DUT
```

Поточні параметри:

```text
AP profile: SENTRY-HIL
SSID: SENTRY-HIL
password: 12345678
AP interface: wlp1s0
AP address: 10.42.0.1/24
upstream profile: NeO
upstream interface: wlp0s21f0u2
```

NetworkManager піднімає AP, а `dnsmasq` у shared-режимі видає DHCP-адреси клієнтам. USB-донгл не використовується для AP, бо його драйвер `rtl8xxxu` не оголошує режим `AP`.

## Ручна перевірка

```bash
nmcli device status
nmcli connection show --active
iw dev
ip -br addr
```

Очікується:

```text
wlp0s21f0u2 -> connected -> NeO
wlp1s0      -> connected -> SENTRY-HIL
wlp1s0      -> type AP -> channel 6
```

Перед використанням перевірити, що встановлено `dnsmasq`:

```bash
command -v dnsmasq
```

## Host controller

Код контролера: `framework/drivers/managed_ap.py`.

За замовчуванням він використовує профілі та інтерфейси вище. Їх можна змінити змінними середовища:

```bash
export HIL_AP_CONNECTION=SENTRY-HIL
export HIL_AP_INTERFACE=wlp1s0
export HIL_UPSTREAM_CONNECTION=NeO
export HIL_UPSTREAM_INTERFACE=wlp0s21f0u2
```

Контролер має тільки явно названі операції:

- `ap_up()` / `ap_down()` — вмикає або вимикає тестову точку доступу;
- `upstream_up()` / `upstream_down()` — перемикає upstream, не вимикаючи AP;
- `snapshot()` — збирає `nmcli`, `ip` і `iw` стан;
- `ensure_baseline()` / `cleanup()` — повертає обидва профілі в робочий стан.

Звичайні pytest-прогони ці команди не викликають. Для destructive Wi-Fi stage потрібні одночасно змінна `HIL_AP_CONNECTION` і прапорець `--run-managed-wifi`.

## Запуск Wi-Fi stage

У `framework/.env` для DUT мають бути вказані параметри саме тестової мережі:

```text
WIFI_SSID=SENTRY-HIL
WIFI_PASSWORD=12345678
SWM_PORT=/dev/ttyUSB1
```

Перед запуском переконатися, що ESP32 вже підключена до `SENTRY-HIL`. USB-донгл ноутбука при цьому продовжує працювати як upstream через `NeO`.

```bash
export BUTTON_STIM_PORT=/dev/ttyUSB0
export SWM_PORT=/dev/ttyUSB1
export HIL_AP_CONNECTION=SENTRY-HIL

cd framework
python -m pytest tests/wifi -m managed_wifi --run-managed-wifi --keep-logs
```

Зараз stage містить два контрольовані сценарії:

- `TC-WF-18`: вимкнення AP, очікування `W110`, повернення AP і reconnect;
- `TC-OTA-25`: відключення upstream при залишеному AP, перевірка, що Wi-Fi link DUT не зник, а OTA повертає фактичний `E402` або `E411`.

## Різні fault-класи

### AP down

```bash
nmcli connection down SENTRY-HIL
```

DUT втрачає association. Це сценарій `TC-WF-18` і Wi-Fi interruption під час `TC-OTA-16`.

### WAN down

```bash
nmcli connection down NeO
```

`SENTRY-HIL` і DHCP залишаються активними, але upstream/internet зникає. Це не те саме, що AP down. Після тесту upstream треба повернути:

```bash
nmcli connection up NeO ifname wlp0s21f0u2
```

### No DHCP і weak RSSI

Ці fault-класи не входять у поточний scope v3. Вони не повинні імітуватися вимкненням AP, бо це інший тип відмови.

## Cleanup

Після будь-якого Wi-Fi-тесту мають бути активні:

```text
NeO on wlp0s21f0u2
SENTRY-HIL on wlp1s0
dnsmasq available
```

Якщо тест упав посередині, перевірити:

```bash
nmcli connection up NeO ifname wlp0s21f0u2
nmcli connection up SENTRY-HIL ifname wlp1s0
```

Не використовувати глобальні `nft flush ruleset`, `nmcli radio wifi off` або вимкнення всіх Wi-Fi адаптерів у звичайному тесті: це може зламати upstream і сам стенд одночасно.
