# Описание потоков ПДн (Data Flow Diagram)

**Проект:** Excel_to_XML
**Дата:** 21.05.2026
**Версия:** 3.1.0

---

## 1. Общая схема движения данных

```
[Источник] → [Импорт/Ввод] → [SQLite (шифрование)] → [Экспорт/API] → [Получатель]
     │                │                    │                   │
     │                │                    │                   └→ Минтруд (TLS)
     │                │                    │
     │                │                    ├→ Резервная копия (ПДн в шифрованном виде)
     │                │                    └→ Удаление (UI/авто)
     │                │
     │                └→ Логи (маскированные)
     │
     └→ Аудит-лог (HMAC integrity)
```

---

## 2. Детальный анализ потоков

### Flow 1: XLSX Import

| Параметр | Значение |
|----------|----------|
| Источник | Файл XLSX (из организации-оператора) |
| Тип данных | ФИО (plaintext), СНИЛС (plaintext), Должность, Программа, Дата, Результат, Протокол |
| Преобразование | Валидация (СНИЛС 11 цифр, программа 1-29, дата не в будущем) → шифрование ФИО/СНИЛС (Fernet) → хеширование СНИЛС (SHA-256) |
| Канал передачи | Файловая система (локальный диск) |
| Шифрование в покое | Файл не шифрован (требуется BitLocker) |
| Шифрование в транзите | Нет (локальный файл) |
| Хранение | SQLite employees + employee_programs (ФИО/СНИЛС зашифрованы) |
| Аудит | IMPORT_XLSX (успех/количество/ошибки) |
| Удаление | Исходный XLSX остаётся на диске (оператор удаляет самостоятельно) |

### Flow 2: XML Import

| Параметр | Значение |
|----------|----------|
| Источник | Файл XML (RegistrySet) |
| Тип данных | ФИО (plaintext), СНИЛС (plaintext), Должность, Программа, Дата, Результат, Протокол |
| Преобразование | XXE-защита (defusedxml) → XSD-валидация (lxml secure) → шифрование ФИО/СНИЛС (Fernet) |
| Канал передачи | Файловая система |
| Шифрование в покое | Файл не шифрован |
| Хранение | SQLite employees + employee_programs |
| Аудит | IMPORT_XML |
| Защита | LimitedXMLParser (50K элементов, depth 20, size 100MB) |

### Flow 3: Manual Data Entry

| Параметр | Значение |
|----------|----------|
| Источник | Оператор (ручной ввод через UI) |
| Тип данных | ФИО, СНИЛС, Должность |
| Преобразование | Валидация → шифрование ФИО/СНИЛС (Fernet) → хеширование СНИЛС |
| Канал передачи | In-memory (Qt signals) |
| Хранение | SQLite employees + employee_programs |
| Аудит | KEY_ACCESS (при шифровании) |

### Flow 4: Data View (decrypt → display)

| Параметр | Значение |
|----------|----------|
| Источник | SQLite (employees) |
| Тип данных | ФИО (расшифрованные), СНИЛС (расшифрованный), Должность |
| Преобразование | Fernet decrypt → отображение в QTableWidget |
| Канал передачи | In-memory |
| Шифрование в покое | В БД — зашифровано |
| Шифрование в памяти | Расшифровано только на время отображения (не кэшируется) |
| Аудит | Нет (не событие аудита) |

### Flow 5: XML Export

| Параметр | Значение |
|----------|----------|
| Источник | SQLite (workers_data) |
| Тип данных | ФИО (расшифрованные), СНИЛС (расшифрованный), все поля |
| Преобразование | Fernet decrypt → формирование XML по XSD |
| Канал передачи | Файловая система (сохранение .xml) |
| Шифрование | Файл XML не шифрован (данные в открытом виде) |
| Аудит | EXPORT_XML |
| Удаление | Оператор удаляет XML-файл самостоятельно |

### Flow 6: XLSX Export

| Параметр | Значение |
|----------|----------|
| Источник | SQLite (любая таблица) |
| Тип данных | ФИО (расшифрованные), СНИЛС (расшифрованный), все поля |
| Преобразование | Fernet decrypt → openpyxl |
| Канал передачи | Файловая система (.xlsx) |
| Шифрование | Файл XLSX не шифрован (рекомендуется BitLocker) |
| Аудит | EXPORT_XLSX |

### Flow 7: API Send (encrypted DB → XML → TLS → Mintrud)

| Параметр | Значение |
|----------|----------|
| Источник | SQLite (workers_data) + XML-файл |
| Тип данных | ФИО, СНИЛС, Должность, Программа, Дата, Результат, Протокол |
| Преобразование | Формирование multipart-запроса (Request.xml + data.olot) |
| Канал передачи | TLS 1.2+, TCP/IP |
| Шифрование в транзите | TLS (verify=True) |
| Шифрование в покое | .olot (ZIP) на диске — не шифрован (временный файл) |
| Аудит | SEND_XML / SEND_XML_SIGNED |
| Хранение | Journal (exam_journal table) — ФИО/СНИЛС зашифрованы |
| Ответ | SetId → отображение в UI + сохранение в журнал |

### Flow 8: API Query (by SetId/SNILS)

| Параметр | Значение |
|----------|----------|
| Источник | API Минтруда |
| Тип данных | ФИО, СНИЛС, рег. номера |
| Преобразование | Парсинг XML (defusedxml) → нормализация дат → шифрование → запись |
| Канал передачи | TLS 1.2+ |
| Аудит | QUERY_SETID / QUERY_SNILS |
| Хранение | Только обновление journal.base_no |

### Flow 9: Backup (DB → ZIP with password)

| Параметр | Значение |
|----------|----------|
| Источник | SQLite app_data.db |
| Тип данных | Все данные (ПДн уже зашифрованы полевым шифрованием) |
| Преобразование | shutil.copy2 (авто) или ZIP+PBKDF2 (manual backup ключей) |
| Канал передачи | Файловая система |
| Шифрование | Данные уже зашифрованы; ZIP пароль для backup ключей |
| Хранение | %APPDATA%/Excel_to_XML/backups/ (до 5 копий) |
| Аудит | BACKUP |
| Удаление | Ротация (старые копии удаляются) |

### Flow 10: Audit Log (events → audit.log)

| Параметр | Значение |
|----------|----------|
| Источник | Все модули приложения |
| Тип данных | События безопасности (без ПДн) |
| Преобразование | Фильтрация (SensitiveDataFilter) → HMAC-SHA256 tag |
| Канал передачи | Файловая система |
| Хранение | %APPDATA%/log/audit.log (ротация 5x5MB) |
| Аудит | N/A (сам является аудитом) |

### Flow 11: Application Log (events → app.log / error.log)

| Параметр | Значение |
|----------|----------|
| Источник | Все модули приложения |
| Тип данных | События приложения (все ПДн маскированы) |
| Преобразование | SensitiveDataFilter (27 паттернов) |
| Канал передачи | Файловая система |
| Хранение | %APPDATA%/log/app.log, error.log (ротация 5x5MB) |

---

## 3. Матрица данных

| Операция | Формат | Шифрование | ПДн в открытом виде | Аудит |
|----------|--------|-----------|-------------------|-------|
| Import XLSX | .xlsx | Нет (файл) | Да | IMPORT_XLSX |
| Import XML | .xml | Нет (файл) | Да | IMPORT_XML |
| Manual entry | UI | В БД — да | Да (UI), Нет (БД) | — |
| View data | UI | Нет (memory) | Да (UI) | — |
| Export XML | .xml | Нет (файл) | Да | EXPORT_XML |
| Export XLSX | .xlsx | Нет (файл) | Да | EXPORT_XLSX |
| Send API | TLS | Да (TLS) | Да (XML в запросе) | SEND_XML |
| Query API | TLS | Да (TLS) | Да (в ответе) | QUERY_SETID |
| Backup | .db | Полевое | Нет (только ciphertext) | BACKUP |
| Delete | SQL | Н/Д | Нет | DELETE_ALL (TODO) |

---

## 4. Хранение данных

| Хранилище | Что хранит | Шифрование | Путь |
|-----------|-----------|-----------|------|
| SQLite employees | Сотрудники (ФИО, СНИЛС) | Fernet field-level | %APPDATA%/Excel_to_XML/app_data.db |
| SQLite employee_programs | Программы обучения | Нет (не ПДн) | %APPDATA%/Excel_to_XML/app_data.db |
| SQLite workers_data | Рабочие данные (ФИО, СНИЛС) | Fernet field-level | %APPDATA%/Excel_to_XML/app_data.db |
| SQLite exam_journal | Журнал (ФИО, СНИЛС) | Fernet field-level | %APPDATA%/Excel_to_XML/app_data.db |
| master.key | Fernet ключ | DPAPI + entropy | %APPDATA%/Excel_to_XML/master.key |
| master.key.json | Метаданные ключа | HMAC integrity | %APPDATA%/Excel_to_XML/master.key.json |
| passphrase_wrapped.key | Passphrase-wrapped key (опц.) | PBKDF2 + Fernet | %APPDATA%/Excel_to_XML/passphrase_wrapped.key |
| api_key.json | API-ключ Минтруда | Fernet | %APPDATA%/Excel_to_XML/api_key.json |
| proxy_settings.json | Proxy credentials | Fernet | %APPDATA%/Excel_to_XML/proxy_settings.json |
| log/app.log | Логи (маскированные) | Нет (plaintext) | %APPDATA%/Excel_to_XML/log/ |
| log/error.log | Ошибки (маскированные) | Нет | %APPDATA%/Excel_to_XML/log/ |
| log/audit.log | События безопасности | HMAC tag | %APPDATA%/Excel_to_XML/log/ |
| backups/ | Копии БД (до 5) | Полевое (внутри БД) | %APPDATA%/Excel_to_XML/backups/ |
| backups/ | Backup ключей | ZIP+PBKDF2 | %APPDATA%/Excel_to_XML/backups/ |

---

## 5. Схема удаления данных

| Операция | Механизм | Безвозвратность | Аудит |
|----------|----------|----------------|-------|
| Удаление одной записи | SQL DELETE FROM employees WHERE id=? | Только SQL DELETE (VACUUM) | ❌ Отсутствует |
| Удаление всех данных | SQL DELETE FROM employees + employee_programs | Только SQL DELETE | ❌ Отсутствует |
| Удаление БД | Удаление app_data.db | Только файловая система (Recycle Bin) | ❌ |
| Удаление master.key | Удаление файла | Безвозвратно (ключ утерян) | ❌ |
| Удаление backup | SQL DELETE FROM backups (логическое) | Только SQL DELETE | ❌ |
| Ротация логов | Удаление старых файлов | Файловая система | ❌ |

**Рекомендации:**
- Реализовать DELETE_ALL audit event (сейчас отсутствует в audit.py)
- Реализовать secure delete (перезапись перед удалением)
- Реализовать retention policy (автоматическое удаление по сроку)

---

*Документ обновлён: 21.05.2026*
*Версия: 1.0*
