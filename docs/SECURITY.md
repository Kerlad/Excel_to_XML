# 🔐 Архитектура безопасности

## Модель хранения данных

| Компонент | Место | Формат |
|-----------|-------|--------|
| База данных | `%APPDATA%/Excel_to_XML/app_data.db` | SQLite (WAL) |
| Персональные данные (ФИО, СНИЛС) | В БД | Полевое шифрование (Fernet) |
| API-ключ | `%APPDATA%/Excel_to_XML/api_key.json` | Encrypted (Fernet) |
| Прокси-учётные данные | `%APPDATA%/Excel_to_XML/proxy_settings.json` | Encrypted (Fernet) |
| Мастер-ключ | `%APPDATA%/Excel_to_XML/master.key` | Зашифрован через DPAPI (Windows) |
| Логи | `%APPDATA%/Excel_to_XML/log/` | Plain text с SensitiveDataFilter |
| Резервные копии БД | `%APPDATA%/Excel_to_XML/backups/` | ZIP с паролем (SHA256 мастер-ключа) |
| Резервные копии master.key | `%APPDATA%/Excel_to_XML/backups/` или пользовательский путь | ZIP (без пароля, хранить в надёжном месте) |

## Полевое шифрование (Fernet)

Персональные данные (ФИО, СНИЛС) шифруются **на уровне отдельных полей** перед записью в SQLite.
Поиск по СНИЛС работает через хешированное поле `snils_hash` (SHA256) — сам СНИЛС в БД хранится только в зашифрованном виде.

## DPAPI Master Key

Мастер-ключ для Fernet защищается **Windows DPAPI** (CryptProtectData):
- Привязка к учётной записи Windows и конкретной машине
- Другой пользователь на том же ПК не сможет расшифровать данные
- При переустановке системы мастер-ключ теряется (требуется restore из резервной копии)

### Fallback режим

Если DPAPI недоступен, мастер-ключ сохраняется **в открытом виде** в `%APPDATA%/Excel_to_XML/master.key`.
В лог выводится предупреждение, а в окне "О программе" отображается красный индикатор.
**Рекомендуется** создать защищённую резервную копию master.key через кнопку в окне "О программе".

### Проверка безопасности master.key

Функция `check_master_key_security()` в `utils/crypto.py`:
- Проверяет, используется ли DPAPI или raw-ключ
- Возвращает статус: `'dpapi'` (защищён), `'raw'` (уязвим), `'none'` (отсутствует)
- Вызывается при старте приложения через `security_audit()`

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

## Резервные копии

### База данных
- При запуске создаётся backup в `%APPDATA%/Excel_to_XML/backups/`
- Ротация: до 5 копий (`.backup.1.zip` — `.backup.5.zip`)
- Бэкап упаковывается в ZIP с паролем (SHA256 хеш мастер-ключа, 16 символов)
- Данные в БД уже зашифрованы (полевое шифрование), но ZIP добавляет дополнительный уровень защиты

### Master Key
- Кнопка "Создать защищённый бэкап master.key" в окне "О программе"
- Сохраняет `master.key` в ZIP-архив в выбранную пользователем директорию
- Восстановление через `restore_master_key_backup()` в `utils/crypto.py`

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
 ├── master.key               # Ключ шифрования (DPAPI или raw)
 ├── backups/                 # Бэкапы БД (ZIP с паролем, ротация 5 шт.)
 ├── log/                     # Логи приложения
 │   ├── app.log             # Основной лог (INFO+)
 │   ├── error.log           # Только ошибки (ERROR+)
 │   └── audit.log           # Аудит действий
 ├── settings/                # Настройки (зашифрованные)
 │   ├── api_key.json
 │   ├── org_settings.json
 │   ├── commission_data.json
 │   └── proxy_settings.json
 └── *.json                   # UI-настройки
```
