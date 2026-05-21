# 🔐 Архитектура безопасности

## Модель хранения данных

| Компонент | Место | Формат |
|-----------|-------|--------|
| База данных | `%APPDATA%/Excel_to_XML/app_data.db` | SQLite (WAL) |
| Персональные данные (ФИО, СНИЛС) | В БД | Полевое шифрование (Fernet) |
| API-ключ | `%APPDATA%/Excel_to_XML/api_key.json` | Encrypted (Fernet) |
| Прокси-учётные данные | `%APPDATA%/Excel_to_XML/proxy_settings.json` | Encrypted (Fernet) |
| Мастер-ключ | `%APPDATA%/Excel_to_XML/master.key` | Зашифрован через DPAPI (Windows) с entropy |
| Метаданные ключа | `%APPDATA%/Excel_to_XML/master.key.json` | JSON (версия, статус passphrase) |
| Passphrase-wrapped key | `%APPDATA%/Excel_to_XML/passphrase_wrapped.key` | Зашифрован через PBKDF2 (опционально) |
| Логи | `%APPDATA%/Excel_to_XML/log/` | Plain text с SensitiveDataFilter |
| Резервные копии БД | `%APPDATA%/Excel_to_XML/backups/` | ZIP с паролем |
| Резервные копии master.key | `%APPDATA%/Excel_to_XML/backups/` или пользовательский путь | ZIP с паролем (SHA256 константы приложения) + metadata + passphrase_wrapped.key |

## Полевое шифрование (Fernet)

Персональные данные (ФИО, СНИЛС) шифруются **на уровне отдельных полей** перед записью в SQLite.
Поиск по СНИЛС работает через хешированное поле `snils_hash` (SHA256) — сам СНИЛС в БД хранится только в зашифрованном виде.

### Безопасная память (memory safety)

Расшифрованные значения **не кэшируются** — `_DECRYPT_CACHE` удалён. Каждый вызов `decrypt_value()` / `decrypt_data()` выполняет расшифровку заново, plaintext живёт только в локальной переменной вызывающего кода.

Кэш `_ENCRYPT_CACHE` хранит только ciphertext (Fernet-зашифрованные строки), что безопасно.

## DPAPI Master Key

Мастер-ключ для Fernet защищается **Windows DPAPI** (CryptProtectData/CryptUnprotectData):
- Привязка к учётной записи Windows и конкретной машине
- Дополнительная **entropy** (`_DPAPI_ENTROPY = b"Excel_to_XML_MasterKey_v2"`) — ключ не может быть расшифрован без неё
- Другой пользователь на том же ПК не сможет расшифровать данные (даже зная entropy)
- При переустановке системы мастер-ключ теряется (требуется restore из резервной копии)
- Автоматическая миграция ключей без entropy на новый формат при первой загрузке

### Fallback режим

Если DPAPI недоступен, мастер-ключ сохраняется **в открытом виде** в `%APPDATA%/Excel_to_XML/master.key`.
В лог выводится предупреждение, а в окне "О программе" отображается красный индикатор.
**Рекомендуется** установить парольную фразу (passphrase) через окно "О программе" для дополнительной защиты.

### Проверка безопасности master.key

Функция `check_master_key_security()` в `utils/crypto.py`:
- Проверяет, используется ли DPAPI, raw-ключ и/или passphrase
- Возвращает статус: `'dpapi'`, `'dpapi_passphrase'`, `'raw_passphrase'`, `'raw'`, `'none'`
- Вызывается при старте приложения через `security_audit()`
- Отображает отпечаток ключа (fingerprint, SHA256 первые 16 символов) в окне "О программе"

## Валидация API-ключа

- После сохранения API-ключа выполняется автоматический тестовый запрос к API Минтруда (`GetEducatedPersonXML` с `PageSize=1`)
- Результат отображается зелёным/красным индикатором на вкладке "Передача данных"
- В StatusBar приложения отображается статус наличия ключа (зелёный/красный кружок)
- Функция `validate_api_key_remote()` в `api/mintrud_api.py` выполняет удалённую проверку

## Защита от XML/XEE (внешних сущностей)

Все операции парсинга XML используют безопасные парсеры:

| Файл | Библиотека |
|------|-----------|
| `importers/xml_importer.py` | `defusedxml.ElementTree` (fallback на `xml.etree.ElementTree`) |
| `api/response_parser.py` | `defusedxml.ElementTree` (fallback на `xml.etree.ElementTree`) |
| `tabs/data_transfer_tab.py` | `defusedxml.ElementTree` для парсинга журнала |
| `tabs/data_transfer_tab.py` | `lxml.etree` (безопасен по умолчанию) для XSD-валидации |
В `defusedxml` заблокированы:
- Billion Laughs (XML bombs)
- External Entity Expansion (XXE)
- DTD retrieval
- Entity recursion

## SQL Injection защита

**Все** SQL-запросы используют параметризованные запросы (`?` placeholders).
Ни один пользовательский ввод не конкатенируется в SQL строки.
Аудит проведён для всех файлов: `db/database.py`, `db/employees_repo.py`,
`db/employee_programs_repo.py`, `db/exam_journal_repo.py`, `db/workers_data_repo.py`.

### Индексы БД

Добавлены индексы на часто используемые поля для оптимизации производительности:
- `workers_data`: `snils_hash`, `program`, `created_at`
- `exam_journal`: `snils_hash`, `set_id`, `status`
- `employees`: `snils_hash`, `last_sync`
- `employee_programs`: `employee_id`, `program_id`, `status`, `updated_at`

## Passphrase (парольная фраза) — дополнительный слой защиты

Опциональный слой защиты поверх DPAPI:

- **PBKDF2HMAC** — 600000 итераций, SHA256, 32-байтовый salt
- Salt хранится вместе с зашифрованным ключом (первые 32 байта `passphrase_wrapped.key`)
- Derived key существует **только в памяти**, никогда не сохраняется на диск
- Passphrase можно установить/снять через окно "О программе"
- После установки passphrase все операции encrypt/decrypt проверяют её наличие
- При установке passphrase мастер-ключ перешифровывается: `Fernet(passphrase_key).encrypt(master_key)`
- Полностью backward compatible — если passphrase не установлена, приложение работает как раньше

## Key Rotation (ротация ключей)

Функция `rotate_master_key()` в `utils/crypto.py`:

- Генерирует новый 32-байтовый мастер-ключ
- Сохраняет его на диск (DPAPI или raw)
- Опционально вызывает `reencrypt_func(old_fernet, new_fernet)` для перешифрования данных
- При ошибке выполняет rollback (восстанавливает старый ключ) — транзакционная безопасность
- Логирует: start, success, failure
- Обновляет метаданные: версия ключа, дата ротации
- Опционально устанавливает новую passphrase

## Резервные копии

### База данных
- При запуске создаётся backup в `%APPDATA%/Excel_to_XML/backups/`
- Ротация: до 5 копий (`.backup.0` — `.backup.4`)
- Бэкап — простая копия SQLite (данные уже зашифрованы полевым шифрованием)

### Master Key
- Кнопка "Создать защищённый бэкап master.key" в окне "О программе"
- **ZIP с фиксированным паролем** — пароль НЕ зависит от мастер-ключа (решение проблемы циклической зависимости: для восстановления не нужен оригинальный ключ)
- В ZIP сохраняются: `master.key`, `master.key.json` (метаданные), `passphrase_wrapped.key` (если установлена passphrase)
- Восстановление через `restore_master_key_backup()` в `utils/crypto.py`
- Проверка целостности через `verify_backup_integrity()`

## Фильтрация логов

Все логи (`app.log`, `error.log`, `audit.log`) проходят через `SensitiveDataFilter`, который автоматически маскирует:
- СНИЛС (`123-456-789 00` → `***-***-*** **`)
- Пароли, API-ключи, токены
- ФИО (полные русские имена)
- URL с встроенными учётными данными
- Прокси-адреса

## Аудит-лог

Отдельный файл `audit.log` для ключевых действий:
- `SEND_XML` — отправка XML
- `QUERY_SETID`, `QUERY_SNILS` — запрос реестра
- `IMPORT_XLSX`, `IMPORT_XML` — импорт данных
- `EXPORT_XML`, `EXPORT_XLSX` — экспорт
- `BACKUP` — бэкапы

## Security Audit при запуске

Функция `security_audit()` в `main.py` выполняется при каждом запуске:
1. Проверяет статус master.key (DPAPI/raw/отсутствует)
2. Проверяет наличие API-ключа
3. Проверяет целостность шифрования БД (тестовое чтение)
4. Логирует все результаты

## Безопасность сети

- **TLS verify=True** по умолчанию (отключается только явно через настройки)
- Автоматический fallback между транспортами **requests** и **WinINET** при SSL-ошибках
- Поддержка корпоративных прокси с аутентификацией (`http://user:pass@host:port`)
- Windows Integrated Authentication (Negotiate/Kerberos) для корпоративных прокси
- Retry-политика: 3 попытки с экспоненциальной задержкой (429, 500, 502, 503, 504)

## Хранение данных

```
%APPDATA%/Excel_to_XML/
 ├── app_data.db              # SQLite (полевое шифрование)
 ├── master.key               # Ключ шифрования (DPAPI или raw, с entropy)
 ├── master.key.json          # Метаданные ключа (версия, статус passphrase)
 ├── passphrase_wrapped.key   # Мастер-ключ, зашифрованный passphrase (опционально)
 ├── backups/                 # Бэкапы master.key (ZIP с паролем)
 │   └── master_key_backup_*.zip
 ├── log/                     # Логи приложения
 │   ├── app.log             # Основной лог (INFO+)
 │   ├── error.log           # Только ошибки (ERROR+)
 │   └── audit.log           # Аудит действий
 ├── *.json                   # Настройки (зашифрованные)
 │   ├── api_key.json
 │   ├── org_settings.json
 │   ├── commission_data.json
 │   ├── proxy_settings.json
 │   └── programs_data.json
 └── *.json                   # UI-настройки (незашифрованные)
```
