# Техническое задание на устранение замечаний аудита безопасности

**Дата:** 22.05.2026
**Версия приложения:** 3.0.0 → 3.1.0
**Тип документа:** Техническое задание на доработку (ФИКС)
**Гриф:** ДСП (для служебного пользования)

---

## Условные обозначения

- 🔴 **P0** — Критический (блокирующий для production)
- 🟠 **P1** — Высокий (обязательный к исправлению)
- 🟡 **P2** — Средний (рекомендованный к исправлению)
- 🟢 **P3** — Низкий (желательный к исправлению)

---

## 1. АУДИТ-СИСТЕМА (CRITICAL)

### 🔴 P0-01: HMAC-верификация audit.log

**Где:** `utils/audit.py`
**Проблема:** HMAC-теги пишутся в audit.log, но функция верификации отсутствует. Любая модификация/удаление записей не обнаруживается.

**Требование к реализации:**

1. Создать функцию `verify_audit_log(log_path: str) -> list[dict]`:
   - Читает audit.log построчно
   - Для каждой строки извлекает HMAC-тег (первые 12 hex-символов в квадратных скобках)
   - Пересчитывает HMAC для содержимого (`timestamp|event | detail`) и сравнивает с извлечённым тегом
   - Возвращает список записей с нарушенной целостностью: `[{'line_number': int, 'expected_tag': str, 'actual_tag': str, 'content': str}, ...]`
   - Использует `hmac.compare_digest()` для constant-time сравнения
   - Логирует результат через `log_audit("AUDIT_INTEGRITY_CHECK", ...)`

2. Создать функцию `verify_audit_log_interactive(parent_widget)`:
   - Вызывает `verify_audit_log()`
   - Показывает результат пользователю:
     - Если integrity OK: `QMessageBox.information("Целостность audit.log подтверждена")`
     - Если найдены нарушения: `DetailsDialog` со списком скомпрометированных записей
     - Кнопка "Экспортировать отчёт" (CSV со списком нарушений)

3. Интегрировать в `LogViewerDialog`:
   - Добавить кнопку "Проверить целостность аудита"
   - Вызывать автоматически при открытии audit.log (в фоновом потоке)

4. Дополнительно:
   - Увеличить HMAC tag с 12 hex-символов (48 бит) до **64 hex-символов** (256 бит) — `hexdigest()[:64]`
   - Совместимость со старыми записями: если тег длиной 12, использовать старый `_get_hmac_key()`, если 64 — новый

**Критерий приёмки:**
- `verify_audit_log()` находит подменённые записи (тест: изменить одну строку в audit.log)
- `verify_audit_log()` проходит на немодифицированном audit.log
- HMAC tag в новых записях — 64 hex-символа
- Старые записи с 12-символьными тегами продолжают читаться
- Кнопка в LogViewerDialog работает

**Файлы для изменения:** `utils/audit.py`, `utils/log_viewer_dialog.py`
**Новые тесты:** `tests/test_audit_verification.py` (минимум 3 теста)

---

### 🔴 P0-02: Убрать hardcoded fallback HMAC-ключ

**Где:** `utils/audit.py:_get_hmac_key()`
**Проблема:** Если `get_key_fingerprint()` не работает, используется `b"EXCEL_XML_AUDIT_V3"` — любой может подделать аудит.

**Требование к реализации:**

1. Убрать hardcoded fallback строку `b"EXCEL_XML_AUDIT_V3"`
2. При невозможности получить ключ из `get_key_fingerprint()`:
   - Логировать `CRITICAL` уровень: "Audit HMAC key unavailable — audit integrity disabled"
   - Возвращать `None`
3. `_compute_audit_hmac()` должна проверять `if _get_hmac_key() is None`:
   - Если ключа нет — тег не добавляется (запись пишется без `[hmac_tag]`)
4. `log_audit()` должна проверять наличие ключа и добавлять предупреждение в лог

**Критерий приёмки:**
- Без master.key audit.log пишется без HMAC-тегов (с предупреждением)
- После инициализации master.key HMAC-теги работают
- Hardcoded `b"EXCEL_XML_AUDIT_V3"` удалён из кода

**Файлы для изменения:** `utils/audit.py`
**Новые тесты:** 2 теста (без master.key, с master.key)

---

## 2. УТЕЧКИ ПДн (HIGH)

### 🟠 P1-01: SNILS в error messages XLSX импорта

**Где:** `importers/xlsx_importer.py:52`
**Проблема:** Raw-значение СНИЛС вставляется в сообщение об ошибке:
```python
'message': f"СНИЛС должен содержать 11 цифр (введено: {value})"
```

**Требование к реализации:**

1. Заменить на маскированное значение:
```python
masked = str(value)[:3] + '***' + str(value)[-2:] if len(str(value)) > 5 else '***'
'message': f"СНИЛС должен содержать 11 цифр (введено: {masked})"
```

2. Аналогично проверить все остальные `f"..."` с `{value}` в `xlsx_importer.py`:
   - `validate_result` — строка 72: `f"Результат должен быть... (введено: {result})"` — здесь не ПДн, но тоже маскировать
   - `validate_date` — строка 117: `f"Дата некорректна"` — OK, нет value
   - `validate_name` — строка 85: не содержит value
   - `validate_required` — строка 131: не содержит value

3. Добавить тест, проверяющий, что SNILS не появляется в error_details в открытом виде

**Дополнительно:** В `validate_result` также не ПДн, но для единообразия маскировать значения длиннее 3 символов.

**Критерий приёмки:**
- При импорте XLSX с невалидным СНИЛС в error_details нет полного номера
- Тест проверяет: `all("***" in err['message'] for err in errors)`

**Файлы для изменения:** `importers/xlsx_importer.py`
**Новые тесты:** `tests/test_importers.py` — добавить тест

---

### 🟠 P1-02: PII в error report XLSX

**Где:** `importers/error_report.py:67`
**Проблема:** В error_report.py при формировании отчёта об ошибках могут попадать ПДн.

**Требование к реализации:**

1. Аудит путей передачи данных в error_report:
   - Проверить, какие данные попадают в error_details при импорте
   - Убедиться, что все ПДн маскируются перед записью в error_report.xlsx
2. Если в error_details попадают raw-значения — применить `filter_sensitive_text()` перед записью
3. Убедиться, что bug с 3-tuple key исправлен (см. P1-07)

**Файлы для изменения:** `importers/error_report.py`

---

### 🟠 P1-03: URL API эндпоинты в логах

**Где:**
- `api/backends/requests_backend.py:63,91`
- `api/backends/wininet_backend.py:104,148`
- `api/mintrud_api.py:474`

**Проблема:** Полные URL API (включая путь и параметры) логируются через `logger.info(f"... {url}")`.

**Требование к реализации:**

1. Заменить логирование полных URL на маскированные:
```python
# Было:
logger.info(f"RequestsBackend: POST {url}")
# Стало:
from urllib.parse import urlparse
parsed = urlparse(url)
logger.info("RequestsBackend: POST %s://%s%s", parsed.scheme, parsed.netloc, parsed.path)
```

2. Или, проще — определить константу `API_ENDPOINT` и логировать только метод + endpoint name

3. Для `mintrud_api.py:474` — аналогично, маскировать query-параметры

**Критерий приёмки:**
- В логах нет полных URL с query-параметрами
- В логах есть путь эндпоинта без параметров

**Файлы для изменения:** `api/backends/requests_backend.py`, `api/backends/wininet_backend.py`, `api/mintrud_api.py`

---

### 🟠 P1-04: f-string логи с ПДн в employee_summary_tab

**Где:** `tabs/employee_summary_tab.py:92`
**Проблема:**
```python
logger.warning(f"API error: {result.get('error')}")
```
Нарушение AGENTS.md #3 — f-string без `filter_sensitive_text()`.

**Требование к реализации:**

1. Заменить на:
```python
logger.warning("API error: %s", filter_sensitive_text(str(result.get('error'))))
```

2. Проверить все `logger.*` вызовы в `employee_summary_tab.py`:
   - Строки 92, 95, 255, 436, 446, 1116, 1178, 1230, 1251, 1313
   - Убедиться, что все используют `%s` + `filter_sensitive_text()`
   - У f-string добавить `filter_sensitive_text()`

**Файлы для изменения:** `tabs/employee_summary_tab.py`

---

### 🟠 P1-05: XML pattern в SensitiveDataFilter не работает

**Где:** `utils/logger.py:71`
**Проблема:**
```python
(r'(<\?xml[^>]*>.*</[^>]+>)(?:\s*http)', '<XML_PAYLOAD ***>')
```
Требует `http` после XML-тега — 99% XML-логов не маскируются.

**Требование к реализации:**

1. Заменить на два паттерна:
```python
# XML с тегом (любой XML, содержащий <?xml)
(r'<\?xml[^>]*>.*?</[^>]+>', '<XML_PAYLOAD ***>'),
# API XML (начинается с <Request> или <EducatedPersonFilter>)
(r'(<(?:Request|EducatedPersonFilter|RegistrySet)[^>]*>.*?</(?:Request|EducatedPersonFilter|RegistrySet)>)', '<XML_API_PAYLOAD ***>'),
```

2. Убедиться, что `re.DOTALL` не требуется (`.` не включает `\n`, что хорошо для производительности)

**Критерий приёмки:**
- Любой XML в логах маскируется
- Тест: `<Request><ApiKey>secret123</ApiKey></Request>` → маскируется
- Тест: `<?xml version="1.0"?><root><data>test</data></root>` → маскируется

**Файлы для изменения:** `utils/logger.py`
**Новые тесты:** В `tests/test_logger_audit.py` — добавить 2 теста

---

## 3. AUDIT-EVENTS (HIGH)

### 🟠 P1-06: Эмитировать 17 недостающих audit-событий

**Где:** Весь код
**Проблема:** 17 из 34 событий определены в `AUDIT_EVENTS`, но никогда не эмитируются.

**Требование к реализации:**

1. Добавить `from utils.audit import log_audit` в каждый модуль, где требуется

2. **`QUERY_SETID`** → `api/mintrud_api.py:query_by_setid()`:
```python
log_audit("QUERY_SETID", f"set_id={set_id}, records={len(records)}")
```

3. **`IMPORT_XLSX`** → `tabs/data_entry_tab.py:_on_import_finished()`:
```python
log_audit("IMPORT_XLSX", f"rows={row_count}, records={len(records)}, errors={error_count}")
```

4. **`IMPORT_XML`** → `tabs/data_entry_tab.py:_on_import_finished()`:
```python
log_audit("IMPORT_XML", f"records={len(records)}, errors={error_count}")
```

5. **`EXPORT_XML`** → `exporters/xml_exporter.py:export_to_xml()`:
```python
log_audit("EXPORT_XML", f"records={len(records)}, file={os.path.basename(file_path)}")
```

6. **`EXPORT_XLSX`** → `tabs/employee_summary_tab.py:_export_xlsx()`:
```python
log_audit("EXPORT_XLSX", f"employees={len(employees)}")
```

7. **`LOGIN`** → `api/mintrud_api.py:validate_api_key()` (при успешной валидации):
```python
log_audit("LOGIN", "API key validated successfully")
```

8. **`BACKUP`** → `db/database.py:_create_backup()`:
```python
log_audit("BACKUP", f"backup_path={backup_path}, size={size_mb:.1f}MB")
```

9. **`KEY_ACCESS`** → `utils/crypto.py:_get_or_create_master_key()`:
```python
log_audit("KEY_ACCESS", "Master key loaded from storage")
```

10. **`KEY_ROTATION`** → `utils/crypto.py:rotate_master_key()`:
```python
log_audit("KEY_ROTATION", f"old_fingerprint={old_fp}, new_fingerprint={new_fp}")
```

11. **`KEY_BACKUP`** → `utils/crypto.py:create_master_key_backup()`:
```python
log_audit("KEY_BACKUP", f"backup_path={backup_path}")
```

12. **`KEY_RESTORE`** → `utils/crypto.py:restore_master_key_backup()`:
```python
log_audit("KEY_RESTORE", "Master key restored from backup")
```

13. **`PASSPHRASE_SET`** → `utils/crypto.py:set_passphrase()`:
```python
log_audit("PASSPHRASE_SET", "Passphrase protection enabled")
```

14. **`PASSPHRASE_REMOVED`** → `utils/crypto.py:remove_passphrase()`:
```python
log_audit("PASSPHRASE_REMOVED", "Passphrase protection removed")
```

15. **`TLS_ERROR`** → `api/mintrud_api.py:_try_backends()` (при SSL ошибке):
```python
log_audit("TLS_ERROR", f"SSL connection failed: {str(e)[:100]}")
```

16. **`EXPORT_PLAN`** → `tabs/employee_summary_tab.py:_generate_plan()`:
```python
log_audit("EXPORT_PLAN", f"employees={len(plan_data)}, not_trained={n}, expired={e}, trained={t}")
```

17. **`EXPORT_SNAPSHOT`** → `tabs/employee_summary_tab.py:_show_current_snapshot()`:
```python
log_audit("EXPORT_SNAPSHOT", f"employees={total}")
```

18. **`EXPORT_TRAINED_REPORT`** → `tabs/employee_summary_tab.py:_generate_trained_report()`:
```python
log_audit("EXPORT_TRAINED_REPORT", f"employees={len(trained)}")
```

19. **`SHUTDOWN`** → `main.py:closeEvent()`:
```python
log_audit("SHUTDOWN", "Application shutdown")
```

20. **`ERROR_RESPONSE_SAVED`** → `api/mintrud_api.py:_save_error_response()`:
```python
log_audit("ERROR_RESPONSE_SAVED", f"status_code={status_code}, size={len(filtered_body)}")
```

21. **`PROXY_CHANGE`** → `tabs/data_transfer_tab.py:_save_proxy()`:
```python
log_audit("PROXY_CHANGE", f"mode={mode}, tls_verify={tls_verify}")
```

22. **`BACKEND_CHANGE`** → `tabs/data_transfer_tab.py:_on_backend_change()`:
```python
log_audit("BACKEND_CHANGE", f"backend={backend_name}")
```

23. **`IMPORT_CANCELLED`** — уже логируется в `utils/workers.py:63` — OK

**Критерий приёмки:**
- После выполнения всех действий audit.log содержит соответствующие события
- `grep -c "KEY_ACCESS\|LOGIN\|BACKUP\|SHUTDOWN" audit.log` > 0
- Тест интеграционный: выполнить последовательность действий → проверить audit.log

**Файлы для изменения:** `api/mintrud_api.py`, `tabs/data_entry_tab.py`, `tabs/employee_summary_tab.py`, `tabs/data_transfer_tab.py`, `exporters/xml_exporter.py`, `db/database.py`, `utils/crypto.py`, `main.py`, `utils/secure_temp.py`

---

## 4. AUDIT HASH CHAINING (HIGH)

### 🟠 P1-07: Добавить hash chaining в audit.log

**Где:** `utils/audit.py`
**Проблема:** Каждая аудито-запись HMAC-ится независимо. Selective deletion не обнаруживается.

**Требование к реализации:**

1. В `log_audit()` добавить hash chaining:
```python
_prev_hash = "0" * 64  # инициализация при старте

def log_audit(event, detail=""):
    global _prev_hash
    ...
    chain_input = _prev_hash + "|" + timestamp + "|" + msg
    hmac_tag = _compute_audit_hmac(chain_input)
    _prev_hash = hmac_tag  # или SHA256(hmac_tag) для 64-символов
    audit_logger.info("[ch=%s] %s", _prev_hash, msg)
```

2. HMAC теперь считается от: `prev_hash | timestamp | event | detail`
3. При верификации — проверять цепочку: hash(prev) должен совпадать с hash текущей записи

**Файлы для изменения:** `utils/audit.py`

---

## 5. LOGGER (HIGH)

### 🟠 P1-08: %% double escaping в error.log

**Где:** `utils/logger.py:81`
**Проблема:** Фильтр применяется дважды к одному LogRecord (main_handler + error_handler). При первом проходе `%` → `%%`, при втором `%%` → `%%%%`.

**Требование к реализации:**

1. В `SensitiveDataFilter.filter()` добавить guard:
```python
if hasattr(record, '_sanitized'):
    return True
record._sanitized = True
```

2. Или альтернатива — убрать `msg.replace('%', '%%')` полностью, т.к. `record.args` уже очищен (строка 83).

**Рекомендуемый вариант:** убрать `record.msg = msg.replace('%', '%%')` — он не нужен после `record.args = ()`.

**Файлы для изменения:** `utils/logger.py`

---

### 🟠 P1-09: Dead code в safe_format_exception

**Где:** `utils/logger.py:127-129`
**Проблема:**
```python
tb_lines = traceback.format_exception(
    type(None), None, None, limit=limit
) if False else []
```

**Требование:** Удалить строки 127-129 полностью. Если нужна работающая версия — переписать:
```python
def safe_format_exception(limit=3):
    import traceback, sys
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_type is None:
        return "No exception"
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb, limit=limit)
    return ''.join(tb_lines)
```

**Файлы для изменения:** `utils/logger.py`

---

### 🟠 P1-10: JSON маскировка — числовые/булевы значения

**Где:** `utils/logger.py:99-105`
**Проблема:** Маскируются только строковые значения: `"key": "value"`, не маскируются `"key": 123`, `"key": true`, `"key": {"nested": "secret"}`.

**Требование к реализации:**

1. Расширить паттерн:
```python
# Старый:
r'"(password|secret|api_key|...)"\s*:\s*"([^"]+)"'
# Новый:
r'"(password|secret|api_key|...)"\s*:\s*(?:"[^"]*"|\d+|true|false|null|\{[^}]*\})'
```

2. Добавить рекурсивную обработку вложенных JSON (уже есть `_mask_json_sensitive_keys`, использовать её)

**Файлы для изменения:** `utils/logger.py`
**Новые тесты:** 2 теста (числовое значение, булево, вложенный JSON)

---

## 6. КРИПТОГРАФИЯ (HIGH)

### 🟠 P1-11: Memory safety — мастер-ключ не зануляется

**Где:** `utils/crypto.py:27`
**Проблема:** `_MASTER_KEY = None` (module-level global) — живёт всю жизнь процесса.

**Требование к реализации:**

1. После каждого использования мастер-ключа (decrypt/encrypt) занулять:
```python
import ctypes
def _zero_memory(data: bytes):
    if data:
        ctypes.memset(id(data) + 16, 0, len(data))  # +16 для PyObject header
```
**Внимание:** `ctypes.memset` может не работать с `bytes` из-за интернирования. Использовать `bytearray` для временных значений или `sodium.memzero` через `nacl.bindings`.

2. Альтернатива (рекомендуемая) — **не хранить мастер-ключ в global**. 
   - Создать `class MasterKeyManager`:
     - `_key: Optional[bytes]` — инстансный, не классовый
     - `__enter__` / `__exit__` — context manager, зануляет при выходе
     - `use_key(callback)` — передаёт ключ в callback, зануляет после

3. Если module-level global остаётся — хотя бы добавить:
```python
import atexit
atexit.register(lambda: _zero_memory(_MASTER_KEY) if _MASTER_KEY else None)
```

4. `_ENCRYPT_CACHE` — переделать ключи с plaintext→ciphertext на ciphertext→plaintext:
   - Сейчас: `Dict[plaintext, ciphertext]` — ключи кэша в открытом виде
   - Должно быть: `Dict[ciphertext, plaintext]` — ключи кэша зашифрованы

5. `_CURRENT_PASSPHRASE_KEY` — добавлять `_zero_memory()` при `clear_caches()` и при выходе

6. VirtualLock — либо реализовать через `ctypes.windll.kernel32.VirtualLock`, либо удалить упоминание из docstring

**Файлы для изменения:** `utils/crypto.py`

---

### 🟠 P1-12: Thread safety crypto

**Где:** `utils/crypto.py`
**Проблема:** `_MASTER_KEY`, `_FERNET_INSTANCE`, `_CURRENT_PASSPHRASE_KEY`, `_ENCRYPT_CACHE` читаются/пишутся из разных потоков без блокировки.

**Требование к реализации:**

1. Создать `threading.RLock()` — `_crypto_lock = threading.RLock()`
2. Все глобальные чтения/записи обернуть:
```python
def get_master_key():
    with _crypto_lock:
        return _MASTER_KEY
```

3. `rotate_master_key()` — весь метод под lock:
```python
def rotate_master_key(reencrypt_func):
    with _crypto_lock:
        ...
```

4. `set_passphrase()`, `clear_caches()`, `encrypt_value()`, `decrypt_value()` — защитить доступ к `_FERNET_INSTANCE`

5. `_ENCRYPT_CACHE` — заменить на `threading.Lock()` + dict или использовать `functools.lru_cache` с maxsize (она thread-safe в Python 3.12+)

**Внимание:** Не оборачивать весь `encrypt_value()`/`decrypt_value()` в lock — только критические секции (чтение/запись глобалов, кэша). Само шифрование Fernet не требует блокировки.

**Файлы для изменения:** `utils/crypto.py`
**Новые тесты:** `tests/test_crypto_thread_safety.py` — 2 теста

---

## 7. TOCTOU В XML ИМПОРТЕ (HIGH)

### 🟠 P1-13: Double file read — race condition

**Где:** `importers/xml_importer.py:33,53`
**Проблема:** XML читается дважды: defusedxml + lxml. Между чтениями файл может быть подменён.

**Требование к реализации:**

Переиспользовать распаршенное дерево:
```python
# Было:
tree = safe_parse_xml(file_path)
...
xml_doc = etree.parse(file_path, parser)  # Второе чтение!

# Стало:
tree = safe_parse_xml(file_path)
root = tree.getroot()
...
# Конвертируем ElementTree в строку и парсим lxml'ом
xml_bytes = etree.tostring(root)  # из stdlib, не нужно! Используем lxml
# Или просто сериализуем и парсим:
import io
xml_str = xml_bytes.decode('utf-8')
xml_doc = etree.fromstring(xml_str.encode('utf-8'), parser)
```

**Вариант проще:** совсем отказаться от второй парсинга и использовать `xml.etree.ElementTree` для XSD-валидации? Нет, XSD-валидация требует lxml. 

**Правильное решение:** сериализовать уже распаршенное defusedxml-дерево и отдать lxml:
```python
import io
xml_doc = etree.parse(io.BytesIO(etree.tostring(root)), parser)
```

**Файлы для изменения:** `importers/xml_importer.py`

---

## 8. БАГИ (HIGH)

### 🟠 P1-14: Bug — 3-tuple key vs 2-tuple unpack в error_report

**Где:** `importers/error_report.py:64`, `tabs/data_entry_tab.py`
**Проблема:** `duplicate_map` использует 3-tuple ключи `(hash, program, date)`, а `error_report.py` распаковывает как 2-tuple `snils, program = key`.

**Требование к реализации:**

1. В `tabs/data_entry_tab.py:_finalize_import()`:
```python
# Существующий код (строка ~740):
duplicate_map[existing_keys.get(key_hash)] = (key_hash, program, date) if isinstance(key, tuple) else ...
# или явно:
duplicate_map[key_hash] = (key_hash_program_date)  # 3-элементный tuple
```

2. В `error_report.py:_add_error_rows()`:
```python
# Исправить распаковку:
# Было:
for key, source_rows in duplicate_map.items():
    snils, program = key
# Стало:
for key_data, source_rows in duplicate_map.items():
    if isinstance(key_data, tuple) and len(key_data) == 3:
        key_hash, program, date = key_data
    elif isinstance(key_data, tuple) and len(key_data) == 2:
        key_hash, program = key_data
        date = ''
    else:
        key_hash, program, date = str(key_data), '', ''
```

3. Добавить type hints для `duplicate_map`:
```python
# Тип: Dict[Union[str, Tuple[str, str, str]], List[int]]
```

**Файлы для изменения:** `importers/error_report.py`, `tabs/data_entry_tab.py`

---

## 9. ДОКУМЕНТАЦИЯ (MEDIUM-HIGH)

### 🟡 P2-01: Добавить PRAGMA integrity_check при старте

**Где:** `db/database.py`
**Требование:** При создании первого соединения (или при запуске) выполнять `PRAGMA integrity_check`. При ошибке — логировать и показывать предупреждение.

**Реализация:**
```python
def _check_integrity(self):
    cursor = conn.execute("PRAGMA integrity_check")
    result = cursor.fetchone()
    if result and result[0] != 'ok':
        logger.critical("Database integrity check FAILED: %s", result)
        # show_exception_dialog или логировать
        log_audit("SECURITY_WARNING", f"Database integrity check failed: {result[0]}")
    else:
        logger.info("Database integrity check: OK")
```

**Файлы для изменения:** `db/database.py`

---

### 🟡 P2-02: Clipboard auto-clear

**Где:** `utils/auto_lock.py` или новый модуль `utils/clipboard.py`
**Требование:** При копировании через `QApplication.clipboard()` запускать таймер на 30 секунд, после которого очищать буфер обмена.

**Реализация:**
```python
class ClipboardGuard:
    _timer = None
    
    @classmethod
    def start(cls, timeout_ms=30000):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        cls._timer = QTimer()
        cls._timer.setSingleShot(True)
        cls._timer.timeout.connect(lambda: QApplication.clipboard().clear())
        QApplication.clipboard().dataChanged.connect(cls._timer.start(timeout_ms))
```

**Файлы для изменения:** `utils/auto_lock.py` (или новый `utils/clipboard_guard.py`) + подключение в `main.py`

---

### 🟡 P2-03: Confirmation dialog для TLS verify=False

**Где:** `tabs/data_transfer_tab.py`
**Требование:** При отключении `verify=True` в настройках прокси показывать confirmation dialog:
```
⚠️ ВНИМАНИЕ! Отключение проверки TLS-сертификата делает соединение
незащищённым от атак Man-in-the-Middle.

Вы подтверждаете отключение?
[Да] [Нет]
```

**Реализация:**
```python
def _on_tls_verify_toggled(self, checked):
    if not checked:
        reply = QMessageBox.warning(
            self, "Отключение TLS", 
            "Отключение проверки TLS-сертификата...\n\nВы подтверждаете?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            checkbox.setChecked(True)  # вернуть обратно
            return
    log_audit("TLS_WARNING", f"TLS verify set to {checked}")
```

**Файлы для изменения:** `tabs/data_transfer_tab.py`

---

### 🟡 P2-04: Retention policy (автоудаление по сроку хранения)

**Где:** `db/` + UI в `tabs/`
**Требование:**

1. Добавить настройку срока хранения в `org_settings.json`:
```json
{
  "retention_months": 60,  // 5 лет
  "retention_enabled": true
}
```

2. При старте приложения проверять:
   - Записи старше `retention_months` месяцев
   - Показывать диалог: "Найдено N записей старше срока хранения. Удалить?"
   - При подтверждении — удалять (с secure delete)

3. `EmployeeProgramsRepo` — метод `delete_older_than(months: int)`

4. Аудит: `log_audit("SECURITY_WARNING", f"Retention: deleted {count} records")`

**Файлы для изменения:** `db/employees_repo.py`, `db/employee_programs_repo.py`, `utils/constants.py`, UI

---

### 🟡 P2-05: Secure delete (перезапись перед удалением)

**Где:** `utils/secure_temp.py` (функция есть) + `db/employees_repo.py` (добавить)
**Требование:**

1. В `EmployeesRepo.delete()` и `EmployeesRepo.clear()`:
   - Прочитать зашифрованные значения ПДн
   - **Не расшифровывать** — просто перезаписать поля случайными байтами
   - UPDATE с random-данными
   - Затем DELETE

```python
def secure_delete(conn, table, id_field, id_value):
    # Перезаписать поля
    encrypted_fields = ['last_name_enc', 'first_name_enc', 'middle_name_enc', 'snils_enc']
    import os
    for field in encrypted_fields:
        conn.execute(f"UPDATE {table} SET {field} = ? WHERE {id_field} = ?",
                    (os.urandom(64), id_value))
    conn.execute(f"DELETE FROM {table} WHERE {id_field} = ?", (id_value,))
```

**Файлы для изменения:** `db/employees_repo.py`, `db/employee_programs_repo.py`

---

### 🟡 P2-06: ZIP backup — AES-256 (pyzipper)

**Где:** `utils/crypto.py:723-726`
**Требование:** Заменить `zipfile.ZipFile(setpassword)` на `pyzipper` с AES-256.

**Реализация:**
```python
try:
    import pyzipper
    with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED,
                              encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(backup_password.encode('utf-8'))
        zf.write(src_path, arcname=os.path.basename(src_path))
except ImportError:
    # Fallback на Fernet-шифрование файла перед zip
    ...
```

**Добавить `pyzipper` в `requirements.txt`**

**Файлы для изменения:** `utils/crypto.py`, `requirements.txt`

---

### 🟡 P2-07: Thread safety secure_temp

**Где:** `utils/secure_temp.py`
**Требование:** Добавить `threading.Lock()` для `get_secure_temp_dir()`:
```python
_secure_temp_lock = threading.Lock()

def get_secure_temp_dir():
    with _secure_temp_lock:
        if _secure_temp_dir is not None and os.path.exists(_secure_temp_dir):
            return _secure_temp_dir
        ...
```

**Файлы для изменения:** `utils/secure_temp.py`

---

### 🟡 P2-08: ACL — SE_DACL_PROTECTED

**Где:** `utils/secure_temp.py:44-46`
**Требование:** После создания DACL добавить защиту от наследования:
```python
sd.SetSecurityDescriptorControl(
    win32security.SE_DACL_PROTECTED,
    win32security.SE_DACL_PROTECTED
)
```

**Файлы для изменения:** `utils/secure_temp.py`

---

### 🟡 P2-09: safe_fromstring_xml без CountingTarget

**Где:** `utils/xml_safe.py:89-105`
**Требование:** Добавить element/depth limits для `safe_fromstring_xml()`:
```python
def safe_fromstring_xml(data):
    ...
    parser = XMLParser(target=CountingTarget(), forbid_dtd=True)
    return fromstring(data, parser=parser)
```

**Файлы для изменения:** `utils/xml_safe.py`

---

### 🟡 P2-10: Нет file path validation в xml_importer

**Где:** `importers/xml_importer.py`
**Требование:** Добавить нормализацию и валидацию пути:
```python
file_path = os.path.realpath(file_path)
# Проверка, что файл в допустимой директории
allowed_dirs = [tempfile.gettempdir(), os.path.expanduser("~")]
if not any(file_path.startswith(d) for d in allowed_dirs):
    # В production — логировать и отклонять
    pass
```

**Файлы для изменения:** `importers/xml_importer.py`

---

### 🟡 P2-11: XSD output validation отсутствует

**Где:** `exporters/xml_exporter.py`
**Требование:** Перед записью XML-файла валидировать его по XSD:
```python
if xsd_path and os.path.exists(xsd_path):
    try:
        schema_doc = etree.parse(xsd_path, secure_parser)
        schema = etree.XMLSchema(schema_doc)
        schema.assertValid(xml_doc)
    except etree.DocumentInvalid as e:
        log_audit("XML_VALIDATION_ERROR", f"Output XML invalid: {e}")
        raise
```

**Файлы для изменения:** `exporters/xml_exporter.py`

---

### 🟡 P2-12: Control chars в XML output

**Где:** `exporters/xml_exporter.py:169-176`
**Требование:** В `_escape_xml()` добавить фильтрацию control characters (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F), кроме разрешённых (tab, CR, LF):
```python
_ILLEGAL_XML_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
def _escape_xml(s):
    s = _ILLEGAL_XML_CHARS.sub('', s)
    s = s.replace('&', '&amp;').replace('<', '&lt;')...
```

**Файлы для изменения:** `exporters/xml_exporter.py`

---

### 🟡 P2-13: XLSX extension case-sensitive

**Где:** `importers/xlsx_importer.py:245`
**Требование:** Заменить:
```python
if not file_path.endswith('.xlsx'):
# на:
if not file_path.lower().endswith('.xlsx'):
```

**Файлы для изменения:** `importers/xlsx_importer.py`

---

### 🟡 P2-14: DatabaseLockError dead code

**Где:** `db/database.py:108-109`
**Требование:** Исправить `transaction()` — убрать `continue` в цикле retry, чтобы `DatabaseLockError` реально выбрасывался.

```python
def transaction():
    for attempt in range(_BUSY_RETRIES):
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield
            conn.commit()
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < _BUSY_RETRIES - 1:
                time.sleep(0.1)
                continue
            else:
                raise DatabaseLockError(...)  # <-- убрать re-raise
    raise DatabaseLockError(...)  # <-- сюда дойдём после всех попыток
```

**Файлы для изменения:** `db/database.py`

---

### 🟡 P2-15: No audit events for export operations

**Где:** `exporters/xml_exporter.py`, `tabs/data_entry_tab.py`
**Требование:** Уже описано в P1-06 (пункты 5-6). Дополнительно — добавить audit для:
- Экспорт XLSX из `data_view_tab.py`
- Экспорт протокола из `protocol_tab.py`

**Файлы для изменения:** См. P1-06

---

### 🟡 P2-16: No PII warning on XLSX/XML export

**Где:** UI `tabs/`
**Требование:** При экспорте XLSX/XML показывать предупреждение:
```
⚠️ Файл будет содержать персональные данные (ФИО, СНИЛС).
Убедитесь, что файл сохраняется на зашифрованном диске (BitLocker).
```

**Файлы для изменения:** `tabs/data_entry_tab.py`, `tabs/employee_summary_tab.py`

---

### 🟡 P2-17: org_settings.json без HMAC integrity

**Где:** `utils/crypto.py` (функции `save_data`/`load_data`)
**Требование:** При сохранении `org_settings.json` добавить HMAC tag (аналогично `master.key.json`).

**Файлы для изменения:** `utils/crypto.py`

---

## 10. LOW (P3)

### 🟢 P3-01: Position (должность) в plaintext

**Где:** `db/employees_repo.py`
**Требование (опционально):** Добавить поле `position_enc` и шифровать его Fernet. Миграция: при запуске проверять наличие поля, если нет — создать, перешифровать.

**Приоритет:** Низкий (должность не ПДн, но рекомендуется)

---

### 🟢 P3-02: mask_sensitive() — 8/11 SNILS visible

**Где:** `utils/logger.py:109-115`
**Требование:** Улучшить маскировку: показать `12*******00` (2+2) вместо `1234***8901` (4+4).

**Файлы для изменения:** `utils/logger.py`

---

### 🟢 P3-03: Duplicate size constants

**Где:** `importers/xml_importer.py:14`, `utils/xml_safe.py:21`
**Требование:** Использовать единый источник истины:
```python
# В utils/constants.py:
MAX_XML_FILE_SIZE_BYTES = 100 * 1024 * 1024
# В xml_importer.py:
from utils.constants import MAX_XML_FILE_SIZE_BYTES
```

**Файлы для изменения:** `utils/constants.py`, `importers/xml_importer.py`, `utils/xml_safe.py`

---

### 🟢 P3-04: str(data) fallback в safe_fromstring_xml

**Где:** `utils/xml_safe.py:93`
**Требование:** Заменить:
```python
data = data.decode("utf-8") if isinstance(data, bytes) else str(data)
# на:
if isinstance(data, bytes):
    data = data.decode("utf-8")
elif not isinstance(data, str):
    raise TypeError(f"Expected str or bytes, got {type(data).__name__}")
```

**Файлы для изменения:** `utils/xml_safe.py`

---

### 🟢 P3-05: No log injection protection

**Где:** `utils/logger.py:SensitiveDataFilter`
**Требование:** В начале `filter()` добавить удаление control chars:
```python
record.msg = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', record.msg)
```

**Файлы для изменения:** `utils/logger.py`

---

### 🟢 P3-06: File path in log output

**Где:** `importers/xlsx_importer.py:250-251`
**Требование:** Маскировать или обрезать путь:
```python
logger.info("Loading XLSX: ... (%s, %.1f MB)",
            os.path.basename(file_path), size_mb)
```

**Файлы для изменения:** `importers/xlsx_importer.py`

---

## 11. ОРГАНИЗАЦИОННЫЕ МЕРЫ (НЕ В КОДЕ)

| ID | Мера | Ответственный | Приоритет |
|----|------|---------------|-----------|
| O-01 | Назначить ответственного за обработку ПДн (приказ) | Руководитель организации | IMMEDIATE |
| O-02 | Утвердить Политику обработки ПДн (ст. 18.1 152-ФЗ) | Руководитель / Юрист | IMMEDIATE |
| O-03 | Уведомить Роскомнадзор об обработке ПДн (форма 4-ПДн) | Ответственный за ПДн | IMMEDIATE |
| O-04 | Включить BitLocker на ПК оператора | Системный администратор | IMMEDIATE |
| O-05 | Установить/проверить антивирус (Microsoft Defender) | Системный администратор | IMMEDIATE |
| O-06 | Установить `EXCEL_XML_PROD=1` в переменные окружения | Системный администратор | IMMEDIATE |
| O-07 | Издать приказ о вводе ИСПДн в эксплуатацию | Руководитель | HIGH |
| O-08 | Ограничить физический доступ к ПК оператора | Руководитель | HIGH |
| O-09 | Настроить Windows Defender Firewall (только edu.rosmintrud.ru) | Системный администратор | HIGH |
| O-10 | Провести инструктаж оператора по работе с ПДн | Ответственный за ПДн | HIGH |
| O-11 | Утвердить регламент резервного копирования | Ответственный за ПДн | HIGH |
| O-12 | Утвердить план реагирования на инциденты | Ответственный за ПДн | MEDIUM |
| O-13 | Настроить Screen Lock (5 минут, пароль) | Системный администратор | MEDIUM |
| O-14 | Ознакомить работников с обработкой ПДн (уведомление) | Ответственный за ПДн | MEDIUM |

---

## 12. ПЛАН-ГРАФИК РАБОТ (8 НЕДЕЛЬ)

| Неделя | Задачи | Ожидаемый результат |
|--------|--------|---------------------|
| 1-2 | P0-01, P0-02, P1-01, P1-05, P1-08, P1-09 | Исправлены критические和高 приоритетные flaws |
| 2-3 | P1-06 (все 17 событий), P1-07, P1-14 | Полноценный audit trail |
| 3-4 | P1-02, P1-03, P1-04, P1-11, P1-12, P1-13 | Memory safety, thread safety, утечки ПДн |
| 4-5 | P2-01...P2-10 | integrity_check, clipboard, TLS dialog, retention, secure delete |
| 5-6 | P2-11...P2-17 | XML output validation, AES-256, ACL, Security PII warnings |
| 6-7 | P3-01...P3-06 | Low priority fixes |
| 7-8 | Тестирование, регрессия, документирование | 337 тестов pass + новые тесты |

---

## 13. КРИТЕРИИ ГОТОВНОСТИ (Definition of Done)

1. Все 🔴 P0 и 🟠 P1 задачи выполнены
2. Все тесты проходят: `py -m pytest tests -v` (337 + новые ≥ 350)
3. Audit.log содержит HMAC-теги длиной 64 символа
4. `verify_audit_log()` работает и интегрирована в UI
5. В audit.log присутствуют все 34 события
6. XLSX/XML импорт не содержит raw SNILS в error messages
7. `EXCEL_XML_PROD=1` не выдаёт ошибок
8. Нет f-string логов с ПДн (grep по коду)
9. Secure temp использует SE_DACL_PROTECTED
10. Crypto module thread-safe (тест race condition)
11. Backup ZIP использует AES-256 или Fernet
12. Код не содержит hardcoded secrets (grep по source)
13. В LogViewerDialog есть кнопка "Проверить integrity audit"

---

## 14. ТЕСТИРОВАНИЕ

### Новые тесты (минимум 20)

| Модуль | Тесты | Описание |
|--------|-------|----------|
| `test_audit_verification.py` | 5 | verify_audit_log, hash chaining, HMAC tag length |
| `test_crypto_thread_safety.py` | 3 | Concurrent encrypt, concurrent rotate, memory zero |
| `test_logger_audit.py` (доп) | 3 | XML pattern, JSON numeric, control chars |
| `test_secure_temp.py` | 3 | SE_DACL_PROTECTED, thread safety, cleanup |
| `test_integrity.py` | 3 | PRAGMA integrity_check, backup integrity |
| `test_retention.py` | 3 | Delete older than, retention config |

### Регрессия

```bash
# После каждого раунда:
py -m pytest tests -v --tb=short
```

---

*Документ обновлён: 22.05.2026*
*Версия приложения: 3.1.0*
*Автор: Senior AppSec Engineer*

В конце - поменять версию приложения во всех источниках, в т.ч. отображаемую в программе
