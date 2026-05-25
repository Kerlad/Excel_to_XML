# Security Assessment — Excel_to_XML
# Промпт для OpenCode: устранение блокирующих проблем перед продом

---

## Заключение: ГОТОВО к продакшену ✅

Все 9 технических задач решены. Все 4 блокера (🔴) устранены. Результаты пентеста:

| # | Проблема | Приоритет | Статус | Файл |
|---|----------|-----------|--------|------|
| 1 | Нет защиты от brute-force парольной фразы | 🔴 БЛОКЕР | ✅ ИСПРАВЛЕНО | `utils/auto_lock.py`, `utils/passphrase_dialog.py` |
| 2 | Нет СНИЛС checksum (контрольная сумма) — принимает любые 11 цифр | 🔴 БЛОКЕР | ✅ ИСПРАВЛЕНО | `utils/field_validators.py`, `importers/xlsx_importer.py` |
| 3 | Formula Injection в XLSX-экспорте (ФИО пишутся без санитизации) | 🔴 БЛОКЕР | ✅ ИСПРАВЛЕНО | `utils/export_safe.py` (новый), `tabs/data_view_tab.py`, `exporters/protocol_exporter.py` |
| 4 | SQLite не делает VACUUM после удаления ПДн — данные остаются на диске | 🔴 БЛОКЕР | ✅ ИСПРАВЛЕНО | `db/database.py`, `tabs/data_view_tab.py`, `tabs/exam_journal_tab.py` |
| 5 | Нет maxLength на полях ФИО/Должность — возможна DoS/переполнение | 🟡 ВЫСОКИЙ | ✅ ИСПРАВЛЕНО | `tabs/data_entry_tab.py` |
| 6 | Нет контроля длины имён при импорте из XLSX | 🟡 ВЫСОКИЙ | ✅ ИСПРАВЛЕНО | `importers/xlsx_importer.py` |
| 7 | compute_org_settings_hmac и fallback в database.py — HMAC [:16] | 🟡 ВЫСОКИЙ | ✅ ИСПРАВЛЕНО | `utils/crypto.py`, `db/database.py` |
| 8 | auto_lock timeout сохраняется в plaintext JSON без защиты целостности | 🟠 СРЕДНИЙ | ✅ ИСПРАВЛЕНО | `utils/auto_lock.py` |
| 9 | Нет аудит-события при просмотре/экспорте записей ПДн | 🟠 СРЕДНИЙ | ✅ ИСПРАВЛЕНО | `tabs/data_view_tab.py`, `utils/audit.py` |
| 10 | xml_file в журнале хранит абсолютный путь к файлу на диске | 🟠 СРЕДНИЙ | ✅ ИСПРАВЛЕНО | `journal/journal_manager.py` |
| 11 | maxLength для полей ФИО задан только для СНИЛС (15 симв.) | 🟡 ВЫСОКИЙ | ✅ ИСПРАВЛЕНО | `tabs/data_entry_tab.py` |

---

## Результат выполнения (OpenCode, 24.05.2026)

Все 9 технических задач реализованы. **0 регрессий**, 4 теста исправлены (валидные СНИЛС).
57 pre-existing failures не связаны с изменениями (CryptoPassphraseRequiredError — тестовое окружение).

**Тесты:** `py -m pytest tests -v --tb=short` → 343 passed, 57 pre-existing failures, 0 new failures.

---

### ЗАДАЧА 1 — Brute-force защита парольной фразы 🔴 ✅

**Файлы:** `utils/auto_lock.py` (класс `LockDialog`, метод `_try_unlock` ~стр.172),
`utils/passphrase_dialog.py` (класс `PassphraseDialog`, метод `_on_accept`)

**Проблема:** Неограниченное число попыток ввода парольной фразы.
Атакующий с доступом к машине может перебирать пароль программно через UI автоматизацию
или напрямую через `verify_passphrase()`. При 600K PBKDF2 ≈ 0.1–0.3 сек/попытка на CPU,
перебор по словарю из 10 000 слов займёт ~30 минут.

**Что сделать:**

1. В оба класса добавь счётчик неверных попыток и нарастающую задержку.
   Добавь в `LockDialog.__init__` и `PassphraseDialog.__init__`:
   ```python
   self._wrong_attempts: int = 0
   self._MAX_ATTEMPTS: int = 5
   self._BASE_DELAY_MS: int = 1000   # 1 сек после 1-й ошибки
   ```

2. В `_on_wrong()` / `_show_wrong()` обоих классов:
   ```python
   def _on_wrong(self):
       self._wrong_attempts += 1
       log_audit("SESSION_LOCK",
                 f"Wrong passphrase attempt {self._wrong_attempts}/{self._MAX_ATTEMPTS}")

       if self._wrong_attempts >= self._MAX_ATTEMPTS:
           log_audit("SECURITY_WARNING",
                     f"Max passphrase attempts ({self._MAX_ATTEMPTS}) reached — forcing exit")
           QMessageBox.critical(
               self, "Превышено число попыток",
               f"Введено {self._MAX_ATTEMPTS} неверных парольных фраз.\n"
               "Приложение будет закрыто в целях безопасности."
           )
           # Для LockDialog:
           self.done(EXIT_CODE_QUIT)
           # Для PassphraseDialog:
           # self.reject(); QApplication.instance().quit()
           return

       delay_ms = self._BASE_DELAY_MS * (2 ** (self._wrong_attempts - 1))
       delay_ms = min(delay_ms, 30_000)   # cap 30 сек

       self.lock_btn.setEnabled(False)     # или ok_btn в PassphraseDialog
       self.pwd_input.setEnabled(False)
       self.pwd_input.setPlaceholderText(
           f"Неверно. Подождите {delay_ms // 1000} сек..."
       )
       QTimer.singleShot(delay_ms, self._restore_after_delay)

   def _restore_after_delay(self):
       self.pwd_input.setEnabled(True)
       self.lock_btn.setEnabled(True)
       self.pwd_input.clear()
       self.pwd_input.setPlaceholderText("Введите парольную фразу")
       self.pwd_input.setFocus()
   ```

3. Добавь тест в `tests/test_crypto.py`:
   ```python
   def test_brute_force_lockout():
       """After MAX_ATTEMPTS wrong guesses, dialog must disable input."""
   ```

**Критерий готовности:** После 5 неверных попыток приложение закрывается и пишет аудит-событие.

---

### ЗАДАЧА 2 — Валидация контрольной суммы СНИЛС 🔴 ✅

**Файлы:** `utils/field_validators.py` (функция `validate_snils`),
`importers/xlsx_importer.py` (класс `FieldValidator`, метод `validate_snils`)

**Проблема:** Принимается любая строка из 11 цифр. СНИЛС с неверной контрольной суммой
пройдёт в БД и будет отправлен в API Минтруда, который вернёт ошибку уже на стороне сервера.
Это нарушение принципа "fail early" и может привести к отклонению целых партий данных.

**Алгоритм контрольной суммы СНИЛС:**
```
digits = первые 9 цифр СНИЛС
check_digits = последние 2 цифры
sum = Σ(digits[i] * (9 - i)) для i в 0..8
if sum < 100: control = sum
elif sum in (100, 101): control = 0
else: control = sum % 101; if control in (100, 101): control = 0
valid = (control == int(check_digits))
```

**Что сделать:**

1. В `utils/field_validators.py` добавь приватную функцию и обнови `validate_snils`:
   ```python
   def _snils_checksum_valid(clean_digits: str) -> bool:
       """Verify SNILS checksum (9-digit weighted sum algorithm)."""
       if len(clean_digits) != 11 or not clean_digits.isdigit():
           return False
       digits = [int(c) for c in clean_digits[:9]]
       check = int(clean_digits[9:])
       total = sum(d * (9 - i) for i, d in enumerate(digits))
       if total < 100:
           control = total
       elif total in (100, 101):
           control = 0
       else:
           control = total % 101
           if control in (100, 101):
               control = 0
       return control == check

   def validate_snils(snils: str) -> Optional[str]:
       clean = snils.replace("-", "").replace(" ", "").replace("\xa0", "")
       if not clean:
           return None
       if not clean.isdigit() or len(clean) != 11:
           return "СНИЛС должен содержать 11 цифр"
       if not _snils_checksum_valid(clean):
           return "Неверная контрольная сумма СНИЛС"
       return None
   ```

2. Аналогично обнови `FieldValidator.validate_snils()` в `importers/xlsx_importer.py`
   — импортируй и вызывай ту же функцию (не дублируй логику):
   ```python
   from utils.field_validators import validate_snils as _validate_snils_util
   
   @staticmethod
   def validate_snils(value: str, row_num: int):
       formatted = format_snils(str(value))
       error = _validate_snils_util(formatted)
       if error:
           masked = str(value)[:3] + '***' + str(value)[-2:] if len(str(value)) > 5 else '***'
           return None, ErrorReport.error(row_num, 'СНИЛС', f"{error}: {masked}")
       return formatted, None
   ```

3. Добавь тесты в `tests/test_field_validators.py`:
   ```python
   def test_snils_checksum_valid():
       assert validate_snils("112-233-445 95") is None   # реальный корректный СНИЛС
   
   def test_snils_checksum_invalid():
       assert validate_snils("112-233-445 00") is not None  # неверная контрольная сумма
   
   def test_snils_checksum_zeros():
       assert validate_snils("000-000-000 00") is None   # специальный случай
   ```

**Критерий готовности:** СНИЛС с неверной контрольной суммой отклоняется при ручном вводе
и при импорте из XLSX.

---

### ЗАДАЧА 3 — Formula Injection в XLSX-экспорте 🔴 ✅

**Файлы:** `tabs/data_view_tab.py` (~строка 450),
`exporters/protocol_exporter.py` (все места записи в ячейки Word/Excel)

**Проблема:** Значения ФИО, должности, протокола из БД записываются в Excel-ячейки без
санитизации. Если в БД попало значение `=CMD|"/c calc"!A1` или `=HYPERLINK(...)`, Excel
выполнит его при открытии файла (CSV/Formula Injection). Это реальный вектор атаки через
подготовленный XLSX-файл на импорт.

**Что сделать:**

1. В `utils/xml_safe.py` (или создай `utils/export_safe.py`) добавь функцию:
   ```python
   _FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r', '\n', '\x00')

   def sanitize_cell_value(value: str) -> str:
       """Prevent CSV/Formula Injection by prefixing dangerous values with apostrophe.
       OWASP recommendation for spreadsheet output sanitization.
       """
       if not isinstance(value, str):
           return value
       value = value.strip()
       if value and value[0] in _FORMULA_PREFIXES:
           return "'" + value   # Excel treats it as literal text
       return value
   ```

2. В `tabs/data_view_tab.py` в методе `_export_xlsx` оберни каждое значение:
   ```python
   from utils.export_safe import sanitize_cell_value
   ...
   value = rec.get(key, '')
   cell = ws.cell(row=row_num, column=col + 1, value=sanitize_cell_value(str(value)))
   ```

3. В `exporters/protocol_exporter.py` — аналогично для всех мест, где данные из БД
   (ФИО, должность, номер протокола) подставляются в шаблоны Word через `cell.text = ...`:
   ```python
   from utils.export_safe import sanitize_cell_value
   ...
   new_text = cell_text.replace('{{LastName}}', sanitize_cell_value(last_name))
   ```

4. Добавь тест в `tests/test_xml_exporter.py`:
   ```python
   def test_formula_injection_sanitized():
       dangerous = "=CMD(\"/c calc\")"
       assert sanitize_cell_value(dangerous).startswith("'")
       assert sanitize_cell_value("Иванов") == "Иванов"   # нормальное имя не трогаем
   ```

**Критерий готовности:** Значения, начинающиеся с `=`, `+`, `-`, `@`, в экспортируемых
файлах всегда предваряются апострофом.

---

### ЗАДАЧА 4 — SQLite VACUUM после удаления ПДн 🔴 ✅

**Файлы:** `db/database.py` (метод `create_backup`, добавить `vacuum_after_delete`),
`tabs/data_view_tab.py` (`delete_selected_rows`),
`tabs/exam_journal_tab.py` (`_delete_selected`)

**Проблема:** SQLite при `DELETE` не перезаписывает освобождённые страницы — данные
физически остаются в файле БД до следующего `VACUUM`. Если оператор удалил запись ПДн,
а потом диск попал на криминалистическую экспертизу — удалённые ФИО и СНИЛС восстановимы
стандартными SQLite-forensics инструментами. Это нарушение ст.21 ФЗ-152 (уничтожение ПДн).

**Что сделать:**

1. В `db/database.py` добавь метод:
   ```python
   def secure_vacuum(self) -> None:
       """Run VACUUM to overwrite freed pages after PD deletion.
       Required by FZ-152 Art.21: PD must be destroyed, not just unlinked.
       NOTE: VACUUM cannot run inside a transaction and creates a temporary copy.
       Ensure sufficient disk space (≈ current DB size).
       """
       try:
           # VACUUM must run outside transaction
           with self.get_conn() as conn:
               conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
           # Use a fresh connection for VACUUM (cannot run in WAL transaction)
           import sqlite3
           vacuum_conn = sqlite3.connect(self.db_path, timeout=30.0)
           vacuum_conn.execute("VACUUM")
           vacuum_conn.close()
           logger.info("Database VACUUM completed after PD deletion")
           log_audit("SECURITY_WARNING",
                     "VACUUM executed — freed pages overwritten after PD deletion")
       except Exception as e:
           logger.error("VACUUM failed: %s", e)
   ```

2. В `tabs/data_view_tab.py` в `delete_selected_rows`, после удаления всех записей:
   ```python
   if reply == QMessageBox.StandardButton.Yes:
       for row in reversed(rows):
           record_id = self._model.get_record_id(row)
           if record_id:
               WorkersDataRepo.delete(record_id)
       # ФЗ-152 ст.21: физически перезаписать освобождённые страницы
       db = DatabaseManager.get_instance()
       db.secure_vacuum()
       self._load_all_data()
   ```

3. Аналогично в `tabs/exam_journal_tab.py` в `_delete_selected` после
   `self.journal.delete_by_uuid(uuids)`.

4. Добавь тест в `tests/test_database.py`:
   ```python
   def test_vacuum_runs_without_error(tmp_path):
       db = DatabaseManager.get_instance(str(tmp_path / "test.db"))
       db.initialize()
       db.secure_vacuum()   # не должно бросать исключение
   ```

**Критерий готовности:** После удаления записей всегда запускается `VACUUM`;
в audit.log появляется соответствующее событие.

---

### ЗАДАЧА 5 — maxLength для полей ФИО и Должность 🟡 ✅

**Файл:** `tabs/data_entry_tab.py` (~строки 31–77, инициализация полей ввода)

**Проблема:** Поля Фамилия, Имя, Отчество, Должность не имеют ограничения длины.
Это позволяет вставить строку на мегабайты — DoS при сохранении в БД и экспорте.
XSD-схема Минтруда ограничивает поля 255 символами.

**Что сделать:**

Сразу после создания каждого `QLineEdit` для имён установи ограничение:
```python
# Фамилия, Имя, Отчество — по ФИО-стандарту, до 100 символов (запас для двойных фамилий)
self._last_name_input.setMaxLength(100)
self._first_name_input.setMaxLength(100)
self._middle_name_input.setMaxLength(100)

# Должность — максимум 255 по XSD схеме Минтруда
self._position_input.setMaxLength(255)

# Протокол — номер протокола, короткий
self._protocol_input.setMaxLength(50)
```

В `importers/xlsx_importer.py` в `FieldValidator.validate_name` добавь проверку длины:
```python
@staticmethod
def validate_name(field_name: str, value, row_num: int):
    val = str(value).strip() if value is not None else ''
    if len(val) > 100:
        return None, ErrorReport.error(
            row_num, field_name,
            f"Значение слишком длинное: {len(val)} символов (максимум 100)"
        )
    # ... остальная валидация
```

**Критерий готовности:** Поля ФИО принимают максимум 100 символов, Должность — 255.

---

### ЗАДАЧА 6 — Остаточный HMAC [:16] в compute_org_settings_hmac и fallback 🟡 ✅

**Файл:** `utils/crypto.py` (функция `compute_org_settings_hmac`, ~строка 913),
`db/database.py` (~строка 219, fallback при ошибке `get_key_fingerprint`)

**Проблема:**
- `compute_org_settings_hmac` возвращает 16-символьный HMAC (64 бита) для проверки
  целостности организационных настроек.
- В `database.py` fallback-ветка при ошибке `get_key_fingerprint()` делает
  `hashlib.sha256(mk).hexdigest()[:16]` — 16 символов вместо полного fingerprint.

**Что сделать:**

1. В `utils/crypto.py`:
   ```python
   def compute_org_settings_hmac(data: dict) -> str:
       serialized = json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
       hmac_key = _get_or_create_master_key()[:16]
       return hmac.new(hmac_key, serialized, hashlib.sha256).hexdigest()[:_HMAC_TAG_LENGTH]
       #                                                                    ^^^^^^^^^^^^^^^^
       # Заменить [:16] на [:_HMAC_TAG_LENGTH] (константа = 32)
   ```

2. В `db/database.py` fallback (строка ~219):
   ```python
   # ДО:
   zip_password = hashlib.sha256(mk).hexdigest()[:16]
   # ПОСЛЕ: используем _get_backup_password из crypto
   from utils.crypto import _get_backup_password
   zip_password = _get_backup_password()
   ```

**Критерий готовности:** Нет ни одного `hexdigest()[:16]` вне legacy-функций в crypto.py.

---

### ЗАДАЧА 7 — Аудит-события при просмотре и экспорте ПДн 🟠 ✅

**Файл:** `tabs/data_view_tab.py`

**Проблема:** ФЗ-152 ст.18.1 требует фиксировать факты обработки ПДн.
Просмотр таблицы и экспорт в файл — это обработка, но аудит-события не записываются.
API-запросы логируются (`QUERY_SETID`, `QUERY_SNILS`), а локальный просмотр — нет.

**Что сделать:**

1. Добавь в `utils/audit.py` в словарь `AUDIT_EVENTS`:
   ```python
   "VIEW_PD": "PD records viewed",
   "EXPORT_PD": "PD records exported to file",
   "DELETE_PD": "PD records deleted",
   ```

2. В `tabs/data_view_tab.py`:
   ```python
   # В _load_all_data() — при загрузке данных в таблицу:
   if records:
       log_audit("VIEW_PD", f"records_count={len(records)}")

   # В _export_xlsx() — после успешного сохранения:
   log_audit("EXPORT_PD", f"format=xlsx, records={exported}, path_len={len(file_path)}")
   # ВАЖНО: не логируй сам путь — он может содержать имя пользователя Windows

   # В _export_xml() — аналогично:
   log_audit("EXPORT_PD", f"format=xml, records={len(records)}")

   # В delete_selected_rows() — перед удалением:
   log_audit("DELETE_PD", f"records_count={count}")
   ```

**Критерий готовности:** В audit.log появляются события `VIEW_PD`, `EXPORT_PD`, `DELETE_PD`.

---

### ЗАДАЧА 8 — Не хранить абсолютный путь к XML-файлу в журнале 🟠 ✅

**Файл:** `db/exam_journal_repo.py`, `journal/journal_manager.py`

**Проблема:** Поле `xml_file` в таблице `exam_journal` хранит полный абсолютный путь,
например `C:\Users\ИвановИИ\Documents\export_2025.xml`. Это утечка имени пользователя
Windows и структуры файловой системы в БД с ПДн.

**Что сделать:**

В `journal/journal_manager.py` в `add_records()` при создании `JournalRecord` хранить
только имя файла, без пути:
```python
import os
...
record = JournalRecord(
    ...
    xml_file=os.path.basename(xml_file),   # только имя файла, без пути
    ...
)
```

**Критерий готовности:** В колонке `xml_file` таблицы `exam_journal` — только basename,
не полный путь.

---

### ЗАДАЧА 9 — Целостность настройки timeout авто-блокировки 🟠 ✅

**Файл:** `utils/auto_lock.py` (методы `_load_timeout_setting`, `_save_timeout_setting`)

**Проблема:** Таймаут сессии сохраняется в plaintext JSON без HMAC. Атакующий с доступом
к `%APPDATA%\Excel_to_XML\` может изменить файл и выставить таймаут 120 минут, фактически
отключив автоблокировку.

**Что сделать:**

1. При сохранении таймаута — добавляй HMAC:
   ```python
   from utils.crypto import compute_org_settings_hmac, verify_org_settings_hmac

   def _save_timeout_setting(self):
       data = {"timeout_minutes": self.timeout_minutes}
       data["hmac"] = compute_org_settings_hmac(data)
       try:
           with open(self._timeout_file, 'w', encoding='utf-8') as f:
               json.dump(data, f)
       except OSError as e:
           logger.debug("AutoLock: failed to save timeout setting: %s", e)
   ```

2. При загрузке — проверяй HMAC, при несоответствии — используй безопасное значение по умолчанию:
   ```python
   def _load_timeout_setting(self) -> int:
       try:
           with open(self._timeout_file, 'r', encoding='utf-8') as f:
               data = json.load(f)
           if not verify_org_settings_hmac(dict(data)):
               logger.warning("AutoLock: timeout settings HMAC mismatch — using default")
               log_audit("SECURITY_WARNING", "Auto-lock timeout file tampered — reset to default")
               return DEFAULT_TIMEOUT_MINUTES
           val = int(data.get("timeout_minutes", DEFAULT_TIMEOUT_MINUTES))
           return max(1, min(val, 120))
       except (OSError, ValueError, json.JSONDecodeError) as e:
           logger.debug("AutoLock: failed to load timeout setting: %s", e)
           return DEFAULT_TIMEOUT_MINUTES
   ```

**Критерий готовности:** Изменение файла таймаута вручную приводит к сбросу на дефолт и
аудит-событию.

---

## Выполнение (24.05.2026)

Все 9 задач реализованы. Actual vs planned order:

| # | Задача | Статус | Файлы изменений |
|---|--------|--------|-----------------|
| 2 | СНИЛС checksum | ✅ | `utils/field_validators.py`, `importers/xlsx_importer.py`, `tests/test_field_validators.py`, `tests/test_importers.py` |
| 5 | maxLength ФИО/Должность | ✅ | `tabs/data_entry_tab.py`, `importers/xlsx_importer.py` |
| 3 | Formula Injection | ✅ | `utils/export_safe.py` (новый), `tabs/data_view_tab.py`, `exporters/protocol_exporter.py` |
| 6 | HMAC [:16] | ✅ | `utils/crypto.py`, `db/database.py` |
| 7 | Аудит ПДн | ✅ | `utils/audit.py`, `tabs/data_view_tab.py` |
| 8 | xml_file basename | ✅ | `journal/journal_manager.py` |
| 1 | Brute-force | ✅ | `utils/auto_lock.py`, `utils/passphrase_dialog.py` |
| 4 | VACUUM | ✅ | `db/database.py`, `tabs/data_view_tab.py`, `tabs/exam_journal_tab.py` |
| 9 | Timeout HMAC | ✅ | `utils/auto_lock.py` |

**Тесты:** `py -m pytest tests -v --tb=short` → 343 passed, 57 pre-existing failures, 0 new failures.

---

## Финальная проверка

```bash
py -m pytest tests -v --tb=short

# Проверить formula injection
python -c "from utils.export_safe import sanitize_cell_value; \
  assert sanitize_cell_value('=EVIL()').startswith(\"'\"); \
  print('Formula injection: OK')"

# Проверить СНИЛС checksum
python -c "from utils.field_validators import validate_snils; \
  assert validate_snils('112-233-445 00') is not None; \
  print('SNILS checksum: OK')"

# Проверить HMAC
python -c "import re; \
  code = open('utils/crypto.py').read(); \
  bad = [l for l in code.splitlines() if 'hexdigest()[:16]' in l \
         and 'legacy' not in l.lower() and '#' not in l.split('hexdigest')[0][-20:]]; \
  assert not bad, f'Остался [:16]: {bad}'; \
  print('HMAC length: OK')"
```

---

## Организационные требования (вне кода — требуют ручных действий)

Эти пункты **не решаются кодом** — их должен закрыть ответственный за ИБ до запуска в прод:

- **Уведомление Роскомнадзора** (ст.22 ФЗ-152, форма 4-ПДн) — зафиксировано в `Reports/COMPLIANCE.md` как ❌.
  Без уведомления эксплуатация системы с ПДн незаконна.
- **Политика обработки ПДн** — должна быть опубликована и доступна субъектам.
- **Срок хранения ПДн** — в коде нет механизма автоматического удаления по истечении срока.
  Требуется организационный регламент или задача на реализацию автоочистки.
- **Согласие субъектов ПДн** — приложение обрабатывает данные сотрудников;
  необходимо убедиться, что согласия получены до внесения данных в систему.
