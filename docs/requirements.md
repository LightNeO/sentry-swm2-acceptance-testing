# Реєстр вимог SENTRY SWM-2 (fw_7)

Джерело істини: `fw_7/PRD.md`. Тут PRD розкладено на атомарні перевіряємі вимоги з тими самими ID, що вже є в PRD (AC, ST, WF, AU, OTA, LM, RL, DS, HL, GD, AL), плюс `BTN` для розділу 12 «Кнопки» та `SYS` для розділу 13 «Система».

## Позначення

- **Ver**: `21` — діє в 2.1.0 і 2.3.0; `23` — з 2.3.0 (у 2.1.0 очікується `E099 ... planned in v2.3.0`).
- **P (пріоритет)**: P1 — критично (безпека, втрата даних, brick); P2 — важливо; P3 — другорядно.
- **Тип перевірки**: `A` — автотест; `M` — ручна/мануальна; `A+M` — обидві.
- **Межі** — значення для граничного аналізу: `мін-1 / мін / макс / макс+1`.

---

## 1. Доступ і стани

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| AC-1a | Команда без позначки доступна завжди | 21 | P2 | A | |
| AC-1b | `[wifi]` без Wi-Fi → `E002` | 21 | P1 | A | |
| AC-1c | `[login]` без Wi-Fi + входу → `E003` | 21 | P1 | A | |
| AC-1d | `[debug]` без debug-доступу → `E004` | 21 | P1 | A | |
| AC-2a | Невідома команда → `E001 unknown command '<x>'. Type 'help'` | 21 | P2 | A | |
| AC-2b | Регістр першого слова не важливий | 21 | P3 | A | `HELP`, `Help`, `hElP` |
| AC-2c | Нелатинські символи ігноруються з `W006` | 21 | P3 | A | кирилиця, емодзі |
| ST-1a | `state` показує поточний стан [login] | 21 | P2 | A | |
| ST-1b | `state <1-4\|name>` змінює стан [login] | 21 | P1 | A | межі: 0, 1, 4, 5; імена |
| ST-1c | DEBUG: сирі дані датчика, `[DBG]`, LED blink-коди | 21 | P2 | A+M | LED — очима |
| ST-1d | VERBOSE: `[V]`, health кожні 10 с, LED heartbeat, `Did you mean` | 21 | P2 | A+M | |
| ST-2 | EMERGENCY лише з VERBOSE, інакше `E302`, стан не змінюється (команда і кнопки) | 21 | P1 | A+M | з 1, 2, 3, 4 |
| ST-3a | В EMERGENCY дозволені лише `help,status,whoami,version,health now,alert list(23),reboot` | 21 | P1 | A | |
| ST-3b | Інша команда в EMERGENCY → E005/E001 і температура драйвера росте | 21 | P2 | A | |
| ST-3c | При 95 °C — аварійний reboot | 21 | P2 | A | довго, емпірично |
| ST-3d | Вихід з EMERGENCY лише reboot (`E304`) | 21 | P1 | A | |
| ST-3e | Кнопки в EMERGENCY → `E005 buttons blocked in EMERGENCY` | 21 | P2 | A | |
| ST-4a | Повторний перехід у поточний стан → `W303` | 21 | P3 | A | |
| ST-4b | `logout` повертає DEBUG/VERBOSE у NORMAL | 21 | P2 | A | |
| ST-4c | Після reboot завжди NORMAL | 21 | P1 | A | |

## 2. Wi-Fi

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| WF-1a | `connect`: scan → список → SSID (назва/номер) → пароль | 21 | P1 | A+M | |
| WF-1b | Пароль <8 символів → `E112` | 21 | P2 | A | 7 / 8 / 63 / 64 |
| WF-1c | Порожній SSID → `E111` | 21 | P2 | A | |
| WF-1d | Успіх: `got ip`, `connected to '<ssid>', rssi N dBm`, перевірка інтернету, NTP | 21 | P1 | A | |
| WF-1e | Мережа зберігається в NVS | 21 | P1 | A | reboot |
| WF-2 | Коди помилок: E101 пароль, E102 немає мережі, E103 шифрування, E104 DHCP, E105 інтернет, W106 NTP, W107 слабкий сигнал, E108 інше | 21 | P2 | A (частково) | У поточному scope перевіряються лише E101/E102 (`TC-WF-06/07`); E103/E104/E105/W106/W107 свідомо виключені з тестування |
| WF-3a | `reconnect`: немає збереженої → `E113`; вже підключено → `W114` | 21 | P2 | A | |
| WF-3b | `forget` стирає мережу | 21 | P2 | A | |
| WF-3c | `disconnect`; не підключено → `W115` | 21 | P2 | A | |
| WF-3d | Автопідключення при старті немає; boot log `known network '<ssid>'. Type 'reconnect'` | 21 | P2 | A | |
| WF-4a | `scan` — список мереж з RSSI | 21 | P3 | A | |
| WF-4b | `net` — IP, gateway, DNS, MAC [wifi] | 21 | P3 | A | |
| WF-4c | `ping [host]`, за замовчуванням 8.8.8.8 | 21 | P3 | A | |
| WF-4d | `time`; не синхронізовано → `E121` | 21 | P3 | A | |
| WF-5 | Втрата з'єднання → `W110`, 3 автоспроби перепідключення | 21 | P1 | A | керовано вимкнути AP `SENTRY-HIL` і повернути його |

## 3. Акаунт

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| AU-1a | `register`: один профіль на пристрій, повторно → `E202` | 21 | P1 | A | |
| AU-1b | Login 3–16 символів `a-zA-Z0-9_` → інакше `E204` | 21 | P1 | A | довжина 2/3/16/17; символи `-`, пробіл, `ї` |
| AU-1c | Пароль 6–32 → інакше `E205` | 21 | P1 | A | 5/6/32/33 |
| AU-1d | Login `debug` зарезервований → `E203` | 21 | P2 | A | `DEBUG`, `Debug` (регістр!) |
| AU-1e | Профіль у NVS, переживає reboot і OTA | 21 | P1 | A | |
| AU-2a | Невірні дані → `E209 ... Attempts: N/3` | 21 | P1 | A | |
| AU-2b | 3 невдалі → `E210 ... locked for 30 s`, далі `E207 ... Try again in N s` | 21 | P1 | A | перевірити таймер 30 с (29/30/31) |
| AU-2c | Обмеження діє на **будь-який** login, що вводиться | 21 | P1 | A | неіснуючий login теж рахується |
| AU-2d | Вже увійшли → `E206` | 21 | P2 | A | |
| AU-3a | `logout`: вимикає лампу, реле, зупиняє виміри; DEBUG/VERBOSE → NORMAL | 21 | P1 | A+M | |
| AU-3b | `logout` без сесії → `W211` | 21 | P3 | A | |
| AU-4 | `whoami` → `user: <login>, access: user\|debug` | 21 | P2 | A | до і після `sudo` |
| AU-5a | `passwd`: новий пароль працює після logout/reboot/OTA, старий — ні | 21 | P1 | A | |
| AU-5b | Невірний старий → `E215`; новий 6–32 → `E205` | 21 | P1 | A | 5/6/32/33 |
| AU-6a | `sudo <pwd>` піднімає до debug; невірний → `E213`; вже debug → `W212` | 21 | P1 | A | |

## 4. OTA

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| OTA-1 | `version`: рядок формату PRD + `partition ... state: valid`; версія однакова у `version`/boot/`ota` | 21 | P2 | A | |
| OTA-2 | `ota`/`ota status`: поточна + попередня прошивка | 21 | P2 | A | |
| OTA-3 | `ota check`: current/stable/beta + `update available`/`up to date (stable)`/`running newer than stable` | 21 | P2 | A | |
| OTA-4a | `ota update` ставить stable, `ota update beta` — beta | 21 | P1 | A | |
| OTA-4b | Та сама версія → `[OTA] already up to date`, без завантаження і reboot | 21 | P2 | A | |
| OTA-5a | `ota install <X.Y.Z>`: формат → `E414`; немає → `E415` | 21 | P2 | A | `2.1`, `2.1.0.0`, `a.b.c`, `9.9.9` |
| OTA-5b | Даунгрейд без force → `E408`, прошивка не змінюється | 21 | P1 | A | |
| OTA-5c | З `force` дозволено; та сама версія з `force` → `W409` | 21 | P2 | A | |
| OTA-6 | Процес: `current → target`, `downloading`, `image`, прогрес по 10 %, `success ... Rebooting` | 21 | P2 | A | |
| OTA-7 | Self-check: `PENDING_VERIFY` → `passed, marked VALID` | 21 | P1 | A | |
| OTA-8a | `ota broken` → `self-check FAILED ... Rolling back...`, повернення, state valid | 21 | P1 | A | |
| OTA-8b | `ota rollback`: немає → `E416`; invalid → `E417` | 21 | P1 | A | |
| OTA-9 | Помилки E401–E412; після помилки пристрій працює і наступна OTA проходить | 21 | P1 | A+M | E401 одночасні; E402/E403 сервер; E410 `--drop-at`; E411 `--slow`+Wi-Fi off; E406 garbage; E412 corrupted; truncated |
| OTA-10 | Після OTA (up/down/rollback) зберігаються: Wi-Fi, профіль+пароль, лампа+сцени, лічильник+auto реле, калібрування/alarm/filter, health, PIN+зона Guard | 21 | P1 | A | список із 8 груп даних |
| OTA-11 | `ota url <url> [force]`; не http/https → `E418` | 21 | P2 | A | `ftp://`, `file://`, порожній |
| OTA-12 | `ota server [<url>\|default]`; зберігається в NVS; `default` повертає GitHub | 21 | P2 | A | |

## 5. Лампа (Smart Lamp, K1)

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| LM-1 | `lamp on\|off\|toggle` [login]; повторне on/off → `W510`; після reboot/logout вимкнена | 21 | P2 | A+M | |
| LM-2a | Кольори: white red green blue yellow purple cyan orange | 21 | P2 | A+M | усі 8 очима |
| LM-2b | `lamp color R G B` 0–255, інакше `E502` | 21 | P1 | A+M | -1/0/255/256 для кожного каналу |
| LM-2c | Невідомий колір → `E503` | 21 | P3 | A | регістр `RED` |
| LM-3 | `lamp brightness 0-100`, інакше `E504` | 21 | P1 | A+M | -1/0/100/101 |
| LM-4 | `lamp mode solid\|blink\|breathe\|rainbow`, інакше `E505`; яскравість діє в усіх режимах | 21 | P2 | A+M | |
| LM-5a | `lamp timer 1-3600`, `[BEACON] auto-off in N s` (секунди) | 21 | P1 | A | 0/1/3600/3601 |
| LM-5b | `timer 0` скасовує; поза діапазоном → `E506`; лампа вимкнена → `E507`; `status` → `timer N s left` | 21 | P2 | A | |
| LM-6 | `scene save\|load 1-3`; номер → `E508`; порожня → `E509`; зберігає колір+яскравість+режим | 21 | P2 | A | 0/1/3/4 |
| LM-7 | `lamp status` формат `ON\|off, color (r,g,b), brightness N%, mode <m>, timer ...`; NVS | 21 | P1 | A | reboot |
| LM-8 | Пріоритет LED: EMERGENCY > Guard ALARM > OTA > помилка датчика > Guard INTRUSION/ARMING > лампа > стан | 21/23 | P2 | M | Guard — лише 2.3.0 |

## 6. Реле / клапан (K2, діод GPIO4)

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| RL-1a | `relay on\|off\|toggle`; діод світить коли ON; повторне → `W601` | 21 | P1 | A+M | діод очима |
| RL-1b | Не більше 2 перемикань за секунду → `E602` | 21 | P2 | A | |
| RL-2 | `relay status`: стан, auto, `cycles N` (за весь час, +1 за on або off); NVS | 21 | P1 | A | reboot |
| RL-3 | `relay pulse 100-10000`; інакше `E603 pulse must be 100-10000 ms`; вже ON → `E604` | 21 | P1 | A+M | 99/100/10000/10001 |
| RL-4 | `relay schedule <on> <off>` 2–3600 с, інакше `E606`; `schedule off`; `W605` | 21 | P2 | A | 1/2/3600/3601 для кожного параметра |
| RL-5 | `relay auto on\|off` — вмикати реле при перетині порога alarm | 21 | P2 | A+M | |
| RL-6 | `relay health` — знос контактів (ресурс 100000), стан котушки | 21 | P3 | A | |
| RL-7 | `logout` вимикає реле, імпульс, розклад (крім Guard ALARM) | 21 | P1 | A | |

## 7. Активний сонар HC-SR04 (K3)

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| DS-1 | `distance` — один вимір; `distance N` — N вимірів **1–20 включно** + середнє; інакше `E704` | 21 | P1 | A | 0/1/20/21 |
| DS-2a | `distance log [100-5000]`, інакше `E705`; `distance stop`; `W710` | 21 | P2 | A | 99/100/5000/5001 |
| DS-2b | Під час log інші `distance ...` → `E711` | 21 | P2 | A | |
| DS-3 | `distance calibrate 5-300`, скидання окремою командою `distance reset` (не `calibrate reset` — текст у `help` вводить в оману); E706/E707 | 21 | P2 | A+M | 4/5/300/301; об'єкт на відомій відстані |
| DS-4 | `alarm 5-300\|off`; `PROXIMITY ALARM`/`cleared`; гістерезис 5 см; `E708` | 21 | P1 | A+M | 4/5/300/301 |
| DS-5a | `filter on\|off` (медіана з 5; за замовч. on) | 21 | P3 | A | |
| DS-5b | `stats` (кількість, помилки, min/max/avg), `history` — останні 10 | 21 | P2 | A | |
| DS-6a | `<20 см` → `[COLLISION]` один раз на наближення, знову після віддалення >25 см | 21 | P1 | M | лінійка/долоня |
| DS-6b | Немає ехо → `E701`; поза діапазоном → `E702` + LED червоний 2 с | 21 | P2 | A+M | |
| DS-7 | Діод блимає частіше при ближчому об'єкті, <10 см постійно (клапан open + виміри) | 21 | P2 | M | |

## 8. Health

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| HL-1a | Автозвіт кожні 30 с (налаштовується), VERBOSE 10 с, EMERGENCY 5 с | 21 | P1 | A | таймінг ±1 с |
| HL-1b | Формат `[TELEMETRY #N] ... up heap rssi temp depth hull batt valve sonar state [WARN]` | 21 | P2 | A | regexp |
| HL-1c | З 2.3.0 у рядку `watch <стан> alerts <N>` | 23 | P2 | A | |
| HL-2 | Попередження: low heap, weak signal, no internet, sensor error, overheat, guard alarm(23) | 21 | P3 | A (частково) | |
| HL-3a | `health` / `health now` | 21 | P2 | A | |
| HL-3b | `health on\|off`; повторно → `W901` | 21 | P3 | A | |
| HL-3c | `health interval 10-300` **включно**, інакше `E902`; NVS | 21 | P1 | A | 9/10/300/301 |

## 9. Guard (лише 2.3.0, K4)

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| GD-1 | `guard arm`: `arming in N s` (10 с) → `ARMED`; `guard`/`status` | 23 | P1 | A+M | |
| GD-2a | Об'єкт ближче зони (50 см за замовч.) → `INTRUSION`, 15 с на PIN, інакше `ALARM` | 23 | P1 | A+M | |
| GD-2b | `guard zone 10-200`, інакше `E808` | 23 | P2 | A | 9/10/200/201 |
| GD-3 | ALARM: `guard panic`, утримання K4, 3 невірні PIN, 3 виміри без ехо (tamper); ALARM = CRITICAL alert + реле ON + LED + нагадування кожні 10 с | 23 | P1 | A+M | |
| GD-4a | `guard disarm <pin>`; PIN за замовч. 1234; `E803 ... Attempts: N/3`, на 3-й — ALARM | 23 | P1 | A | |
| GD-4b | Лічильник спроб **з нуля** при кожному `guard arm` і після правильного PIN | 23 | P1 | A | регресійна пастка |
| GD-5a | `guard pin <old> <new>` 4 цифри (`E804`), лише коли знято з охорони (`E807`) | 23 | P1 | A | 3/4/5 цифр, літери |
| GD-5b | `guard log` — останні 10 подій | 23 | P3 | A | |
| GD-5c | `logout` охорону не знімає | 23 | P1 | A | |

## 10. Alert center (лише 2.3.0)

| ID | Вимога | Ver | P | Тип | Межі / нотатки |
|---|---|---|---|---|---|
| AL-1 | Останні 20 alerts, рівні INFO/WARNING/CRITICAL; формат `[CIC #id LEVEL] src: text` | 23 | P2 | A | створити 21+ |
| AL-2 | `alert`/`alert list`, `*` — непідтверджений | 23 | P2 | A | |
| AL-3a | `alert ack` — останній непідтверджений | 23 | P2 | A | |
| AL-3b | `alert ack <id>` — **саме цей** id; нема → `E851`; вже → `W852` | 23 | P1 | A | перевірка що не підтверджується інший |
| AL-3c | `alert ack all`; `W853` якщо нема чого | 23 | P3 | A | |
| AL-4a | `alert clear` лише коли все підтверджено, інакше `E855` | 23 | P2 | A | |
| AL-4b | `alert test info\|warning\|critical`; `E854` | 23 | P2 | A | |
| AL-5 | CRITICAL (крім EMERGENCY): реле ON і NORMAL/DEBUG → VERBOSE | 23 | P1 | A+M | |

## 11. Кнопки (потрібен login, інакше `E003`)

| ID | Вимога | Ver | P | Тип |
|---|---|---|---|---|
| BTN-1 | K1: press — лампа on/off, hold 1.5 с — наступний колір | 21 | P2 | A+M |
| BTN-2 | K2: press — реле on/off, hold 1.5 с — імпульс 1 с | 21 | P2 | A+M |
| BTN-3 | K3: press — виміри 30 с кожні 500 мс; ще раз — стоп | 21 | P2 | A+M |
| BTN-4 | K4: press — ack alert, hold 1.5 с — PANIC (у 2.1.0 → `E099`) | 23 | P2 | A+M |
| BTN-5 | Комбінації hold 2 с: K1+K2 → 1, K2+K3 → 2, K3+K4 → 3, K4+K1 → 4 (лише з 3, ST-2) | 21/23 | P2 | A |
| BTN-6 | Кнопка без login → `E003` | 21 | P2 | A |

## 12. Система

| ID | Вимога | Ver | P | Тип |
|---|---|---|---|---|
| SYS-1 | `help` — по групах з позначками доступу | 21 | P3 | A |
| SYS-2 | `status` — прошивка, стан, Wi-Fi, користувач, час, реле, guard(23), відстань, heap | 21 | P2 | A |
| SYS-3 | `sysinfo`, `temp`, `uptime` | 21 | P3 | A |
| SYS-4 | `reboot` — відлік 3-2-1 і перезавантаження | 21 | P2 | A |
| SYS-5 | Boot log: версія, розділ, `last reset: power on\|software reboot\|PANIC\|watchdog\|brownout` | 21 | P2 | A |

## 13. Нефункціональне (з розділів 0–2 PRD)

| ID | Вимога | Ver | P | Тип |
|---|---|---|---|---|
| NFR-1 | Кожна наступна версія містить весь функціонал попередньої і працює не гірше (регресія) | 23 | P1 | A |
| NFR-2 | Фонова телеметрія (`[NAV]`,`[ACU]`,`[PWR]`,`[HW]`,`[LINK]`) і `W` без коду — не баги | 21 | — | — (виключення зі scope) |
| NFR-3 | Помилки мають код `E<код>` / `W<код>` | 21 | P2 | A |
| NFR-4 | Некоректний ввід не призводить до зависання/перезавантаження (fuzz) | 21 | P1 | A |
| NFR-5 | Тематичні аліаси еквівалентні основним командам | 21/23 | P3 | A |

## 14. Додаткові дослідницькі цілі (не з PRD)

| ID | Ціль | Ver | P | Тип |
|---|---|---|---|---|
| RES-1 | Приховані команди (відсутні в `help`) | 21 | P1 | M |
| RES-2 | Секрети у boot log / бінарнику / відповідях | 21 | P1 | M |
| RES-3 | Захист `sudo` / `debug` від перебору | 21 | P1 | A |
| RES-4 | Відкритий текст паролів у логах | 21 | P2 | M |

---

## Підсумок кількості

- Вимог загалом: 139 атомарних ID.
- P1 — основа ризикового тестування: межі діапазонів, NVS-збереження, блокування логіну, OTA-безпека, Guard-лічильник.
