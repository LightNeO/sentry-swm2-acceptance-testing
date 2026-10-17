# Тест-кейси SENTRY SWM-2 (fw_7)

Пов'язано з: `requirements.md` (ID вимог), `test_plan.md`, `traceability.md` (генерується з цього файлу).

## Як читати

- **TC** — ID кейса. Формат `TC-<блок>-<NN>`.
- **Req** — ID вимоги з `requirements.md`.
- **Ver** — на яких версіях виконується: `21` (обидві, регресія на 2.3.0), `23` (лише 2.3.0). У 2.1.0 для `23`-функцій перевіряється `E099`.
- **Тип** — `A` автотест, `M` ручний, `A+M` обидва.
- **Межі** — параметризований кейс: один TC перевіряється на всіх значеннях (мін-1 / мін / макс / макс+1).
- Загальна передумова для всіх кейсів: DUT після reboot, стан `1 NORMAL`, якщо не вказано інше. Для `[login]` команд — виконаний `login`.
- Кожен кейс після виконання повертає DUT у відомий стан (`logout`, `lamp off`, `relay off`).

Результат виконання фіксується у `traceability.md` (колонки 2.1.0 / 2.3.0 / Bug).

---

## 1. Доступ і стани (AC, ST)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-AC-01 | AC-1a | Без Wi-Fi і login виконати `help`, `status`, `version`, `uptime`, `sysinfo`, `temp`, `whoami`, `logout`, `scan` | Усі відповідають без E002/E003 | 21 | A |
| TC-AC-02 | AC-1b | Без Wi-Fi виконати `net`, `ping`, `time`, `register a b` | Кожна → `E002` | 21 | A |
| TC-AC-03 | AC-1c | Wi-Fi є, login немає: `lamp on`, `relay on`, `distance`, `state`, `ota`, `health now`, `passwd a b`, `sudo x` | Кожна → `E003` | 21 | A |
| TC-AC-04 | AC-1c | Без Wi-Fi: ті самі `[login]` команди | `E002` або `E003` (PRD не визначає пріоритет); фактично `E002 Wi-Fi required`; команда не виконується | 21 | A |
| TC-AC-05 | AC-1d | Login без sudo: виконати debug-команди, знайдені в дослідженні | `E004` | 21 | A |
| TC-AC-06 | AC-2a | Ввести `foo`, `lamp2`, `statuss` | `E001 unknown command '<x>'. Type 'help'` | 21 | A |
| TC-AC-07 | AC-2b | `HELP`, `Help`, `STATUS`, `Version` | Працюють як `help`, `status`, `version` | 21 | A |
| TC-AC-08 | AC-2c | `привіт`, `status ї`, `🙂` | Нелатинські символи ігноруються з `W006`, пристрій не зависає | 21 | A |
| TC-AC-09 | AC-2a | Порожній рядок (Enter), рядок із пробілів, дуже довга команда (1000 символів) | Без reboot і зависання (див. NFR-4) | 21 | A |
| TC-ST-01 | ST-1a,ST-1b | Login → `state` → `state 2` → `state debug` → `state 3` → `state verbose` → `state 1` | Стан змінюється, вивід містить N NAME | 21 | A |
| TC-ST-02 | ST-1b | Межі: `state 0`, `state 5`, `state -1`, `state abc`, `state` + пробіли | Помилка, стан не змінюється, без reboot | 21 | A |
| TC-ST-03 | ST-1c | `state 2`; `distance` | Сирі дані без фільтра/калібрування, `[DBG]`; LED показує blink-коди (очима) | 21 | A+M |
| TC-ST-04 | ST-1d | `state 3`; чекати 10–12 с; ввести `foo` | `[V]` логи, health кожні ~10 с, LED heartbeat (очима), `Did you mean '<cmd>'?` | 21 | A+M |
| TC-ST-05 | ST-2 | З кожного стану 1,2,4 виконати `state 4` | `E302 EMERGENCY can be entered only from 3 VERBOSE (now N NAME)`, стан не змінився | 21 | A |
| TC-ST-06 | ST-2 | `state 3` → `state 4` | Перехід у EMERGENCY, глибина в телеметрії зменшується | 21 | A |
| TC-ST-07 | ST-2 | Те саме через кнопки: K4+K1 з 1, 2, 3 | З 1,2 → `E302`; з 3 → EMERGENCY | 21 | M |
| TC-ST-08 | ST-3a | У EMERGENCY: `help`, `status`, `whoami`, `version`, `health now`, `reboot` | Усі працюють | 21 | A |
| TC-ST-09 | ST-3a | У EMERGENCY (2.3.0): `alert list` | Працює | 23 | A |
| TC-ST-10 | ST-3b | У EMERGENCY: `lamp on`, `relay on`, `distance`, `state 1`, `logout` | Кожна → E005/E001; температура драйвера в наступному health росте | 21 | A |
| TC-ST-11 | ST-3c | У EMERGENCY повторювати заборонені команди | При 95 °C — аварійний reboot, `last reset` показує причину | 21 | A |
| TC-ST-12 | ST-3d | У EMERGENCY: `state 1`, `logout` | `E304`; вихід лише `reboot` | 21 | A |
| TC-ST-13 | ST-3e | У EMERGENCY натиснути K1, K2, K3 | `E005 buttons blocked in EMERGENCY` | 21 | M |
| TC-ST-14 | ST-4a | `state 2` двічі; `state 1` у NORMAL | `W303 already in N NAME` | 21 | A |
| TC-ST-15 | ST-4b | `state 2` → `logout`; `state 3` → `logout` | Стан NORMAL | 21 | A |
| TC-ST-16 | ST-4c | `state 3` → `reboot` | Після старту стан `1 NORMAL` | 21 | A |

## 2. Wi-Fi (WF)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-WF-01 | WF-1a,WF-1d | `connect`, вибрати мережу за номером, ввести пароль | scan-список; `got ip`; `connected to '<ssid>', rssi N dBm`; перевірка інтернету; NTP | 21 | A |
| TC-WF-02 | WF-1a | `connect`, вибрати мережу за назвою | Те саме | 21 | A |
| TC-WF-03 | WF-1b | Пароль довжиною 7 (E112), 8 (приймається), 63, 64 для мережі без відповідного пароля (проходить валідацію, далі E101) | 7 → `E112`; ≥8 → спроба підключення | 21 | A |
| TC-WF-04 | WF-1c | `connect`, SSID порожній | `E111` | 21 | A |
| TC-WF-05 | WF-1e,WF-3d | Після підключення `reboot` | Boot log `known network '<ssid>'. Type 'reconnect'`, автопідключення немає | 21 | A |
| TC-WF-06 | WF-2 | Неправильний пароль до існуючої мережі | `E101` | 21 | A |
| TC-WF-07 | WF-2 | SSID, якого немає | `E102` | 21 | A |
| TC-WF-10 | WF-3a | `reconnect` без збереженої мережі; після підключення ще раз | `E113`; `W114` | 21 | A |
| TC-WF-11 | WF-3a | `reconnect` після `disconnect` | Підключення до збереженої | 21 | A |
| TC-WF-12 | WF-3b | `forget` → `reboot` | У boot log немає `known network`; `reconnect` → `E113` | 21 | A |
| TC-WF-13 | WF-3c | `disconnect` двічі | Перший відключає, другий `W115` | 21 | A |
| TC-WF-14 | WF-4a | `scan` | Список мереж з RSSI | 21 | A |
| TC-WF-15 | WF-4b | `net` | IP, gateway, DNS, MAC | 21 | A |
| TC-WF-16 | WF-4c | `ping`, `ping 1.1.1.1`, `ping invalid.host.zzz` | 8.8.8.8 за замовчуванням; помилка для невалідного хоста без зависання | 21 | A |
| TC-WF-17 | WF-4d | `time` до і після NTP | `E121` до синхронізації; час після | 21 | A |
| TC-WF-18 | WF-5 | Керовано вимкнути AP `SENTRY-HIL` під час сесії | `W110 wifi connection lost`, 3 автоспроби; після повернення AP — reconnect і стан зафіксовано | 21 | A |

## 3. Акаунт (AU)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-AU-01 | AU-1a | `register qa_swm Pass1234` | Профіль створено | 21 | A |
| TC-AU-02 | AU-1a | Повторний `register other Pass1234` | `E202` | 21 | A |
| TC-AU-03 | AU-1b | **Межі довжини login**: 2 (`ab`), 3 (`abc`), 16, 17 символів (на чистому NVS перед кожним — `forget`/erase профілю неможливо, тому використовувати окремі прогони після erase-flash або перевіряти E204 до перевірки E202) | 2, 17 → `E204`; 3, 16 → успіх | 21 | A |
| TC-AU-04 | AU-1b | Недопустимі символи: `ab-c`, `ab c`, `abї`, `ab@c`, `ab.c` | `E204` | 21 | A |
| TC-AU-05 | AU-1c | **Межі пароля**: 5, 6, 32, 33 символи | 5, 33 → `E205`; 6, 32 → успіх | 21 | A |
| TC-AU-06 | AU-1d | `register debug Pass1234`, `register DEBUG ...`, `register Debug ...` | `E203` (перевірити, чи регістр обходить заборону) | 21 | A |
| TC-AU-07 | AU-1e | Створити профіль → `reboot` → login | Login успішний | 21 | A |
| TC-AU-08 | AU-2a | `login qa_swm wrong` | `E209 wrong login or password. Attempts: 1/3` | 21 | A |
| TC-AU-09 | AU-2b | Три помилкові спроби поспіль | 1/3, 2/3, `E210 ... locked for 30 s` | 21 | A |
| TC-AU-10 | AU-2b | Під блокуванням спробувати правильний пароль; виміряти час до розблокування | `E207 ... Try again in N s` (N спадає); розблокування через 30 с ±1 | 21 | A |
| TC-AU-11 | AU-2c | Три помилкові спроби з **неіснуючим** login (`nouser x`) | Лічильник теж рахується, блокування спрацьовує | 21 | A |
| TC-AU-12 | AU-2c | Змішані: 2 помилки з одним login + 1 з іншим | Блокування на третій | 21 | A |
| TC-AU-13 | AU-2d | Увійшовши, повторити `login` | `E206` | 21 | A |
| TC-AU-14 | AU-2a | Після успішного login лічильник спроб скидається | Наступна помилка → `Attempts: 1/3` | 21 | A |
| TC-AU-15 | AU-3a | Login → `lamp on`, `relay on`, `distance log`, `state 3` → `logout` | Лампа, реле вимкнені (очима), виміри зупинені, стан NORMAL | 21 | A+M |
| TC-AU-16 | AU-3b | `logout` без сесії | `W211` | 21 | A |
| TC-AU-17 | AU-4 | `whoami` до login, після login, після `sudo` | `user: <login>, access: user` → `access: debug` | 21 | A |
| TC-AU-18 | AU-5a | `passwd Pass1234 NewPass99` → `logout` → `login` зі старим → з новим | Старий — `E209`, новий — успіх | 21 | A |
| TC-AU-19 | AU-5a | Після `passwd`: `reboot` → login новим | Новий працює, старий ні | 21 | A |
| TC-AU-20 | AU-5b | `passwd wrong X123456` | `E215` | 21 | A |
| TC-AU-21 | AU-5b | Новий пароль довжиною 5, 6, 32, 33 | 5, 33 → `E205` | 21 | A |
| TC-AU-22 | AU-6a | `sudo wrong`; повторно після успіху | `E213`; `W212` | 21 | A |

## 4. OTA (OTA)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-OTA-01 | OTA-1 | `version` + boot log + `ota` | Версія однакова в усіх трьох місцях; `partition: ota_N @ <addr>, state: valid` | 21 | A |
| TC-OTA-02 | OTA-2 | `ota`, `ota status` | Поточна і попередня прошивка/розділ | 21 | A |
| TC-OTA-03 | OTA-3 | `ota check` на 2.1.0 / 2.3.0 | Current, stable, beta; `update available` / `up to date (stable)` / `running newer than stable` | 21 | A |
| TC-OTA-04 | OTA-4a,OTA-6,OTA-7 | `ota update beta` на 2.1.0 | `current → target`, `downloading`, `image`, прогрес по 10 %, `success`, reboot, `PENDING_VERIFY` → `marked VALID`, `version` = 2.3.0 | 21 | A |
| TC-OTA-05 | OTA-4a | `ota update` (stable) з 2.3.0 | Поведінка за PRD: stable = 2.1.0 → даунгрейд заблоковано (`E408`) або `running newer than stable` — зафіксувати фактичне | 21 | A |
| TC-OTA-06 | OTA-4b | `ota update beta` на 2.3.0; `ota update` на 2.1.0 | `[OTA] already up to date`, без завантаження і reboot | 21 | A |
| TC-OTA-07 | OTA-5a | `ota install 2.1`, `2.1.0.0`, `a.b.c`, `2.1.x`, `-1.0.0`, `` | `E414` | 21 | A |
| TC-OTA-08 | OTA-5a | `ota install 9.9.9`, `ota install 2.2.0` | `E415` | 21 | A |
| TC-OTA-09 | OTA-5b | На 2.3.0 `ota install 2.1.0` без force | `E408 downgrade blocked: v2.3.0 -> v2.1.0. Use 'ota install 2.1.0 force'`; прошивка не змінилась | 23 | A |
| TC-OTA-10 | OTA-5c | `ota install 2.1.0 force` | Даунгрейд виконано | 23 | A |
| TC-OTA-11 | OTA-5c | `ota install 2.3.0 force` на 2.3.0 | Перевстановлення з `W409` | 23 | A |
| TC-OTA-12 | OTA-8a | `ota broken` | Після reboot `self-check FAILED ... Rolling back...`, повернення на попередню версію, `version` = попередня, state valid | 21 | A |
| TC-OTA-13 | OTA-8b | `ota rollback` без іншого розділу / після broken | `E416` / `E417` / успішний rollback — залежно від стану | 21 | A |
| TC-OTA-14 | OTA-8b | `ota rollback` коли попередня валідна | Завантаження прошивки з іншого розділу | 21 | A |
| TC-OTA-15 | OTA-9 | `--drop-at 50`; `ota update` | `E410`, пристрій на поточній версії, працює | 21 | A+M |
| TC-OTA-16 | OTA-9 | `--slow 20`; під час завантаження керовано вимкнути AP `SENTRY-HIL` | Auto: AP fault/recovery; manual/partial: slow OTA orchestration до додавання server fixture; `W110` + `E410/E411` або інша контрольована помилка | 21 | A+M |
| TC-OTA-17 | OTA-9,OTA-11 | `ota url .../test/garbage.bin` | `E406` | 21 | A |
| TC-OTA-18 | OTA-9,OTA-11 | `ota url .../test/truncated.bin` | Контрольована помилка (E406/E410/E412), пристрій на поточній версії | 21 | A |
| TC-OTA-19 | OTA-9,OTA-11 | `ota url .../test/corrupted.bin` | `E412` | 21 | A |
| TC-OTA-20 | OTA-9 | `ota url` іншого проєкту (ESP-прошивка не SENTRY, якщо є) | `E407` | 21 | A |
| TC-OTA-21 | OTA-9 | Після кожної помилки (TC-15…20): `version`, `status`, потім успішний `ota check` / `ota update` | Пристрій працює, наступна OTA проходить одразу | 21 | A |
| TC-OTA-22 | OTA-9 | Запустити `ota update`, одразу ще раз `ota update` | `E401` | 21 | A |
| TC-OTA-23 | OTA-9 | Сервер недоступний (`ota server http://192.0.2.1:8000/fw7/`) → `ota check` | `E402` | 21 | A |
| TC-OTA-24 | OTA-9 | `--beta 9.9.9` → `ota check` / `ota update beta` | `E403` або `E415` | 21 | A |
| TC-OTA-25 | OTA-9,AC-1b | Managed AP down → `ota check` (а); AP up, upstream/WAN down → `ota check` (б) | Auto (а): `E002 Wi-Fi required`; partial (б): фактичний `E402/E411` фіксується до уточнення контракту | 21 | A+M |
| TC-OTA-26 | OTA-9 | Старт завантаження не вдається (недоступний шлях) | `E405` | 21 | A |
| TC-OTA-27 | OTA-10 | **Збереження після OTA.** Перед `ota update beta` виставити: Wi-Fi мережа, профіль+новий пароль, лампа (колір/яскравість/режим), сцена 1–3, `relay` cycles, relay auto, `distance calibrate/alarm/filter off`, `health interval 77`, (Guard PIN/зона — після 2.3.0). Виконати OTA 2.1.0→2.3.0 | Усі значення збережені; для кожної групи — окремий assert | 21 | A |
| TC-OTA-28 | OTA-10 | Те саме при даунгрейді з force (2.3.0→2.1.0) і rollback (broken) | Значення збережені; Guard PIN/зона після повернення на 2.1.0 → знову 2.3.0 | 23 | A |
| TC-OTA-29 | OTA-11 | `ota url ftp://x`, `file:///x`, `x`, `` | `E418` | 21 | A |
| TC-OTA-30 | OTA-11 | `ota url <валідний http-образ> force` | Встановлення | 21 | A |
| TC-OTA-31 | OTA-12 | `ota server` (показати), `ota server http://<IP>:8000/fw7/`, `reboot` | Boot log `custom update server: ...`; після `ota server default` — GitHub | 21 | A |
| TC-OTA-32 | OTA-1 | Після кожного OTA: версія у `version`, boot log, `ota` однакова | Збігається | 21 | A |

## 5. Лампа (LM)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-LM-01 | LM-1 | `lamp on`, `off`, `toggle` ×2 | Лампа змінює стан (очима), `lamp status` збігається | 21 | A+M |
| TC-LM-02 | LM-1 | `lamp on` двічі; `lamp off` двічі | `W510` | 21 | A |
| TC-LM-03 | LM-1 | Лампа on → `reboot` / `logout` | Вимкнена | 21 | A+M |
| TC-LM-04 | LM-2a | Усі 8 кольорів за назвою | Фактичний колір LED збігається з назвою (очима) | 21 | A+M |
| TC-LM-05 | LM-2b | **Межі RGB** для кожного каналу: -1, 0, 255, 256 | -1, 256 → `E502` | 21 | A |
| TC-LM-06 | LM-2b | `lamp color 0 0 0`, `255 255 255`, `1 2` (2 значення), `1 2 3 4` | 0 0 0 і 255 255 255 приймаються; неповні/зайві аргументи — помилка | 21 | A |
| TC-LM-07 | LM-2c | `lamp color orange2`, `RED`, `pink` | `E503` (перевірити регістр) | 21 | A |
| TC-LM-08 | LM-3 | **Межі яскравості**: -1, 0, 1, 99, 100, 101 | -1, 101 → `E504`; 0 — LED не світить, 100 — максимум | 21 | A+M |
| TC-LM-09 | LM-3 | `lamp brightness abc`, `1.5`, порожнє | Помилка, без зміни стану | 21 | A |
| TC-LM-10 | LM-4 | Усі 4 режими; `lamp mode disco` | solid/blink/breathe/rainbow очима; невідомий → `E505` | 21 | A+M |
| TC-LM-11 | LM-4 | Яскравість 20 і 100 у кожному режимі | Яскравість діє в усіх режимах | 21 | M |
| TC-LM-12 | LM-5a | **Межі таймера**: 0, 1, 3600, 3601 | 3601 → `E506`; 1 → вимкнення через 1 с; `[BEACON] auto-off in N s` | 21 | A |
| TC-LM-13 | LM-5b | `lamp timer 60`; `lamp status` через 10 с | `timer ~50 s left`; в **секундах** | 21 | A |
| TC-LM-14 | LM-5b | `lamp timer 0` після запуску | Скасовано | 21 | A |
| TC-LM-15 | LM-5b | `lamp timer 10` при вимкненій лампі | `E507` | 21 | A |
| TC-LM-16 | LM-5b | Дочекатися закінчення таймера | Лампа вимкнулась ~через N с (виміряти реальний час) | 21 | A+M |
| TC-LM-17 | LM-6 | `scene save 1` → змінити → `scene load 1` | Відновлено колір+яскравість+режим | 21 | A |
| TC-LM-18 | LM-6 | `scene save/load` номери 0, 1, 2, 3, 4 | 0, 4 → `E508` | 21 | A |
| TC-LM-19 | LM-6 | `scene load` порожньої сцени | `E509` | 21 | A |
| TC-LM-20 | LM-7 | `lamp status` формат | `ON\|off, color (r,g,b), brightness N%, mode <m>, timer ...` | 21 | A |
| TC-LM-21 | LM-7 | Виставити колір/яскравість/режим/сцену → `reboot` → `lamp status`, `scene load` | Збережено в NVS (лампа вимкнена, налаштування ті самі) | 21 | A |
| TC-LM-22 | LM-8 | Пріоритет LED: лампа off → LED показує стан системи; лампа on → лампа; EMERGENCY / OTA / помилка датчика над лампою | Відповідно до пріоритету | 21 | M |

## 6. Реле (RL)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-RL-01 | RL-1a | `relay on`, `off`, `toggle` ×2 | Реле клацає, діод світить при ON (очима); `[VALVE]` OPEN/closed | 21 | A+M |
| TC-RL-02 | RL-1a | Повторне `on` / `off` | `W601` | 21 | A |
| TC-RL-03 | RL-1b | Швидко 3 перемикання за <1 с | Третє → `E602` | 21 | A |
| TC-RL-04 | RL-1b | 2 перемикання за 1 с | Обидва проходять | 21 | A |
| TC-RL-05 | RL-2 | `relay status`; 4 перемикання on/off/on/off | `cycles N` збільшилось на 4 (+1 за кожне on і off) | 21 | A |
| TC-RL-06 | RL-2 | `cycles` після `reboot` | Значення збережено | 21 | A |
| TC-RL-07 | RL-3 | **Межі pulse**: 99, 100, 10000, 10001 | 99, 10001 → `E603 pulse must be 100-10000 ms` | 21 | A |
| TC-RL-08 | RL-3 | `pulse 1000`: виміряти тривалість (очима/логічним аналізатором) | ≈1 с, потім реле OFF | 21 | A+M |
| TC-RL-09 | RL-3 | `relay on` → `relay pulse 500` | `E604` | 21 | A |
| TC-RL-10 | RL-3 | `pulse abc`, `pulse 0`, `pulse -1` | Помилка | 21 | A |
| TC-RL-11 | RL-4 | **Межі schedule**: on/off = 1, 2, 3600, 3601 (кожен параметр окремо) | 1, 3601 → `E606` | 21 | A |
| TC-RL-12 | RL-4 | `schedule 3 3`; спостерігати ≥2 цикли; `schedule off`; `schedule off` повторно | Цикл ON 3 с / OFF 3 с; `W605` на повторне | 21 | A+M |
| TC-RL-13 | RL-5 | `relay auto on` + `distance alarm 30`; піднести об'єкт <30 см | Реле вмикається при перетині порога | 21 | A+M |
| TC-RL-14 | RL-6 | `relay health` | Знос контактів (з 100000), стан котушки | 21 | A |
| TC-RL-15 | RL-7 | `relay on`, `pulse`, `schedule` → `logout` | Реле OFF, імпульс/розклад зупинені (очима) | 21 | A+M |

## 7. Сонар (DS)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-DS-01 | DS-1 | `distance` | Одне значення, см | 21 | A |
| TC-DS-02 | DS-1 | **Межі N**: 0, 1, 20, 21 | 0, 21 → `E704`; 20 включно приймається; N вимірів + середнє | 21 | A |
| TC-DS-03 | DS-1 | `distance abc`, `-1`, `1.5` | Помилка | 21 | A |
| TC-DS-04 | DS-2a | **Межі log**: 99, 100, 5000, 5001 | 99, 5001 → `E705` | 21 | A |
| TC-DS-05 | DS-2a | `distance log 500`; ~3 с; `distance stop`; `distance stop` повторно | Виміри з ≈500 мс; `W710` | 21 | A |
| TC-DS-06 | DS-2b | Під час log: `distance`, `distance 5`, `distance stats` | `E711` | 21 | A |
| TC-DS-07 | DS-3 | **Межі calibrate**: 4, 5, 300, 301 | 4, 301 → помилка (`E706`/`E707`) | 21 | A |
| TC-DS-08 | DS-3 | Об'єкт на відомих 20 см → `distance calibrate 20` → `distance` | Зсув враховано; `distance reset` (окрема команда, не `calibrate reset`) повертає | 21 | A+M |
| TC-DS-09 | DS-4 | **Межі alarm**: 4, 5, 300, 301, `off` | 4, 301 → `E708` | 21 | A |
| TC-DS-10 | DS-4 | `alarm 30`; піднести об'єкт <30 см, потім віддалити | `PROXIMITY ALARM: contact at X cm`; `cleared` після віддалення >35 см (гістерезис 5 см) | 21 | A+M |
| TC-DS-11 | DS-5a | `filter off` → `distance`; `filter on` → `distance` | Значення стабільніші з фільтром (медіана 5) | 21 | A |
| TC-DS-12 | DS-5b | 6 вимірів → `distance stats` | count, errors, min/max/avg коректні | 21 | A |
| TC-DS-13 | DS-5b | 12 вимірів → `distance history` | Рівно 10 останніх | 21 | A |
| TC-DS-14 | DS-6a | Піднести об'єкт <20 см; тримати; віддалити >25 см; знову <20 | `[COLLISION]` один раз на наближення; повторно лише після >25 см | 21 | M |
| TC-DS-15 | DS-6b | Напрямити сонар у відкритий простір, де в ефективній дальності немає нічого (луна не повертається) | `E701` (перевірено: у кімнаті це відстань понад ~40 см) | 21 | A+M |
| TC-DS-16 | DS-6b | Прикрити/заблокувати датчик рукою впритул (обчислена відстань нижче 2 см) | `E702`, LED червоний ~2 с | 21 | A+M |
| TC-DS-17 | DS-7 | `relay on` + `distance log 200`; відстань 40 / 20 / 9 см | Діод блимає частіше при ближчій відстані; <10 см світить постійно | 21 | M |

## 8. Health (HL)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-HL-01 | HL-1a | Login; виміряти інтервал між `[TELEMETRY #N]` | ≈30 с (±1) | 21 | A |
| TC-HL-02 | HL-1a | `state 3` → виміряти інтервал | ≈10 с | 21 | A |
| TC-HL-03 | HL-1a | `state 4` → виміряти інтервал | ≈5 с | 21 | A |
| TC-HL-04 | HL-1b | Формат рядка | Відповідає regexp PRD (up, heap, rssi, temp, depth, hull, batt, valve, sonar, state) | 21 | A |
| TC-HL-05 | HL-1c | Формат рядка на 2.3.0 | Є `watch <стан> alerts <N>`; у 2.1.0 — немає | 23 | A |
| TC-HL-06 | HL-2 | Умови попереджень: слабкий сигнал, перегрів тощо | Відповідний `[WARN ...]` | 21 | A |
| TC-HL-07 | HL-3a | `health`, `health now` | Налаштування; миттєвий звіт | 21 | A |
| TC-HL-08 | HL-3b | `health off` → пауза > 30 с → `health on`; повторні on/off | Автозвіти зупиняються/відновлюються; `W901` | 21 | A |
| TC-HL-09 | HL-3c | **Межі interval**: 9, 10, 300, 301 | 9, 301 → `E902`; 10 і 300 **приймаються** | 21 | A |
| TC-HL-10 | HL-3c | `health interval 15` → `reboot` → `health` | Збережено в NVS | 21 | A |
| TC-HL-11 | HL-3c | `health interval abc`, `-1`, `10.5` | Помилка | 21 | A |

## 9. Guard (GD) — 2.3.0

У 2.1.0 усі `guard ...` / `watch ...` → `E099 ... planned in v2.3.0` (TC-GD-00).

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-GD-00 | GD-1 | `guard arm`, `watch status`, `alert list`, K4 | `E099 ... planned in v2.3.0` | 21 | A |
| TC-GD-01 | GD-1 | `guard`, `guard status` до arm | Стан DISARMED, зона 50, остання відстань | 23 | A |
| TC-GD-02 | GD-1 | `guard arm` | `arming in N s` (≈10 с), потім `ARMED` | 23 | A |
| TC-GD-03 | GD-2a | ARMED; піднести об'єкт <50 см | `INTRUSION`; 15 с на PIN | 23 | A+M |
| TC-GD-04 | GD-2a | INTRUSION; нічого не робити 15 с | Перехід в `ALARM` | 23 | A+M |
| TC-GD-05 | GD-2b | **Межі zone**: 9, 10, 200, 201 | 9, 201 → `E808`; нова зона діє | 23 | A |
| TC-GD-06 | GD-3 | `guard panic` | ALARM: alert CRITICAL, реле ON, LED червоний/синій, нагадування кожні 10 с | 23 | A+M |
| TC-GD-07 | GD-3 | Утримати K4 1.5 с | UART: PANIC → ALARM; manual: підтвердити фізичний Guard/LED стан | 23 | A+M |
| TC-GD-08 | GD-3 | 3 неправильні PIN | `E803 Attempts: 1/3`, `2/3`, на 3-й — ALARM | 23 | A |
| TC-GD-09 | GD-3 | 3 виміри без ехо (закрити датчик) | ALARM (tamper) | 23 | A+M |
| TC-GD-10 | GD-4a | ALARM → `guard disarm 1234` | ALARM зупинено, зняття з охорони | 23 | A |
| TC-GD-11 | GD-4b | `arm` → 2 помилкові PIN → правильний PIN → `arm` → 2 помилкові PIN | Лічильник **з нуля** після правильного PIN і при кожному `arm`: ALARM не повинен виникнути на 1-й помилці другої серії | 23 | A |
| TC-GD-12 | GD-4b | `arm` → 2 помилкові → `disarm 1234` → знову `arm` → 1 помилковий | `Attempts: 1/3` (не 3/3) | 23 | A |
| TC-GD-13 | GD-5a | `guard pin 1234 4321`, потім disarm новим | Новий працює, старий ні | 23 | A |
| TC-GD-14 | GD-5a | PIN з 3, 4, 5 цифр; літери; порожній | 3/5/літери → `E804` | 23 | A |
| TC-GD-15 | GD-5a | `guard pin` у ARMED | `E807` | 23 | A |
| TC-GD-16 | GD-5b | Після кількох подій `guard log` | Останні 10 подій | 23 | A |
| TC-GD-17 | GD-5c | ARMED → `logout` | Охорону не знято; `guard status` показує ARMED | 23 | A |
| TC-GD-18 | RL-7 | ALARM → `logout` | Реле лишається ON (виняток RL-7) | 23 | A+M |
| TC-GD-19 | OTA-10 | PIN 4321 + зона 100 → OTA → `guard status` | PIN і зона збережені | 23 | A |
| TC-GD-20 | GD-1 | `guard arm` коли вже в `arming` | `W801 guard already arming`, відлік не перезапускається | 23 | A |
| TC-GD-21 | GD-4a | `guard disarm <pin>` коли на охороні немає (`disarmed`) | `W802 guard is not armed` | 23 | A |
| TC-GD-22 | GD-4a | `guard disarm <pin>` під час відліку `arming` (до переходу в ARMED) | Скасовує постановку, `disarmed (was arming)` | 23 | A |

## 10. Alert center (AL) — 2.3.0

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-AL-01 | AL-1 | `alert test info` / `warning` / `critical` | `[CIC #id LEVEL] test: ...` | 23 | A |
| TC-AL-02 | AL-1 | Створити 21+ alerts; `alert list` | Лише останні 20 | 23 | A |
| TC-AL-03 | AL-2 | `alert`, `alert list` | `*` біля непідтверджених | 23 | A |
| TC-AL-04 | AL-3a | Створити 3 alert; `alert ack` | Підтверджено **останній** непідтверджений | 23 | A |
| TC-AL-05 | AL-3b | Створити alert #1, #2, #3; `alert ack 1` | Підтверджено **саме #1**, інші лишаються `*` | 23 | A |
| TC-AL-06 | AL-3b | `alert ack 999`; `alert ack 1` двічі | `E851`; `W852` | 23 | A |
| TC-AL-07 | AL-3c | `alert ack all`; повторно | Усі підтверджені; `W853` | 23 | A |
| TC-AL-08 | AL-4a | Є непідтверджений → `alert clear` | `E855` | 23 | A |
| TC-AL-09 | AL-4a | Усі підтверджені → `alert clear` | Список порожній | 23 | A |
| TC-AL-10 | AL-4b | `alert test foo`, `alert test` | `E854` | 23 | A |
| TC-AL-11 | AL-5 | У NORMAL: `alert test critical` | Auto: Alert/state/relay логіка; manual: фізичне клацання реле та LED | 23 | A+M |
| TC-AL-12 | AL-5 | У DEBUG: `alert test critical` | Реле ON, стан → VERBOSE | 23 | A |
| TC-AL-13 | AL-5 | У EMERGENCY: `alert test critical` | Не змінює стан EMERGENCY (виняток) | 23 | A |
| TC-AL-14 | ST-3a | У EMERGENCY: `alert list` | Працює | 23 | A |

## 11. Кнопки (BTN)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-BTN-01 | BTN-1 | K1 press ×2; K1 hold 1.5 с ×3 | Auto: UART lamp events/колір; manual: фактичний RGB LED | 21 | A+M |
| TC-BTN-02 | BTN-2 | K2 press ×2; K2 hold 1.5 с | Auto: UART valve/pulse; manual: фізичне реле та діод | 21 | A+M |
| TC-BTN-03 | BTN-3 | K3 press; чекати; ще K3 | Auto: start/stop та UART timing; manual: відстань/collision без sonar stimulator | 21 | A+M |
| TC-BTN-04 | BTN-4 | K4 press (alert є / нема); K4 hold 1.5 с | Auto: 2.1.0 `E099`, 2.3.0 ack; manual/partial: PANIC потребує Guard/sonar setup | 21 | A+M |
| TC-BTN-05 | BTN-5 | K1+K2, K2+K3, K3+K4, K4+K1 утримати 2 с | Автоматично: стани 1, 2, 3, 4(з 3) | 21 | A |
| TC-BTN-06 | BTN-5 | K4+K1 з 1, 2 | Автоматично: `E302`, state не змінюється | 21 | A |
| TC-BTN-07 | BTN-6 | Без login натиснути K1–K4 | Автоматично: `E003` для кожної кнопки | 21 | A |
| TC-BTN-08 | BTN-1 | Короткі натискання (<1.5 с) vs утримання; дребезг (швидкі 5 натискань) | Auto: timing/classification; manual: справжній electrical bounce ще не імітується | 21 | A+M |
| TC-BTN-09 | ST-3e | Кнопки в EMERGENCY | Автоматично для 2.1.0: `E005 buttons blocked in EMERGENCY` | 21 | A |

## 12. Система і NFR

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-SYS-01 | SYS-1 | `help` | Група за групами з позначками `[wifi]`/`[login]`/`[debug]` | 21 | A |
| TC-SYS-02 | SYS-2 | `status` до і після login/connect/OTA | Усі поля; guard — лише 2.3.0 | 21 | A |
| TC-SYS-03 | SYS-3 | `sysinfo`, `temp`, `uptime` | Чип, flash, пам'ять; температура; uptime збільшується | 21 | A |
| TC-SYS-04 | SYS-4 | `reboot` | Відлік 3-2-1, перезавантаження | 21 | A |
| TC-SYS-05 | SYS-5 | Boot log після: power on, `reboot`, OTA | `last reset: power on` / `software reboot` | 21 | A |
| TC-NFR-01 | NFR-1 | Повторний прогін усіх `21` кейсів на 2.3.0 | Нічого не гірше, ніж у 2.1.0 | 23 | A |
| TC-NFR-02 | NFR-3 | Помилки всіх TC мають формат `E<код>`/`W<код>` | Так | 21 | A |
| TC-NFR-03 | NFR-4 | Fuzz: довгі рядки (1k/10k), керуючі символи, `\x00`, ANSI, швидкий потік команд | Без reboot і зависання (`last reset` = power on / software) | 21 | A |
| TC-NFR-04 | NFR-5 | Аліаси: `sonar`=`distance`, `beacon`=`lamp`, `valve open\|close`=`relay on\|off`, `telemetry`=`health`, `watch`=`guard`, `cic`=`alert` | Працюють ідентично | 21 | A |

## 13. Дослідницьке тестування (RES)

| TC | Req | Назва і кроки | Очікуваний результат | Ver | Тип |
|---|---|---|---|---|---|
| TC-RES-01 | RES-1 | Пошук прихованих команд: `strings` по бінарнику, перебір кандидатів у консолі | Список знайдених команд і їхній доступ | 21 | M |
| TC-RES-02 | RES-2 | Аналіз boot log і бінарника на секрети (токени, паролі, base64) | Знахідки з оцінкою ризику | 21 | M |
| TC-RES-03 | RES-3 | Захист `sudo`/debug від перебору (лічильник спроб, затримки) | Описати | 21 | A |
| TC-RES-04 | RES-4 | Чи пишуться паролі у лог відкритим текстом | Описати | 21 | M |
| TC-RES-05 | AC-1d | Доступ до `[debug]` команд без sudo / після sudo / після logout | `E004` / дозволено / `E004` | 21 | A |

---

## Підсумок

- Кейсів: 219 кейсів (з урахуванням параметризації BVA — понад 400 перевірок).
- Автоматизуються: коди помилок, межі, формати, NVS, OTA-послідовності.
- Ручні: фізична поведінка (LED, діод, реле, кнопки, HC-SR04), Wi-Fi-обриви, `--slow`.
