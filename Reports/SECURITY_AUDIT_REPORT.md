# SECURITY AUDIT REPORT — Норма ОТ: Реестр обучения (ИСПДн)

**Дата:** 22.05.2026
**Версия приложения:** 3.1.0
**Тип аудита:** Полный (код + документация + инфраструктура)
**Методология:** 152-ФЗ, ПП РФ №1119, Приказ ФСТЭК №21, STRIDE, OWASP ASVS (subset), privacy-by-design
**Гриф:** ДСП (для служебного пользования)

---

## Executive Summary

### Общая оценка

| Область | Оценка | Статус |
|---------|--------|--------|
| Архитектура безопасности | Хорошая | ✅ Продуманная defence-in-depth архитектура |
| Реализация криптографии | Хорошая (с замечаниями) | ⚠️ Критические: memory safety, thread safety |
| Аудит и логирование | Средняя | 🔴 Критический: HMAC never verified (security theater) |
| XML безопасность | Отличная | ✅ defusedxml, secure lxml, element/depth limits |
| TLS/Сеть | Хорошая | ✅ verify=True default; WinINET ignores verify=False |
| Работа с ПДн | Средняя | 🔴 SNILS leak в error messages; нет retention |
| Тестирование | Хорошее | ✅ 389 тестов; покрытие crypto, XML, audit |
| Документация | Отличная | ✅ Полный комплект: SECURITY, THREAT_MODEL, DPIA, risk register |

---

## Ключевые Findings

### 🔴 CRITICAL (1)

| ID | Finding | Компонент | Описание |
|----|---------|-----------|----------|
| A-01 | **Audit HMAC не верифицируется** | `utils/audit.py` | HMAC tags пишутся в audit.log, но нигде не проверяются. При модификации/удалении записей это не будет обнаружено. HMAC integrity — security theater без функции верификации. |

### 🟠 HIGH (17)

| ID | Finding | Компонент | Риск |
|----|---------|-----------|------|
| H-01 | 17 из 34 audit-событий не эмитируются | `utils/audit.py` + весь код | KEY_ACCESS, LOGIN, BACKUP, SHUTDOWN, QUERY_SETID и др. не логируются |
| H-02 | Audit HMAC fallback key — hardcoded | `utils/audit.py:62` | `b"EXCEL_XML_AUDIT_V3"` — любой с исходниками может подделать |
| H-03 | Audit HMAC tag — 48 bit (12 hex chars) | `utils/audit.py:74` | Брутфорс 2^48 реалистичен |
| H-04 | Нет hash chaining в audit | `utils/audit.py` | Selective deletion не обнаруживается |
| H-05 | SNILS в error message XLSX импорта | `importers/xlsx_importer.py:52` | Raw SNILS в пользовательском сообщении |
| H-06 | PII в error report XLSX | `importers/error_report.py:67` | ПДн в XLSX отчёте об ошибках |
| H-07 | XML pattern в SensitiveDataFilter не работает | `utils/logger.py:71` | `(?:\s*http)` в конце — большинство XML не маскируется |
| H-08 | URL API эндпоинты в логах (5 мест) | `api/backends/*.py`, `api/mintrud_api.py` | Нарушение AGENTS.md |
| H-09 | TOCTOU в XSD валидации XML | `importers/xml_importer.py:33,53` | Файл читается дважды — race condition |
| H-10 | Мастер-ключ в памяти (global, не зануляется) | `utils/crypto.py:27` | _MASTER_KEY живёт весь процесс |
| H-11 | Encrypt cache — plaintext keys | `utils/crypto.py:31` | 2000 записей plaintext в памяти |
| H-12 | VirtualLock не реализован (docstring врёт) | `utils/crypto.py:8` | Заявлено, не реализовано |
| H-13 | Race condition в rotate_master_key | `utils/crypto.py:595-596` | _MASTER_KEY без лока при ротации |
| H-14 | Race condition в secure_temp | `utils/secure_temp.py:28-29` | Два потока = orphan directory |
| H-15 | Backup PKWARE ZipCrypto (слабое) | `utils/crypto.py:723-726` | Known-plaintext атака |
| H-16 | f-string лог с потенциальными ПДн | `tabs/employee_summary_tab.py:92` | API error без filter_sensitive_text |
| H-17 | Main-thread API call в _query_single | `tabs/employee_summary_tab.py:1264-1314` | Блокировка UI |

### 🟡 MEDIUM (39)

| ID | Finding | Компонент |
|----|---------|-----------|
| M-01 | Нет PRAGMA integrity_check БД при старте | `db/database.py` |
| M-02 | Нет clipboard auto-clear | UI/все tabs |
| M-03 | Нет confirmation dialog для TLS verify=False | `tabs/data_transfer_tab.py` |
| M-04 | Нет retention policy (автоудаление) | `db/`, UI |
| M-05 | Нет secure delete (перезапись) | `db/employees_repo.py` |
| M-06 | `_dpapi_decrypt` — `except Exception: continue` | `utils/crypto.py:181` |
| M-07 | `decrypt_value` возвращает `''` при InvalidToken | `utils/crypto.py:538` |
| M-08 | _CURRENT_PASSPHRASE_KEY не зануляется | `utils/crypto.py:72` |
| M-09 | _CURRENT_PASSPHRASE_KEY не сбрасывается при clear_caches | `utils/crypto.py:566` |
| M-10 | Backup password — фиксированная соль | `utils/crypto.py:706` |
| M-11 | Secure delete — фиктивное затирание на SSD | `utils/secure_temp.py:72-82` |
| M-12 | HMAC с пустым ключом (edge case) | `utils/crypto.py:240` |
| M-13 | Баг: 3-tuple key vs 2-tuple unpack в error_report | `importers/error_report.py:64` |
| M-14 | Concurrent import guard отсутствует | `tabs/data_entry_tab.py` |
| M-15 | Password для XLSX не передаётся (dead code) | `tabs/data_entry_tab.py` |
| M-16 | Не загружены audit события для employee_summary_tab (7) | `tabs/employee_summary_tab.py` |
| M-17 | QUERY_SETID не логируется | `api/mintrud_api.py:query_by_setid()` |
| M-18 | _get_hmac_key() — thread unsafe | `utils/audit.py:56-63` |
| M-19 | ACL SE_DACL_PROTECTED не установлен | `utils/secure_temp.py:44-46` |
| M-20 | atexit не срабатывает на os._exit/crash/kill | `utils/secure_temp.py` |
| M-21 | WinINET backend игнорирует verify=False | `api/backends/wininet_backend.py` |
| M-22 | XSD output validation отсутствует | `exporters/xml_exporter.py` |
| M-23 | Control chars не фильтруются в XML | `exporters/xml_exporter.py:169-176` |
| M-24 | JSON маскировка только строк | `utils/logger.py:99-105` |
| M-25 | %% double escaping в error.log | `utils/logger.py:81` |
| M-26 | Dead code в safe_format_exception | `utils/logger.py:127-129` |
| M-27 | safe_fromstring_xml без CountingTarget | `utils/xml_safe.py:89-105` |
| M-28 | Нет file path validation в xml_importer | `importers/xml_importer.py` |
| M-29 | Name validation inconsistent (manual vs XLSX) | `tabs/data_entry_tab.py` vs `xlsx_importer.py` |
| M-30 | XLSX extension case-sensitive | `importers/xlsx_importer.py:245` |
| M-31 | DatabaseLockError dead code | `db/database.py:108-109` |
| M-32 | No audit events for export operations (EXPORT_XML, EXPORT_XLSX) | `exporters/xml_exporter.py` |
| M-33 | No audit for IMPORT_XLSX / IMPORT_XML | `tabs/data_entry_tab.py` |
| M-34 | master.key backup ZIP без AES-256 | `utils/crypto.py` |
| M-35 | Бэкап с random password — потеря данных | `db/database.py:193-199` |
| M-36 | _secure_delete — rename-before-delete not used | `utils/secure_temp.py` |
| M-37 | No PII warning on XLSX/XML export | UI/tabs |
| M-38 | org_settings.json без HMAC integrity | `utils/crypto.py` (config files) |
| M-39 | No backup integrity check on restore | `db/database.py` |

### 🟢 LOW (12)

| ID | Finding | Компонент |
|----|---------|-----------|
| L-01 | HMAC legacy metadata — низкая энтропия | `utils/crypto.py:233` |
| L-02 | Position (должность) в plaintext | `db/employees_repo.py` |
| L-03 | ПДн в открытом виде в XML-файлах экспорта | `exporters/xml_exporter.py` (design) |
| L-04 | No namespace in XML export | `exporters/xml_exporter.py:96` |
| L-05 | mask_sensitive() — 8/11 SNILS visible | `utils/logger.py:109-115` |
| L-06 | Dead code в validate_api_key_remote | `api/mintrud_api.py:177-187` |
| L-07 | case-sensitive extension check | `importers/xlsx_importer.py:245` |
| L-08 | Per-element text size limit отсутствует | `importers/xml_importer.py:202` |
| L-09 | No log injection protection | `utils/logger.py` |
| L-10 | File path in log output | `importers/xlsx_importer.py:250-251` |
| L-11 | tail_log() — file path disclosure | `utils/logger.py:199,232-233` |
| L-12 | str(data) fallback в safe_fromstring_xml | `utils/xml_safe.py:93` |

---

## 2. Архитектура приложения

### 2.1. Компоненты

```
┌─────────────────────────────────────────────────────┐
│                    GUI (PySide6)                     │
│  data_entry  data_view  data_transfer  exam_journal │
│  employee_summary  protocol  single_worker_protocol │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│                  Core Layer                          │
│  crypto.py  │  audit.py  │  logger.py  │  xml_safe.py│
│  secure_temp.py  │  error_utils.py  │  auto_lock.py │
│  proxy_manager.py  │  cache.py  │  app_paths.py    │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│               Data Layer                             │
│  DB (SQLite)  │  EmployeesRepo  │  EmployeePrograms │
│  ExamJournalRepo  │  WorkersDataRepo                │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│            Import/Export Layer                       │
│  xlsx_importer  │  xml_importer  │  xml_exporter    │
│  protocol_exporter  │  error_report                 │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│                API Layer                             │
│  mintrud_api.py  │  payload_builder.py               │
│  response_parser.py  │  backends/ (Requests/WinINET) │
└─────────────────────────────────────────────────────┘
```

### 2.2. Data Flow (ПДн)

```
Ввод (UI/XLSX/XML) → Валидация → Fernet Encrypt (ФИО, СНИЛС) → SQLite DB
SQLite DB → Fernet Decrypt → XML Export → TLS 1.2+ → API Минтруда
SQLite DB → Fernet Decrypt → UI Display / XLSX Export
SQLite DB → Backup (encrypted fields) → File System
```

### 2.3. Ключевая инфраструктура

```
Windows DPAPI → Master Key (32B) → Fernet
                                  → API Key (Fernet encrypted)
                                  → Proxy Credentials (Fernet encrypted)
                                  → Field Encryption (ФИО, СНИЛС)
Master Key + Passphrase → PBKDF2 (600K) → Wrapped Key
```

---

## 3. Compliance Assessment

### 3.1. 152-ФЗ

| Статья | Требование | Статус |
|--------|------------|--------|
| ст.5 | Законность обработки | ✅ |
| ст.5 | Сроки хранения | ❌ Gap |
| ст.6 | Правовое основание | ✅ Без согласия |
| ст.18.1 | Политика, ответственный | ❌ Орг. меры |
| ст.19 | Технические меры | ⚠️ 70% |
| ст.21 | Удаление ПДн | ❌ Gap |
| ст.22 | Уведомление РКН | ❌ Орг. мера |
| ст.22.1 | Ответственный | ❌ Орг. мера |

### 3.2. ПП РФ №1119 (УЗ-3)

| Всего мер | Реализовано | Частично | Орг. меры |
|-----------|-------------|----------|-----------|
| 11 | 5 (45%) | 3 (27%) | 3 (27%) |

**Уточнение:** 3 меры требуют реализации на уровне ОС (BitLocker, антивирус, AppLocker).
При их реализации — 82% coverage.

### 3.3. Приказ ФСТЭК №21 (23 меры ЗИ)

Реализованы:
- Идентификация и аутентификация
- Управление доступом (частично)
- Регистрация событий
- Криптография
- Контроль целостности (частично)
- Обеспечение восстановления

Не реализованы:
- Ограничение программной среды (ОС)
- Защита носителей (ОС)
- Антивирус (ОС)
- Обнаружение вторжений (не требуется)
- Безопасность ВМ (не применимо)

---

## 4. Тестирование

### 4.1. Покрытие

| Модуль | Тестов | Покрытие |
|--------|--------|----------|
| XML security | 17 | ✅ Отличное (XXE, XEE, size, depth, malformed) |
| Crypto | 12 | ✅ Хорошее (roundtrip, cache, hash, invalid) |
| Logger/Audit | 7 | ⚠️ Среднее (нет теста audit HMAC verification) |
| Network client | 8 | ✅ Хорошее |
| API payloads | Mock | ✅ |
| Response parser | Mock | ✅ |
| Database | - | ⚠️ Частичное |

### 4.2. Отсутствующие тесты

- Audit HMAC verification (нет функции для тестирования)
- Crypto thread safety (race conditions)
- Secure temp SE_DACL_PROTECTED
- SNILS leak regression
- XLSX password handling
- TOCTOU race in XML import
- retention/secure delete
- Backup integrity

---

## 5. Остаточные риски

| ID | Риск | Уровень | Комментарий |
|----|------|---------|-------------|
| R-01 | Компрометация Windows-аккаунта → компрометация всех ПДн | Критический | DPAPI привязан к учётной записи |
| R-02 | Memory dump → мастер-ключ в plaintext | Высокий | _MASTER_KEY в global, не зануляется |
| R-03 | Clipboard → ПДн скопированы | Средний | Нет auto-clear |
| R-04 | Audit log tampering не обнаруживается | Высокий | HMAC не верифицируется |
| R-05 | Backup PKWARE — расшифровка ZIP | Средний | Known-plaintext атака |
| R-06 | Потеря мастер-ключа → потеря всех данных | Высокий | Нет backdoor, требуется backup |
| R-07 | 17 audit-событий не логируются | Высокий | Dead code — отсутствие аудита |
| R-08 | Race condition → повреждение данных | Средний | Thread safety crypto/secure_temp |
| R-09 | TOCTOU → XSD validation bypass | Средний | Двойное чтение XML файла |
| R-10 | SNILS leak → ПДн в отчёте об ошибках | Высокий | xlsx_importer.py:52 |

---

## 6. Рекомендации

### Immediate (1-2 дня)

1. **Добавить HMAC verification audit.log** — создать функцию verify_audit_log()
2. **Исправить SNILS leak** в xlsx_importer.py:52 — маскировать значение
3. **Исправить XML pattern** в logger.py:71 — убрать `(?:\s*http)`
4. **Добавить log_audit для 17 недостающих событий** (QUERY_SETID, KEY_ACCESS, LOGIN и др.)
5. **Добавить PRAGMA integrity_check** при старте БД

### Short-term (1-2 недели)

6. **Добавить clipboard auto-clear** (таймер 30-60 сек)
7. **Добавить confirmation dialog** для TLS verify=False
8. **Увеличить HMAC tag до 64 hex chars**
9. **Добавить hash chaining в audit.log**
10. **Исправить TOCTOU в XML импорте** — переиспользовать распаршенное дерево
11. **Убрать plaintext кэш или переделать на ciphertext → plaintext**

### Medium-term (2-4 недели)

12. **Добавить retention policy** (конфигурируемый срок хранения)
13. **Добавить secure delete** (перезапись перед SQL DELETE)
14. **Перейти на AES-256 для ZIP backup** (pyzipper или Fernet)
15. **Добавить thread safety** для crypto module (KEY_LOCK)
16. **Занулять мастер-ключ** после использования (ctypes.memset)
17. **Убрать hardcoded HMAC key** — логировать ошибку вместо fallback

### Long-term (1-3 месяца)

18. **Добавить ролевую модель** (админ/оператор/наблюдатель) - не требуется
19. **Добавить ограничение попыток passphrase** (3 → lockout)
20. **Добавить XSD validation output** в xml_exporter
21. **Добавить cert pinning** (если API предоставит)
22. **Добавить secure update mechanism** (signature verification)

---

## 7. Организационные меры (НЕ в коде)

| ID | Мера | Ответственный | Срок |
|----|------|---------------|------|
| O-01 | Назначить ответственного за обработку ПДн (ст.22.1) | Руководитель | IMMEDIATE |
| O-02 | Утвердить Политику обработки ПДн (ст.18.1) | Руководитель | IMMEDIATE |
| O-03 | Уведомить Роскомнадзор (форма 4-ПДн, ст.22) | Ответственный | IMMEDIATE |
| O-04 | Включить BitLocker на ПК оператора | Системный администратор | IMMEDIATE |
| O-05 | Установить/проверить антивирус | Системный администратор | IMMEDIATE |
| O-06 | Провести инструктаж операторов | Ответственный | 1 неделя |
| O-07 | Утвердить регламент резервного копирования | Ответственный | 1 неделя |
| O-08 | Утвердить план реагирования на инциденты | Ответственный | 1 неделя |
| O-09 | Ограничить физический доступ к ПК | Руководитель | 1 неделя |
| O-10 | Настроить AppLocker/групповые политики | Системный администратор | 2 недели |
| O-11 | Настроить Windows Defender Firewall с правилами | Системный администратор | 2 недели |
| O-12 | Утвердить перечень ИСПДн | Руководитель | 2 недели |

---

## 8. Production Readiness Assessment

### 8.1. Ready for production?

| Аспект | Статус |
|--------|--------|
| Криптография | ✅ Да (с ограничениями: memory safety) |
| TLS/Сеть | ✅ Да |
| XML безопасность | ✅ Да |
| Аудит | ❌ НЕТ — HMAC не верифицируется (security theater) |
| Логирование | ⚠️ Да (с исправлением XML pattern) |
| Backup | ⚠️ Да (рекомендовано улучшение ZIP) |
| Управление ключами | ✅ Да (с резервным копированием) |
| Организационные меры | ❌ Требуется выполнить O-01..O-12 |

**Критический блокер:** Audit система — пока HMAC не верифицируется, аудит не выполняет свою функцию.

### 8.2. Условия production эксплуатации

1. `EXCEL_XML_PROD=1` (переменная окружения)
2. BitLocker включён на системном диске
3. Антивирус активен и обновлён
4. Учётная запись оператора с надёжным паролем
5. Passphrase установлен (минимум 12 символов)
6. Auto-lock включён (таймаут 5 минут)
7. Оператор обучен работе с ПДн
8. Выполнены организационные меры O-01..O-03

### 8.3. Что остаётся за рамками ПО (организационные меры)

- Назначение ответственного за ПДн
- Политика обработки ПДн
- Уведомление РКН
- Физическая безопасность рабочего места
- Контроль доступа к помещению
- Обучение операторов
- Реагирование на инциденты

---

## 9. Уровень защищённости (УЗ)

### Текущий: УЗ-3 (базовый)

Соответствие: 82% при выполнении организационных мер на уровне ОС.

### Целевой: УЗ-2 (рекомендуемый)

Для перехода на УЗ-2 требуется:
- Реализация технических мер (T-01..T-13)
- Выполнение организационных мер (O-01..O-12)
- Усиление криптографии (memory safety, AES-256 backup)
- Полноценный аудит с верификацией HMAC

---

## 10. Заключение

### Сильные стороны

1. **Архитектура безопасности** — продуманная defence-in-depth: полевое шифрование, DPAPI, PBKDF2, defusedxml, TLS verify=True
2. **Документация** — отличный комплект: SECURITY, THREAT_MODEL, DPIA, hardening, risk register, compliance audit
3. **XML безопасность** — defusedxml + LimitedXMLParser + secure lxml + element/depth limits
4. **Логирование** — SensitiveDataFilter с 27+ паттернами
5. **Тестирование** — 389 тестов, покрытие crypto, XML, audit
6. **Production mode** — `EXCEL_XML_PROD=1` блокирует insecure fallback

### Слабые стороны

1. **Audit система** — HMAC не верифицируется (security theater). 17 из 34 событий не эмитируются. Hardcoded fallback ключ.
2. **Memory safety** — Мастер-ключ в global, не зануляется. Encrypt cache с plaintext ключами. VirtualLock не реализован.
3. **Thread safety** — Race conditions в crypto и secure_temp при многопоточном доступе.
4. **Утечки ПДн** — SNILS в error messages, PII в error report XLSX, URL в логах.
5. **Отсутствуют** — retention policy, secure delete, clipboard auto-clear, cert pinning, update mechanism.

### Итоговая оценка

```
Архитектура:     ██████████ 90% (отличная)
Реализация:      ████████░░ 75% (хорошая, с замечаниями)
Безопасность:    ███████░░░ 70% (хорошая, критические gaps)
Compliance:      ██████░░░░ 60% (средний, требуется орг. меры)
Production:      ████████░░ 75% (почти готов, критический блокер — audit)
```

**Приложение может эксплуатироваться в production при условии:**

1. Исправления критического finding A-01 (HMAC verification)
2. Выполнения организационных мер O-01..O-03
3. Включения BitLocker и антивируса
4. Установки EXCEL_XML_PROD=1

---

## Приложение A: Методология

- **152-ФЗ «О персональных данных»** —Articles 5, 6, 18.1, 19, 21, 22, 22.1
- **ПП РФ №1119** — Требования к защите ПДн при обработке в ИСПДн
- **Приказ ФСТЭК №21** — Состав мер ЗИ (23 меры)
- **Постановление №2464** — Обучение по охране труда
- **OWASP ASVS (subset)** — Secure coding practices
- **STRIDE** — Моделирование угроз
- **Privacy-by-design principles** — 7 принципов

## Приложение B: Файлы аудита

### Созданы/обновлены в ходе аудита

| Файл | Действие | Описание |
|------|----------|----------|
| `SECURITY_AUDIT_REPORT.md` | Создан | Полный отчёт аудита |
| `GAP_ANALYSIS.md` | Создан | Матрица gaps по всем категориям |
| `COMPLIANCE.md` | Создан | Соответствие 152-ФЗ, ПП 1119, ФСТЭК |
| `PRIVACY.md` | Создан | Политика обработки ПДн |
| `DEPLOYMENT.md` | Создан | Руководство по развёртыванию |

### Существующие файлы (проверены, актуальны)

| Файл | Статус | Примечание |
|------|--------|------------|
| `README.md` | ✅ Актуален | Обновить claims: УЗ-3, не УЗ-4 |
| `docs/SECURITY.md` | ✅ Актуален | Исправить VirtualLock claim |
| `docs/HARDENING.md` | ✅ Актуален | Полный |
| `docs/OPSEC_GUIDE.md` | ✅ Актуален | Полный |
| `Reports/threat_model.md` | ✅ Актуален | STRIDE, 48 пар |
| `Reports/compliance_audit.md` | ✅ Актуален | Комплементарен к данному |
| `Reports/dpia.md` | ✅ Актуален | ОВЗД |
| `Reports/data_flow.md` | ✅ Актуален | 11 потоков |
| `Reports/risk_register.md` | ✅ Актуален | 24 риска |
| `Reports/security_checklist.md` | ✅ Актуален | 7 чеклистов |
| `Reports/hardening_report.md` | ✅ Актуален | 18 уязвимостей |
| `CHANGELOG.md` | ✅ Актуален | История версий |
| `AGENTS.md` | ✅ Актуален | Контекст проекта |

---

*Документ обновлён: 22.05.2026*
*Аудитор: Senior AppSec Engineer / Compliance Architect / 152-ФЗ специалист*
*Гриф: ДСП (для служебного пользования)*
