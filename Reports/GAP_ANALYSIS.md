# Gap Analysis — Аудит соответствия ИСПДн

**Проект:** Excel_to_XML
**Дата:** 22.05.2026
**Версия приложения:** 3.0.0

---

## 1. 152-ФЗ — Матрица gaps

| № | Требование | Статус | Риск | Что исправить |
|---|-----------|--------|------|---------------|
| 1 | Идентификация и аутентификация (ст.19) | ✅ Частично | Средний | Passphrase — хорошо. Нет ролевой модели — компенсируется организационно |
| 2 | Разграничение доступа (ст.19) | ❌ Gap | Высокий | Нет ролей (админ/оператор/наблюдатель). Организационная компенсация: 1 ПК = 1 оператор |
| 3 | Регистрация событий (ст.19) | ⚠️ Частично | Высокий | 17 из 34 audit-событий не эмитируются (dead code). Нет верификации HMAC |
| 4 | Криптографическая защита (ст.19) | ✅ Реализовано | Низкий | Fernet + DPAPI + PBKDF2. Нет ГОСТ, нет сертифицированного СКЗИ |
| 5 | Контроль целостности (ст.19) | ⚠️ Частично | Средний | HMAC ключей есть. Нет PRAGMA integrity_check при старте |
| 6 | Восстановление (ст.19) | ⚠️ Частично | Средний | Backup есть. ZIP-шифрование — PKWARE (слабое). Нет проверки целостности backup |
| 7 | Назначение ответственного (ст.22.1) | ❌ Орг. мера | Высокий | Требуется приказ руководителя |
| 8 | Политика ПДн (ст.18.1) | ❌ Орг. мера | Высокий | Требуется опубликовать |
| 9 | Уведомление РКН (ст.22) | ❌ Орг. мера | Высокий | Форма 4-ПДн до начала обработки |
| 10 | Сроки хранения (ст.5, 21) | ❌ Gap | Средний | Нет retention policy, нет автоудаления |
| 11 | Удаление ПДн (ст.5) | ❌ Gap | Средний | SQL DELETE без secure delete (перезаписи) |
| 12 | Права субъекта (ст.14-17) | ⚠️ Частично | Средний | Доступ через оператора. Нет блокирования обработки |
| 13 | Безопасность по умолчанию | ✅ | Низкий | PRODUCTION MODE, безопасные defaults |
| 14 | Минимизация ПДн | ✅ | Низкий | Только необходимые поля |

---

## 2. ПП РФ №1119 — Матрица gaps

| № | Мера (п.13 УЗ-3) | Статус | Риск | Что исправить |
|---|-------------------|--------|------|---------------|
| 1 | Идентификация (п.а) | ✅ | Низкий | DPAPI + passphrase |
| 2 | Управление доступом (п.а) | ⚠️ Частично | Средний | Нет ролей — компенсация организационная |
| 3 | Ограничение ПО (п.б) | ❌ Орг. мера | Средний | AppLocker — на уровне ОС |
| 4 | Защита носителей (п.в) | ❌ Орг. мера | Высокий | BitLocker обязателен |
| 5 | Регистрация событий (п.г) | ⚠️ Частично | Высокий | Dead code в audit. Нет верификации HMAC |
| 6 | Антивирус (п.д) | ❌ Орг. мера | Высокий | Microsoft Defender обязателен |
| 7 | Обнаружение вторжений (п.е) | ❌ N/A | Низкий | Для десктоп-приложения не требуется |
| 8 | Контроль целостности (п.ж) | ⚠️ Частично | Средний | HMAC ключей OK. Нет integrity_check БД |
| 9 | Восстановление (п.з) | ⚠️ Частично | Средний | Backup OK. ZIP Crypto слабый |
| 10 | СКЗИ (п.и) | ⚠️ Частично | Средний | AES-128-CBC. НЕ ГОСТ. НЕ сертифицировано |
| 11 | Каналы связи (п.к) | ✅ | Низкий | TLS 1.2+ verify=True |

---

## 3. Secure Coding — Матрица gaps

| № | Аспект | Статус | Риск | Что исправить |
|---|--------|--------|------|---------------|
| 1 | SQL-инъекции | ✅ | Низкий | Только parameterized queries |
| 2 | XXE/XEE/Billion Laughs | ✅ | Низкий | defusedxml + LimitedXMLParser |
| 3 | TOCTOU в XML импорте | ❌ Gap | Средний | Двойное чтение XML (XSD валидация) — race condition |
| 4 | SNILS в error messages | ❌ Gap | Высокий | xlsx_importer.py:52 — raw SNILS в ошибке |
| 5 | PII в error report XLSX | ❌ Gap | Высокий | error_report.py — ПДн в отчёте об ошибках |
| 6 | URL эндпоинты в логах | ⚠️ Gap | Средний | 5 мест логируют полный URL API |
| 7 | f-string логи с ПДн | ⚠️ Gap | Средний | employee_summary_tab.py:92 |
| 8 | XML pattern (logger) не работает | ❌ Gap | Средний | Нет trailing http — XML не маскируется |
| 9 | %% экранирование double-pass | ❌ Gap | Низкий | Двойное экранирование % в error.log |
| 10 | Dead code в safe_format_exception | ⚠️ | Низкий | if False else [] |
| 11 | JSON маскировка только строк | ⚠️ Gap | Средний | Не маскируются числовые/булевы/nested sensitive values |
| 12 | XSD output validation отсутствует | ❌ Gap | Средний | xml_exporter — нет XSD валидации output |
| 13 | Control chars в XML output | ❌ Gap | Средний | _escape_xml не фильтрует control chars |
| 14 | Audit HMAC не верифицируется | ❌ Gap | Критический | HMAC tags пишутся, но никогда не проверяются |
| 15 | Audit hash chaining отсутствует | ❌ Gap | Высокий | Нет chaining — selective deletion не обнаруживается |
| 16 | Audit HMAC tag — 48 bit | ❌ Gap | Высокий | 12 hex chars (48 bit) — слабый |
| 17 | Audit fallback key hardcoded | ❌ Gap | Высокий | b"EXCEL_XML_AUDIT_V3" в исходниках |
| 18 | 17/34 audit events dead code | ❌ Gap | Высокий | Не эмитируются KEY_ACCESS, LOGIN, BACKUP, SHUTDOWN и др. |
| 19 | Мастер-ключ в памяти (global) | ❌ Gap | Средний | _MASTER_KEY не зануляется |
| 20 | Encrypt cache — plaintext keys | ❌ Gap | Средний | Ключи кэша — plaintext (2000 entries) |
| 21 | VirtualLock не реализован | ❌ Gap | Средний | docstring врёт (claim не соответствует коду) |
| 22 | Thread safety crypto — race conditions | ❌ Gap | Средний | _MASTER_KEY, _FERNET_INSTANCE без лока |
| 23 | Thread safety secure_temp | ❌ Gap | Средний | get_secure_temp_dir() race: два потока = orphan dir |
| 24 | ACL — SE_DACL_PROTECTED не установлен | ❌ Gap | Средний | Наследованные ACE от %TEMP% |
| 25 | File extension case-sensitive (.xlsx) | ❌ Gap | Низкий | Не принимает .XLSX |
| 26 | Password для XLSX не передаётся | ❌ Gap | Средний | password параметр игнорируется |
| 27 | Name validation inconsistent | ⚠️ Gap | Низкий | Manual vs XLSX импорт — разная логика |
| 28 | Concurrent import guard отсутствует | ❌ Gap | Средний | Нет защиты от множественного импорта |
| 29 | Транзакции — DatabaseLockError dead code | ❌ Gap | Низкий | Никогда не выбрасывается |
| 30 | Backup ZIP — PKWARE (слабое шифрование) | ❌ Gap | Средний | Нужен pyzipper с AES-256 или Fernet |
| 31 | Бэкап с random password (unrecoverable) | ⚠️ Gap | Средний | Падение на random — потеря данных |
| 32 | QUERY_SETID не логируется | ❌ Gap | Средний | Определён, не эмитируется |
| 33 | Main-thread API call в _query_single | ❌ Gap | Средний | Блокировка UI |

---

## 4. AppSec — Матрица gaps

| № | Аспект | Статус | Риск | Что исправить |
|---|--------|--------|------|---------------|
| 1 | Memory dump resistance | ❌ Gap | Средний | Ключи в global, не зануляются |
| 2 | Clipboard protection | ❌ Gap | Средний | Нет auto-clear |
| 3 | Cert pinning | ❌ Gap | Низкий | Невозможно — сервер не предоставляет |
| 4 | Rate limiting (API) | ❌ Gap | Низкий | Нет защиты от повторяющихся запросов |
| 5 | Secure update mechanism | ❌ Gap | Средний | Нет встроенного обновления, нет signature verification |
| 6 | WORM audit log | ❌ Gap | Средний | audit.log — обычный файл |
| 7 | Role-based access | ❌ Gap | Высокий | Нет ролей |
| 8 | Brute force protection | ❌ Gap | Средний | Нет ограничения попыток passphrase |

---

## 5. Privacy-by-design — Матрица gaps

| № | Принцип | Статус | Риск | Что исправить |
|---|---------|--------|------|---------------|
| 1 | Минимизация | ✅ | Низкий | Только необходимые поля |
| 2 | Ограничение доступа | ⚠️ | Средний | Нет ролей, passphrase для всех |
| 3 | Прозрачность | ⚠️ | Средний | Нет уведомления субъекта через приложение |
| 4 | Контроль субъекта | ❌ Gap | Средний | Субъект не может управлять данными |
| 5 | Безопасность по умолчанию | ✅ | Низкий | PRODUCTION MODE |
| 6 | End-to-end | ✅ | Низкий | Шифрование от ввода до API |
| 7 | Data retention | ❌ Gap | Средний | Нет сроков автоудаления |
| 8 | Secure deletion | ❌ Gap | Средний | SQL DELETE без перезаписи |

---

## 6. Итоговая статистика

### Всего gaps: 48

| Категория | Количество | Критических | Высоких | Средних | Низких |
|-----------|-----------|-------------|---------|---------|--------|
| 152-ФЗ | 14 | 0 | 4 | 5 | 5 |
| ПП 1119 | 11 | 0 | 2 | 5 | 4 |
| Secure coding | 33 | 1 | 10 | 18 | 4 |
| AppSec | 8 | 0 | 1 | 6 | 1 |
| Privacy-by-design | 8 | 0 | 0 | 5 | 3 |

### По severity

| Severity | Count | Ключевые проблемы |
|----------|-------|-------------------|
| 🔴 Critical | 1 | Audit HMAC не верифицируется (security theater) |
| 🟠 High | 17 | SNILS leak, 17 audit dead code, no hash chaining, audit fallback key, TOCTOU, etc. |
| 🟡 Medium | 39 | Retention, secure delete, key in memory, cache, thread safety, ACL, etc. |
| 🟢 Low | 12 | Name validation, file extension, dead code, docstring, etc. |

---

*Документ обновлён: 22.05.2026*
