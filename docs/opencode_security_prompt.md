# Security Fix Prompt — Excel_to_XML (OpenCode / Claude Code)

## Контекст задачи

Ты — security engineer, работающий над Python-приложением **Excel_to_XML** (PySide6, SQLite, cryptography/Fernet, pywin32).
Приложение обрабатывает персональные данные сотрудников (ФИО, СНИЛС) согласно ФЗ-152 и передаёт их в API Минтруда РФ.
Перед тобой — шесть конкретных уязвимостей. Твоя задача: исправить каждую, не сломав существующие тесты и не нарушив архитектурные правила из `AGENTS.md`.

---

## Обязательные правила (из AGENTS.md — не нарушать!)

- Все SQL-запросы — только параметризованные, никакой конкатенации строк.
- Все XML из внешних источников — только через `utils.xml_safe.safe_parse_xml()`.
- Логирование чувствительных данных — только через `filter_sensitive_text()` или `%s`-форматирование с `SensitiveDataFilter`.
- Никаких захардкоженных секретов.
- `TLS verify=True` по умолчанию; отключение — только с аудит-событием `TLS_WARNING`.
- Проверяй тесты после каждого изменения: `py -m pytest tests -v`

---

## Задачи (выполнять по очереди, каждую — отдельным коммитом)

---

### ЗАДАЧА 1 — Устранить in-memory кэш расшифрованных ПДн

**Файл:** `utils/crypto.py`

**Проблема:**
```python
_ENCRYPT_CACHE: Dict[str, str] = {}   # строки 36 и 560–577
_MAX_CACHE_ITEMS: int = 2000
```
Словарь хранит до 2000 пар `{шифртекст: plaintext}`. При дампе памяти процесса (crash dump, hibernation, cold boot attack) — все закэшированные ФИО и СНИЛС читаются в открытом виде. Это прямое нарушение принципа минимизации данных (ФЗ-152, ст. 5).

**Что сделать:**

1. Полностью удали `_ENCRYPT_CACHE`, `_MAX_CACHE_ITEMS` и все обращения к ним в функциях `encrypt_value()` и `decrypt_value()`.

2. Если нужен кэш для производительности (например, для полей типа `position`, `employer_inn`, которые не являются ПДн) — реализуй **отдельный кэш только для не-ПДн полей** через параметр:
   ```python
   def decrypt_value(enc: str, cache_ok: bool = False) -> str:
       ...
   ```
   При `cache_ok=False` (по умолчанию) — кэш не используется никогда. Это должно быть поведение для всех ФИО/СНИЛС полей.

3. Убедись, что `clear_caches()` продолжает работать корректно (там сейчас вызывается `_ENCRYPT_CACHE.clear()`).

4. Обнови тест `tests/test_cache.py` — убери тесты, проверяющие кэширование ПДн, добавь тест, подтверждающий что повторный вызов `decrypt_value()` без `cache_ok=True` каждый раз вызывает Fernet-расшифровку (можно замокать `_fernet()`).

**Критерий готовности:** `grep -n "_ENCRYPT_CACHE" utils/crypto.py` возвращает пустой результат или только строки в not-ПДн ветке.

---

### ЗАДАЧА 2 — Заблокировать plaintext мастер-ключ в dev-режиме при наличии реальных данных

**Файл:** `utils/crypto.py`, функция `_load_existing_key()` (строки ~480–490)

**Проблема:**
```python
if len(raw_bytes) == 32:
    if _is_production_mode():
        raise CryptoProductionModeError(...)
    logger.critical("SECURITY: Loading master key from legacy plaintext file! ...")
    return raw_bytes   # <- возвращает ключ в plaintext в dev-режиме
```
Dev-режим (`EXCEL_XML_PROD` не установлен) допускает хранение мастер-ключа в открытом виде. Если разработчик тестирует на реальных данных — ПДн уязвимы.

**Что сделать:**

1. Добавь функцию `_has_any_encrypted_data() -> bool`, которая проверяет наличие зашифрованных записей в БД:
   ```python
   def _has_any_encrypted_data() -> bool:
       """Returns True if DB contains any PD records (snils_enc not empty)."""
       try:
           from db.database import DatabaseManager
           db = DatabaseManager.get_instance()
           row = db.fetchone(
               "SELECT 1 FROM workers_data WHERE snils_enc != '' LIMIT 1"
           )
           return row is not None
       except Exception:
           return False  # БД ещё не инициализирована — данных нет
   ```

2. В `_load_existing_key()` замени текущий plaintext fallback:
   ```python
   if len(raw_bytes) == 32:
       # Блокируем если есть реальные данные — независимо от режима
       if _has_any_encrypted_data():
           raise CryptoProductionModeError(
               "SECURITY: Master key is plaintext but encrypted PD records exist in DB! "
               "Migrate key to DPAPI protection before continuing. "
               "Run key migration or set EXCEL_XML_PROD=1."
           )
       if _is_production_mode():
           raise CryptoProductionModeError(...)
       logger.critical("SECURITY: Loading plaintext master key (dev mode, no PD data).")
       return raw_bytes
   ```

3. Добавь тест в `tests/test_crypto.py`: при наличии записи в `workers_data` и plaintext ключе — `_load_existing_key()` должна поднимать `CryptoProductionModeError`.

**Критерий готовности:** Dev-режим с plaintext ключом работает только при пустой БД.

---

### ЗАДАЧА 3 — Усилить пароль резервной копии БД

**Файл:** `db/database.py`, функция `_get_backup_password()` (строка ~210)

**Проблема:**
```python
def _get_backup_password() -> str:
    mk = _get_or_create_master_key()
    return hashlib.pbkdf2_hmac('sha256', mk, b'EXCEL_XML_BACKUP_V3', 100000).hex()[:16]
```
- Только 16 hex-символов = 64 бита энтропии.
- Пароль детерминирован от мастер-ключа: компрометация ключа → все бэкапы раскрыты.
- 100 000 итераций PBKDF2 — слабее чем 600 000 в основном крипто.

**Что сделать:**

1. Вынеси соль и число итераций в константы в `utils/crypto.py`:
   ```python
   _BACKUP_KEY_SALT = b'EXCEL_XML_BACKUP_V4_SALT_2024'
   _BACKUP_KEY_ITERATIONS = 600_000
   _BACKUP_KEY_LENGTH = 32   # байт → 64 hex символа
   ```

2. Перепиши функцию:
   ```python
   def _get_backup_password() -> str:
       """Derive backup encryption password from master key via PBKDF2.
       Returns 64-char hex string (256-bit key material).
       """
       mk = _get_or_create_master_key()
       derived = hashlib.pbkdf2_hmac(
           'sha256', mk, _BACKUP_KEY_SALT, _BACKUP_KEY_ITERATIONS, dklen=_BACKUP_KEY_LENGTH
       )
       return derived.hex()   # 64 символа, НЕ обрезаем
   ```

3. Добавь в `_get_backup_password()` и в `database.py::create_backup()` явный комментарий:
   ```python
   # NOTE: If master key is rotated, old backups will be unrecoverable.
   # Always create a new backup immediately after key rotation.
   ```

4. Обнови тест в `tests/test_database.py` — проверь что длина пароля равна 64 символам.

**Критерий готовности:** `len(_get_backup_password()) == 64`.

---

### ЗАДАЧА 4 — Принудительное подтверждение при отключении TLS

**Файлы:** `api/mintrud_api.py` (строки ~304–314), `utils/security_dialog.py`

**Проблема:**
```python
# mintrud_api.py строка 314:
# TODO: Organizational measure - require explicit written authorization to disable TLS
```
Пользователь может снять галочку "Проверять TLS" в настройках без каких-либо барьеров. При работе с ПДн передача через незащищённое соединение недопустима.

**Что сделать:**

1. В `api/mintrud_api.py` функцию `_get_verify()` измени так:
   ```python
   def _get_verify(self) -> bool:
       verify = self.proxy_settings.get("tls_verify", True)
       if not verify:
           logger.warning(
               "SECURITY: TLS verification is DISABLED - connection is insecure. "
               "Outgoing PD data may be intercepted."
           )
           log_audit("TLS_WARNING", "TLS verification disabled by user")
       return bool(verify)
   ```

2. В `utils/security_dialog.py` найди место, где пользователь может отключить TLS (чекбокс или настройка `tls_verify`). Перед сохранением настройки `tls_verify=False` добавь **модальное подтверждение**:
   ```python
   from PySide6.QtWidgets import QMessageBox
   
   def _on_tls_verify_toggled(self, checked: bool):
       if not checked:
           reply = QMessageBox.warning(
               self,
               "Предупреждение безопасности",
               "Отключение проверки TLS-сертификата создаёт риск перехвата "
               "персональных данных (атака MITM).\n\n"
               "Это действие будет зафиксировано в журнале аудита.\n\n"
               "Вы уверены, что хотите отключить проверку TLS?",
               QMessageBox.Yes | QMessageBox.No,
               QMessageBox.No,
           )
           if reply != QMessageBox.Yes:
               # Откатываем чекбокс
               self._tls_checkbox.setChecked(True)
               return
       # Сохраняем настройку только после подтверждения
       self._save_tls_setting(checked)
   ```

3. Убедись, что при запуске приложения с `tls_verify=False` в настройках — в лог сразу пишется `TLS_WARNING` (уже происходит через `_get_verify()`, но добавь также при инициализации `MintrudApiClient`).

**Критерий готовности:** Невозможно отключить TLS без явного диалога подтверждения; событие всегда попадает в audit.log.

---

### ЗАДАЧА 5 — Увеличить длину HMAC метаданных мастер-ключа

**Файл:** `utils/crypto.py`, функции `_compute_metadata_hmac()` и `_compute_metadata_hmac_legacy()` (строки ~252, ~270)

**Проблема:**
```python
return hmac.new(hmac_key, serialized, hashlib.sha256).hexdigest()[:16]
```
Усечение до 16 символов = 64 бита. Для HMAC, защищающего целостность мастер-ключа — недостаточно. NIST SP 800-107 рекомендует минимум 112 бит (28 символов hex), для критических приложений — 128 бит (32 символа).

**Что сделать:**

1. Добавь константу:
   ```python
   _HMAC_TAG_LENGTH: int = 32   # 128-bit HMAC tag (hex chars)
   _HMAC_TAG_LENGTH_LEGACY: int = 16   # для обратной совместимости
   ```

2. Обнови `_compute_metadata_hmac()`:
   ```python
   def _compute_metadata_hmac(meta: dict) -> str:
       ...
       return hmac.new(hmac_key, serialized, hashlib.sha256).hexdigest()[:_HMAC_TAG_LENGTH]
   ```

3. `_compute_metadata_hmac_legacy()` — **не трогай**. Она нужна для миграции старых записей, пусть возвращает `[:16]`. Добавь явный docstring:
   ```python
   def _compute_metadata_hmac_legacy(meta: dict) -> str:
       """LEGACY: 64-bit HMAC for backward compat with pre-3.x metadata. DO NOT USE for new entries."""
   ```

4. В `verify_metadata_integrity()` логика уже корректно обрабатывает оба варианта через `hmac.compare_digest`. Убедись что после миграции (пересохранения) новая запись использует 32-символьный тег:
   ```python
   if hmac.compare_digest(stored_hmac, legacy):
       logger.info("Metadata integrity: legacy 64-bit HMAC — migrating to 128-bit")
       _save_key_metadata(meta)   # пересохраняет с новым _compute_metadata_hmac
       return True
   ```

5. Обнови тест в `tests/test_crypto.py`: проверь `len(compute tag) == 32`.

**Критерий готовности:** Новые метаданные содержат 32-символьный HMAC; старые корректно мигрируют при первой проверке.

---

### ЗАДАЧА 6 — Обнулить старый ключ в памяти при ротации

**Файл:** `utils/crypto.py`, функция `rotate_master_key()` (строки ~634–680)

**Проблема:**
```python
old_key = _get_or_create_master_key()       # строка 634
old_encoded = base64.urlsafe_b64encode(old_key)
old_fernet = Fernet(old_encoded)
...
# При успехе: old_key остаётся в памяти до GC
# При откате: _MASTER_KEY = old_key  (это правильно, но old_encoded не зануляется)
```
После успешной ротации `old_key` и `old_encoded` остаются в памяти как доступные объекты Python до следующей сборки мусора.

**Что сделать:**

1. Обернуть работу со старым ключом в `try/finally` с явным zeroing:
   ```python
   def rotate_master_key(
       new_passphrase: Optional[str] = None,
       reencrypt_func: Optional[Callable] = None,
   ) -> Tuple[bool, str]:
       old_key = _get_or_create_master_key()
       old_encoded = bytearray(base64.urlsafe_b64encode(old_key))  # bytearray для обнуления
       old_fernet = Fernet(bytes(old_encoded))
       
       try:
           new_raw = os.urandom(32)
           ...
           # вся логика ротации
           ...
           return True, "Master key rotated successfully"
           
       except CryptoRotationError:
           raise
       finally:
           # Обнуляем старый ключ в любом случае (успех или откат)
           _zero_memory(old_encoded)
           # old_key — bytes, обнуляем через bytearray copy
           _zero_memory_bytes(old_key)
   ```

2. `old_encoded` сделай `bytearray` с самого начала (вместо `bytes`), чтобы `_zero_memory()` мог занулить содержимое.

3. После успешной ротации явно занули `old_encoded` перед выходом из `try`-блока (до `return`):
   ```python
   _zero_memory(old_encoded)
   log_audit("KEY_ROTATION", f"old_fingerprint={old_fp}, new_fingerprint={new_fp}")
   return True, "Master key rotated successfully"
   ```

4. Добавь тест в `tests/test_crypto.py`: после `rotate_master_key()` старый ключ должен быть обнулён (проверить через `bytearray` если возможно, или через spy на `_zero_memory_bytes`).

**Критерий готовности:** В `finally`-блоке всегда вызывается `_zero_memory`/`_zero_memory_bytes` для `old_encoded` и `old_key`.

---

## Порядок выполнения

```
1. Задача 1 (кэш) → pytest → коммит "security: remove plaintext decrypt cache"
2. Задача 5 (HMAC длина) → pytest → коммит "security: extend metadata HMAC to 128-bit"
3. Задача 6 (zeroing при ротации) → pytest → коммит "security: zero old key material after rotation"
4. Задача 3 (пароль бэкапа) → pytest → коммит "security: strengthen backup password to 256-bit"
5. Задача 2 (plaintext ключ + данные) → pytest → коммит "security: block plaintext key when PD data exists"
6. Задача 4 (TLS подтверждение) → pytest → коммит "security: require confirmation before disabling TLS"
```

Задачи 1, 5, 6 — чисто cryptographic, без UI, делай первыми.
Задачи 3, 2 — затрагивают БД, делай после стабилизации крипто.
Задача 4 — UI-изменение, делай последней, так как требует ручной проверки диалога.

---

## Финальная проверка

После всех задач выполни:

```bash
py -m pytest tests -v --tb=short
grep -n "_ENCRYPT_CACHE" utils/crypto.py       # должно быть пусто или только cache_ok ветка
grep -n "hexdigest\(\)\[:16\]" utils/crypto.py  # только в _legacy функции
python -c "from utils.crypto import _get_backup_password; print(len(_get_backup_password()))"  # 64
```

И убедись что `AGENTS.md` не требует обновлений (если добавил новые публичные функции — задокументируй их там).
