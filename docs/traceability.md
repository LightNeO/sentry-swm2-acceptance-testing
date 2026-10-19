# Матриця трасабіліті SENTRY SWM-2

> Файл генерується: `python framework/tools/gen_traceability.py`. Не редагувати вручну.
> Джерела: `requirements.md`, `test_cases.md`, `results.json`.

## Зведення покриття

- Вимог: **139**; з тест-кейсами: **139**; без кейсів: **0**
- Тест-кейсів: **220**; «осиротілих» посилань на неіснуючі вимоги: **0**
- Виконано кейсів (є результат): **171** з 220

## Матриця

| Req | Ver | P | Тип | Тест-кейси | 2.1.0 | 2.3.0 | Баги |
|---|---|---|---|---|---|---|---|
| AC-1a | 21 | P2 | A | TC-AC-01 | PASS | PASS | — |
| AC-1b | 21 | P1 | A | TC-AC-02, TC-OTA-25 | PARTIAL | PARTIAL | — |
| AC-1c | 21 | P1 | A | TC-AC-03, TC-AC-04 | PASS | PASS | — |
| AC-1d | 21 | P1 | A | TC-AC-05, TC-RES-05 | PARTIAL | — | — |
| AC-2a | 21 | P2 | A | TC-AC-06, TC-AC-09 | PASS | PASS | — |
| AC-2b | 21 | P3 | A | TC-AC-07 | PASS | PASS | — |
| AC-2c | 21 | P3 | A | TC-AC-08 | PASS | PASS | — |
| ST-1a | 21 | P2 | A | TC-ST-01 | PASS | PASS | — |
| ST-1b | 21 | P1 | A | TC-ST-01, TC-ST-02 | PASS | PASS | — |
| ST-1c | 21 | P2 | A+M | TC-ST-03 | PASS | PASS | — |
| ST-1d | 21 | P2 | A+M | TC-ST-04 | PASS | PASS | — |
| ST-2 | 21 | P1 | A+M | TC-ST-05, TC-ST-06, TC-ST-07 | FAIL | PARTIAL | BUG-004 |
| ST-3a | 21 | P1 | A | TC-ST-08, TC-ST-09, TC-AL-14 | PARTIAL | PARTIAL | — |
| ST-3b | 21 | P2 | A | TC-ST-10 | FAIL | FAIL | BUG-007 |
| ST-3c | 21 | P2 | A | TC-ST-11 | PASS | PASS | — |
| ST-3d | 21 | P1 | A | TC-ST-12 | PASS | PASS | — |
| ST-3e | 21 | P2 | A | TC-ST-13, TC-BTN-09 | PASS | — | — |
| ST-4a | 21 | P3 | A | TC-ST-14 | PASS | PASS | — |
| ST-4b | 21 | P2 | A | TC-ST-15 | PASS | PASS | — |
| ST-4c | 21 | P1 | A | TC-ST-16 | PASS | PASS | — |
| WF-1a | 21 | P1 | A+M | TC-WF-01, TC-WF-02 | PARTIAL | PASS | — |
| WF-1b | 21 | P2 | A | TC-WF-03 | — | PASS | — |
| WF-1c | 21 | P2 | A | TC-WF-04 | — | PASS | — |
| WF-1d | 21 | P1 | A | TC-WF-01 | PASS | PASS | — |
| WF-1e | 21 | P1 | A | TC-WF-05 | PASS | PASS | — |
| WF-2 | 21 | P2 | A (частково) | TC-WF-06, TC-WF-07 | — | PASS | — |
| WF-3a | 21 | P2 | A | TC-WF-10, TC-WF-11 | — | PASS | — |
| WF-3b | 21 | P2 | A | TC-WF-12 | — | — | — |
| WF-3c | 21 | P2 | A | TC-WF-13 | — | PASS | — |
| WF-3d | 21 | P2 | A | TC-WF-05 | PASS | PASS | — |
| WF-4a | 21 | P3 | A | TC-WF-14 | — | PASS | — |
| WF-4b | 21 | P3 | A | TC-WF-15 | PASS | PASS | — |
| WF-4c | 21 | P3 | A | TC-WF-16 | — | PASS | — |
| WF-4d | 21 | P3 | A | TC-WF-17 | — | PASS | — |
| WF-5 | 21 | P1 | A | TC-WF-18 | PASS | PASS | — |
| AU-1a | 21 | P1 | A | TC-AU-01, TC-AU-02 | PARTIAL | PARTIAL | — |
| AU-1b | 21 | P1 | A | TC-AU-03, TC-AU-04 | — | PASS | — |
| AU-1c | 21 | P1 | A | TC-AU-05 | — | PASS | — |
| AU-1d | 21 | P2 | A | TC-AU-06 | — | — | — |
| AU-1e | 21 | P1 | A | TC-AU-07 | PASS | — | — |
| AU-2a | 21 | P1 | A | TC-AU-08, TC-AU-14 | PASS | PASS | — |
| AU-2b | 21 | P1 | A | TC-AU-09, TC-AU-10 | PARTIAL | PARTIAL | — |
| AU-2c | 21 | P1 | A | TC-AU-11, TC-AU-12 | PASS | PASS | — |
| AU-2d | 21 | P2 | A | TC-AU-13 | PASS | PASS | — |
| AU-3a | 21 | P1 | A+M | TC-AU-15 | PASS | PASS | — |
| AU-3b | 21 | P3 | A | TC-AU-16 | PASS | PASS | — |
| AU-4 | 21 | P2 | A | TC-AU-17 | PASS | PASS | — |
| AU-5a | 21 | P1 | A | TC-AU-18, TC-AU-19 | FAIL | PASS | BUG-006 |
| AU-5b | 21 | P1 | A | TC-AU-20, TC-AU-21 | PASS | PASS | — |
| AU-6a | 21 | P1 | A | TC-AU-22 | PASS | PASS | — |
| OTA-1 | 21 | P2 | A | TC-OTA-01, TC-OTA-32 | PASS | PASS | — |
| OTA-2 | 21 | P2 | A | TC-OTA-02 | — | — | — |
| OTA-3 | 21 | P2 | A | TC-OTA-03 | — | — | — |
| OTA-4a | 21 | P1 | A | TC-OTA-04, TC-OTA-05 | PARTIAL | PARTIAL | — |
| OTA-4b | 21 | P2 | A | TC-OTA-06 | PASS | PASS | — |
| OTA-5a | 21 | P2 | A | TC-OTA-07, TC-OTA-08 | PASS | PASS | — |
| OTA-5b | 21 | P1 | A | TC-OTA-09 | — | PASS | — |
| OTA-5c | 21 | P2 | A | TC-OTA-10, TC-OTA-11 | — | PARTIAL | — |
| OTA-6 | 21 | P2 | A | TC-OTA-04 | PASS | PASS | — |
| OTA-7 | 21 | P1 | A | TC-OTA-04 | PASS | PASS | — |
| OTA-8a | 21 | P1 | A | TC-OTA-12 | PASS | — | — |
| OTA-8b | 21 | P1 | A | TC-OTA-13, TC-OTA-14 | PARTIAL | — | — |
| OTA-9 | 21 | P1 | A+M | TC-OTA-15, TC-OTA-16, TC-OTA-17, TC-OTA-18, TC-OTA-19, TC-OTA-20, TC-OTA-21, TC-OTA-22, TC-OTA-23, TC-OTA-24, TC-OTA-25, TC-OTA-26 | PARTIAL | PARTIAL | — |
| OTA-10 | 21 | P1 | A | TC-OTA-27, TC-OTA-28, TC-GD-19 | PARTIAL | PARTIAL | — |
| OTA-11 | 21 | P2 | A | TC-OTA-17, TC-OTA-18, TC-OTA-19, TC-OTA-29, TC-OTA-30 | PARTIAL | PARTIAL | — |
| OTA-12 | 21 | P2 | A | TC-OTA-31 | PASS | PARTIAL | — |
| LM-1 | 21 | P2 | A+M | TC-LM-01, TC-LM-02, TC-LM-03 | PASS | PARTIAL | — |
| LM-2a | 21 | P2 | A+M | TC-LM-04 | PASS | PASS | — |
| LM-2b | 21 | P1 | A+M | TC-LM-05, TC-LM-06 | PARTIAL | PARTIAL | — |
| LM-2c | 21 | P3 | A | TC-LM-07 | — | — | — |
| LM-3 | 21 | P1 | A+M | TC-LM-08, TC-LM-09 | PARTIAL | PARTIAL | — |
| LM-4 | 21 | P2 | A+M | TC-LM-10, TC-LM-11 | PASS | — | — |
| LM-5a | 21 | P1 | A | TC-LM-12 | PASS | PASS | — |
| LM-5b | 21 | P2 | A | TC-LM-13, TC-LM-14, TC-LM-15, TC-LM-16 | FAIL | PARTIAL | — |
| LM-6 | 21 | P2 | A | TC-LM-17, TC-LM-18, TC-LM-19 | PASS | PASS | — |
| LM-7 | 21 | P1 | A | TC-LM-20, TC-LM-21 | PARTIAL | PARTIAL | — |
| LM-8 | 21/23 | P2 | M | TC-LM-22 | PASS | — | — |
| RL-1a | 21 | P1 | A+M | TC-RL-01, TC-RL-02 | PASS | PASS | — |
| RL-1b | 21 | P2 | A | TC-RL-03, TC-RL-04 | — | — | — |
| RL-2 | 21 | P1 | A | TC-RL-05, TC-RL-06 | FAIL | PASS | BUG-005 |
| RL-3 | 21 | P1 | A+M | TC-RL-07, TC-RL-08, TC-RL-09, TC-RL-10 | FAIL | FAIL | BUG-003 |
| RL-4 | 21 | P2 | A | TC-RL-11, TC-RL-12 | PASS | PASS | — |
| RL-5 | 21 | P2 | A+M | TC-RL-13 | PASS | PASS | — |
| RL-6 | 21 | P3 | A | TC-RL-14 | PASS | PASS | — |
| RL-7 | 21 | P1 | A | TC-RL-15, TC-GD-18 | PARTIAL | PASS | — |
| DS-1 | 21 | P1 | A | TC-DS-01, TC-DS-02, TC-DS-03 | FAIL | FAIL | BUG-002 |
| DS-2a | 21 | P2 | A | TC-DS-04, TC-DS-05 | PARTIAL | PARTIAL | — |
| DS-2b | 21 | P2 | A | TC-DS-06 | — | — | — |
| DS-3 | 21 | P2 | A+M | TC-DS-07, TC-DS-08 | PASS | PARTIAL | — |
| DS-4 | 21 | P1 | A+M | TC-DS-09, TC-DS-10 | PASS | PASS | — |
| DS-5a | 21 | P3 | A | TC-DS-11 | — | — | — |
| DS-5b | 21 | P2 | A | TC-DS-12, TC-DS-13 | PASS | PASS | — |
| DS-6a | 21 | P1 | M | TC-DS-14 | PASS | PASS | — |
| DS-6b | 21 | P2 | A+M | TC-DS-15, TC-DS-16 | PASS | — | — |
| DS-7 | 21 | P2 | M | TC-DS-17 | PASS | PASS | — |
| HL-1a | 21 | P1 | A | TC-HL-01, TC-HL-02, TC-HL-03 | PASS | PASS | — |
| HL-1b | 21 | P2 | A | TC-HL-04 | — | — | — |
| HL-1c | 23 | P2 | A | TC-HL-05 | — | — | — |
| HL-2 | 21 | P3 | A (частково) | TC-HL-06 | — | — | — |
| HL-3a | 21 | P2 | A | TC-HL-07 | — | — | — |
| HL-3b | 21 | P3 | A | TC-HL-08 | — | — | — |
| HL-3c | 21 | P1 | A | TC-HL-09, TC-HL-10, TC-HL-11 | FAIL | PARTIAL | BUG-001 |
| GD-1 | 23 | P1 | A+M | TC-GD-00, TC-GD-01, TC-GD-02, TC-GD-20 | — | PARTIAL | — |
| GD-2a | 23 | P1 | A+M | TC-GD-03, TC-GD-04 | — | PASS | — |
| GD-2b | 23 | P2 | A | TC-GD-05 | — | PASS | — |
| GD-3 | 23 | P1 | A+M | TC-GD-06, TC-GD-07, TC-GD-08, TC-GD-09 | — | PARTIAL | — |
| GD-4a | 23 | P1 | A | TC-GD-10, TC-GD-21, TC-GD-22 | — | PASS | — |
| GD-4b | 23 | P1 | A | TC-GD-11, TC-GD-12 | — | FAIL | BUG-010 |
| GD-5a | 23 | P1 | A | TC-GD-13, TC-GD-14, TC-GD-15 | — | PASS | — |
| GD-5b | 23 | P3 | A | TC-GD-16 | — | PASS | — |
| GD-5c | 23 | P1 | A | TC-GD-17 | — | PASS | — |
| AL-1 | 23 | P2 | A | TC-AL-01, TC-AL-02 | — | PARTIAL | — |
| AL-2 | 23 | P2 | A | TC-AL-03 | — | PASS | — |
| AL-3a | 23 | P2 | A | TC-AL-04 | — | PASS | — |
| AL-3b | 23 | P1 | A | TC-AL-05, TC-AL-06 | — | FAIL | BUG-008 |
| AL-3c | 23 | P3 | A | TC-AL-07 | — | PASS | — |
| AL-4a | 23 | P2 | A | TC-AL-08, TC-AL-09 | — | PASS | — |
| AL-4b | 23 | P2 | A | TC-AL-10 | — | PASS | — |
| AL-5 | 23 | P1 | A+M | TC-AL-11, TC-AL-12, TC-AL-13 | — | PARTIAL | — |
| BTN-1 | 21 | P2 | A+M | TC-BTN-01, TC-BTN-08 | PASS | PARTIAL | — |
| BTN-2 | 21 | P2 | A+M | TC-BTN-02 | PASS | PASS | — |
| BTN-3 | 21 | P2 | A+M | TC-BTN-03 | PASS | PASS | — |
| BTN-4 | 23 | P2 | A+M | TC-BTN-04 | PASS | PASS | — |
| BTN-5 | 21/23 | P2 | A | TC-BTN-05, TC-BTN-06 | PASS | PASS | — |
| BTN-6 | 21 | P2 | A | TC-BTN-07 | PASS | PASS | — |
| SYS-1 | 21 | P3 | A | TC-SYS-01 | PASS | PASS | — |
| SYS-2 | 21 | P2 | A | TC-SYS-02 | — | — | — |
| SYS-3 | 21 | P3 | A | TC-SYS-03 | — | — | — |
| SYS-4 | 21 | P2 | A | TC-SYS-04 | — | — | — |
| SYS-5 | 21 | P2 | A | TC-SYS-05 | PASS | PASS | — |
| NFR-1 | 23 | P1 | A | TC-NFR-01 | — | — | — |
| NFR-2 | 21 | — | — (виключення зі scope) | **НЕМАЄ** | — | — | — |
| NFR-3 | 21 | P2 | A | TC-NFR-02 | — | — | — |
| NFR-4 | 21 | P1 | A | TC-NFR-03 | PASS | PASS | — |
| NFR-5 | 21/23 | P3 | A | TC-NFR-04 | — | — | — |
| RES-1 | 21 | P1 | M | TC-RES-01 | PASS | — | — |
| RES-2 | 21 | P1 | M | TC-RES-02 | PASS | — | — |
| RES-3 | 21 | P1 | A | TC-RES-03 | FAIL | — | — |
| RES-4 | 21 | P2 | M | TC-RES-04 | — | — | — |
