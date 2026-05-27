# Project Context for AI Agents

## Tech Stack
- Python 3.12, PySide6, SQLite (via custom DatabaseManager)
- openpyxl, lxml, cryptography, dateutil, requests
- PyInstaller for EXE builds

## Build & Test
- Tests: `py -m pytest tests -v`
- Production mode: `set EXCEL_XML_PROD=1` before running (blocks plaintext keys)

### EXE Build & Release
1. Remove old build: `Remove-Item -Path "dist\ExcelXML-Mintrud" -Recurse -Force`
2. Build EXE: `py -m PyInstaller ExcelXML-Mintrud.spec`
3. Create zip: `Compress-Archive -Path "dist\ExcelXML-Mintrud\*" -DestinationPath "dist\ExcelXML-Mintrud.zip" -Force`
4. Update README.md download link to point to the new zip (raw URL: `https://github.com/Kerlad/Excel_to_XML/raw/main/dist/ExcelXML-Mintrud.zip`)
5. Commit all changes including the new zip, README link, and any deleted old zips

## SECURITY: Critical Rules
1. **ALL XML from external sources** MUST use `defusedxml.ElementTree` (not stdlib `xml.etree`)
2. **ALL XML from external sources** MUST go through `utils.xml_safe.safe_parse_xml()` or `safe_fromstring_xml()`
3. **NO f-string logging** with user data — use `%s` formatting with `filter_sensitive_text()`
4. **NO raw exceptions** in UI — use `utils.error_utils.show_exception_dialog()`
5. **NO plaintext master key** in production mode — raises `CryptoProductionModeError`
6. **NO hardcoded secrets** — backup password MUST derive from master key via PBKDF2
7. **TLS verify=True** by default — disabling MUST log audit event `TLS_WARNING`
8. **ALL SQL queries** MUST use parameterized queries (no string concatenation)
9. **ALL sensitive logging** MUST pass through `SensitiveDataFilter`
10. **Thread-local connections** MUST be closed at end of background thread via `DatabaseManager.close_thread_connection()`

## Key Architecture
- `importers/` — XLSX/XML file loading (employees import; `.xls` removed, use `.xlsx` only)
  - XLSX uses `openpyxl read_only=True` (streaming), background `QThread`, progress reporting, cancel support
  - Limits: `MAX_XLSX_FILE_SIZE_MB=10`, `MAX_XLSX_ROWS=100000`
- `exporters/` — XML/XLSX generation
- `api/` — Mintrud API client (mintrud_api.py, payload_builder.py, response_parser.py, backends/)
- `db/` — SQLite via DatabaseManager, EmployeesRepo, EmployeeProgramsRepo
- `tabs/` — UI tabs: employee_summary_tab, data_entry_tab, data_transfer_tab, exam_journal_tab
- `utils/` — crypto, proxy_manager, logger, audit, app_paths, log_viewer_dialog, secure_temp

## Database Architecture (`db/database.py`)

### Connection Lifecycle
- **Thread-local connections** via `threading.local()` — each thread gets its own connection on first use
- **`_thread_connections` dict** (class-level, `_connections_lock` protected) — tracks all open connections by thread ID
- **Auto-closed** on app shutdown via `atexit.register(cls.close_all)` in `get_instance()`

### Key Methods
| Method | Description |
|---|---|
| `get_instance(db_path)` | Singleton, registers `atexit` cleanup on first creation |
| `_get_connection()` | Creates thread-local connection with WAL+FK+optimized PRAGMAs |
| `get_conn()` | Context manager — yields connection, rolls back on `DatabaseError` |
| `transaction()` | Context manager — commits on success, retries on lock (`_BUSY_RETRIES=3`), rolls back on error |
| `execute(sql, params)` | Implicit cursor via `get_conn()` |
| `executemany(sql, seq)` | Batch execute via `get_conn()` |
| `fetchone(sql, params)` | Returns `dict` or `None` |
| `fetchall(sql, params)` | Returns `list[dict]` |
| **`close_thread_connection()`** | Closes current thread's connection, removes from `_thread_connections` dict. Call in background threads at end of `run()`. |
| **`close()`** | Instance method — delegates to `close_thread_connection()` |
| **`close_all()`** | Classmethod, closes ALL tracked connections, clears dict + thread-local. Idempotent. |

### Rules for Background Threads
- **Always** call `DatabaseManager.close_thread_connection()` at the end of `QThread.run()` if the thread used the database
- Currently applied in: `tabs/employee_summary_tab.py:ApiQueryThread.run()`
- Connections created in tests are cleaned up by fixture teardown calling `db.close_all()`

### Error Handling
- `DatabaseLockError` — raised after `_BUSY_RETRIES` exhausted (all retries got "database is locked")
- Lock retries: 3 attempts, 100ms delay between retries
- Logging: connection open/close at DEBUG, rollback at ERROR, lock timeout at WARNING
- `except BaseException` changed to `except Exception` — no longer catches `KeyboardInterrupt`/`SystemExit`

### Backup Security
- Backup password derived from master key via `get_key_fingerprint()` or PBKDF2
- NEVER use hardcoded or date-based passwords
- Backup rotation: max 5 copies

## Crypto Architecture (`utils/crypto.py`)

### Key Hierarchy
```
Windows DPAPI (user + machine + entropy)
    └── Master Key (32 bytes, Fernet AES-128-CBC)
         ├── [Optional] Passphrase (PBKDF2-HMAC-SHA256, 600K iterations)
         │    └── Passphrase-wrapped key
         ├── API key (Fernet-encrypted)
         ├── Proxy credentials (Fernet-encrypted)
         └── Field-level encryption (ФИО, СНИЛС)
```

### Production Mode
- Set `EXCEL_XML_PROD=1` to enable strict mode
- Blocks: plaintext master keys, missing DPAPI, insecure fallbacks
- Raises `CryptoProductionModeError` on violation

### Key Metadata
- Stored in `master.key.json` with HMAC-SHA256 integrity tag
- Version tracking, creation/rotation timestamps, key fingerprint
- `verify_metadata_integrity()` checks HMAC before use
- Corrupted keys archived to `corrupted_keys/` directory

### Security Rules
- `encrypt_value()` / `decrypt_value()` — field-level Fernet
- `hash_for_search()` — SHA-256 of normalized value (for DB indexing)
- Cache: only ciphertext (never plaintext), max 2000 items
- Backup: PBKDF2-derived password from master key (NO hardcoded constants)

## Logging Security (`utils/logger.py`)

### SensitiveDataFilter (27+ patterns)
- SNILS, passports, phones, emails, API keys, tokens, JWT
- Full Russian names (ФИО), initials
- Passwords, proxies, cookies, session IDs
- JSON sensitive key values (recursive)
- XML/SOAP payload tagging

### Production Logging
- Main handler: INFO level (NOT DEBUG)
- Error handler: ERROR level
- Third-party libs: urllib3, requests, openpyxl → WARNING
- Safe exception formatting via `safe_format_exception()`
- `filter_sensitive_text()` for all log messages

### Prohibited in Logs
- Raw PDn (SNILS, names)
- Endpoint URLs
- File paths containing sensitive data
- Full traceback in user-facing dialogs
- Raw HTTP request/response bodies

## Audit System (`utils/audit.py`)

### 34 Security Events
`SEND_XML`, `SEND_XML_SIGNED`, `QUERY_SETID`, `QUERY_SNILS`,
`IMPORT_XLSX`, `IMPORT_XML`, `EXPORT_XML`, `EXPORT_XLSX`,
`LOGIN`, `BACKUP`, `KEY_ACCESS`, `KEY_ROTATION`,
`KEY_BACKUP`, `KEY_RESTORE`, `PASSPHRASE_SET`, `PASSPHRASE_REMOVED`,
`TLS_WARNING`, `TLS_ERROR`, `XML_VALIDATION_ERROR`, `XML_SECURITY_ERROR`,
`EXPORT_PLAN`, `EXPORT_SNAPSHOT`, `EXPORT_TRAINED_REPORT`,
`IMPORT_CANCELLED`, `SECURITY_WARNING`, `STARTUP`, `SHUTDOWN`,
`CRASH`, `ERROR_RESPONSE_SAVED`, `PROXY_CHANGE`, `BACKEND_CHANGE`,
`AUDIT_INTEGRITY_CHECK`

### HMAC Protection
Each audit entry includes HMAC-SHA256 tag: `[hmac_tag] EVENT | detail`

## XML Security (`utils/xml_safe.py`)

### Required for ALL external XML
- `safe_parse_xml(file_path)` — file-based parsing with defusedxml
- `safe_fromstring_xml(data)` — string-based parsing with defusedxml
- `LimitedXMLParser` — limits: 50000 elements, depth 20, size 100MB

### Require check for lxml usage
When using `lxml.etree` for XSD validation, ALWAYS use:
```python
parser = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    dtd_validation=False,
    huge_tree=False,
)
```

### Prohibited
- `xml.dom.minidom.parseString()` for external XML
- `lxml.etree.parse()` without secure parser settings
- `xml.etree.ElementTree` without defusedxml wrapper

## Temp File Security (`utils/secure_temp.py`)
- Per-process isolated temp directory: `%TEMP%/excel_xml_secure_<UUID>`
- ACL-restricted to current user
- Secure deletion: 3-pass overwrite before delete
- Auto-cleanup on process exit via `atexit`

## Requirements (Implemented)

### FR-001: Employee Status (Employee-level, NOT program-level)
- Status per employee is determined by scanning ALL their `need_training=1` programs:
  - If **any** program has `status='not_trained'` (null exam_date) → employee = "Не обучен"
  - Else if **any** program has `status='expired'` → employee = "Просрочено"
  - Else all programs are `trained` → employee = "Обучен"
- Priority: `not_trained` > `expired` > `trained`

### FR-002: Stats Cards Count Employees, Not Programs
- `_update_stats()` iterates all employees, calls `_get_employee_status()` per employee
- Counts how many employees are in each status category
- Same logic used in `_build_table()` for per-row overall_status

### FR-003: Current Snapshot Report
- Button "Текущая ситуация" (replaces old "Обновить данные")
- Generates a report dialog showing every employee with their current status
- Uses PlanDialog for display
- Status priority: Не обучен (Высокий) > Просрочено (Высокий) > Обучен (Низкий)

### FR-004: Plan Generation (Employee-level)
- `_generate_plan()` iterates employees, determines per-employee status via `_get_employee_status()`
- For not_trained employees → includes if "Включать не обученных" checked
- For expired employees → includes if "Включать просроченных" checked
- For trained employees → includes if "Истекает срок действия" and expiry year matches plan year
- One row per employee (not one per program)

### FR-009: Training Period Toggle for Type B Programs (№6-29)
- Programs 1-5 (Type A): always 3-year training period
- Programs 6-29 (Type B): configurable via checkbox "Обучение по программам В (№6-29) — 1 раз в 3 года"
  - Checked (default): 3-year period (post-September 2026 rule)
  - Unchecked: 1-year period (pre-September 2026 rule)
- Checkbox state persisted in `summary_programs.json` (`b_period_3years`)
- Affects: `_get_employee_status()`, `_build_table()`, `_show_current_snapshot()`, `_generate_plan()`, `_generate_trained_report()`
- Central logic in `utils/training_rules.py` — delete this file + remove references from `employee_summary_tab.py` to disable

### FR-005: SetId Capture on XML Send
- SetId from `send_xml` response is saved to UI display field and journal
- Located in `data_transfer_tab.py:send_xml()`

### FR-006: API SNILS Query Format
- SNILS sent to server in `XXX-XXX-XXX XX` format (with dashes and space)
- `<ApiKey>` element required in all EducatedPersonFilter queries
- No XML namespace on EducatedPersonFilter
- Pagination: break when `len(records) < page_size`

### FR-007: API Date Normalization
- `_normalize_api_date()` in `employee_summary_tab.py` converts ISO dates (`2025-09-26T00:00:00`) to `DD.MM.YYYY`
- Applied in `_process_api_records()` and `_query_single()`

### FR-008: Error Response Saving
- Full server error responses saved to `log/error_response.txt` (UTF-8 BOM)
- Implemented in `mintrud_api.py:_save_error_response()`
- Filtered through `filter_sensitive_text()` before saving

## Key Files
- `tabs/employee_summary_tab.py` — main tab for registry sync, plan, stats
- `tabs/data_entry_tab.py` — XML/XLSX import tab
- `tabs/data_transfer_tab.py` — API send/query tab
- `utils/constants.py` — shared constants (VALID_PROGRAMS, PROGRAM_TITLES)
- `tabs/programs_dialog.py` — training programs editor dialog
- `api/mintrud_api.py` — MintrudClient class
- `api/backends/` — transport backends (Requests, WinINET)
- `utils/crypto.py` — Fernet + DPAPI encryption + production mode enforcement
- `utils/audit.py` — 34 security events with HMAC integrity
- `utils/logger.py` — SensitiveDataFilter (27+ patterns, recursive)
- `utils/xml_safe.py` — defusedxml wrapper with element/depth limits
- `utils/secure_temp.py` — isolated temp directory, secure deletion
- `utils/error_utils.py` — safe exception display (no PII)
- `utils/training_rules.py` — training period rules (program A vs B period, easily removable)
- `network/client.py` — network diagnostics (no USERNAME)
- `db/employee_programs_repo.py` — program data per employee
- `db/employees_repo.py` — employee CRUD

## UI Layout (employee_summary_tab.py)

### Toolbar — two rows
- **Row 1** (`_build_toolbar_row1()`): [+ Добавить сотрудника] [Импорт из xlsx] [Экспорт в xlsx] [Экспорт (все)] [Выбрать программы]
- **Row 2** (`_build_toolbar_row2()`): [Запросить из реестра] [Обновить выбранные] [~2cm spacer] [Удалить выбранные] [Удалить все]
- 2cm indent (75px fixed-width spacer) separates "Обновить выбранные" from "Удалить выбранные"
- References: `employee_summary_tab.py:621-664`, `main.layout at line 575-576`

### Row order (top to bottom)
1. Stats cards (`_build_stats`)
2. Period settings (`_build_period_row`)
3. Report buttons (`_build_report_row`)
4. Toolbar row 1 (`_build_toolbar_row1`)
5. Toolbar row 2 (`_build_toolbar_row2`)
6. Filters (`_build_filters`)
7. Table (stretch)

## Window Geometry Persistence
- `main.py` — saves/restores window size+position via `saveGeometry()` / `restoreGeometry()` (QByteArray → base64)
- File: `%APPDATA%\Excel_to_XML\window_settings.json` (plain JSON)
- Save: `_save_window_geometry()` called in `closeEvent` (`main.py:356-359`)
- Restore: `_restore_window_geometry()` called in `__init__` after `resize()` (`main.py:48`)
- Fallbacks to default 1000×700 on first launch or on corrupt/missing file
- AppUserModelID set via `SetCurrentProcessExplicitAppUserModelID("excelxml.mintrud.3.1")` for correct Windows taskbar icon (`main.py:444`)

## Audit Results (2026-05-22)
- See `SECURITY_AUDIT_REPORT.md` for full report, `GAP_ANALYSIS.md` for gap matrix
- **CRITICAL**: Audit HMAC is NEVER verified (security theater)
- **HIGH**: 17/34 audit events never emitted (dead code), SNILS leak in xlsx_importer.py:52
- **HIGH**: Master key lives in module-level global, not zeroed; no thread safety in crypto
- **HIGH**: XML pattern in SensitiveDataFilter is broken (trailing `(?:\s*http)`)
- **MEDIUM**: TOCTOU in XSD validation (file read twice), PKWARE ZipCrypto for backups
- **MEDIUM**: No retention policy, no secure delete, no clipboard auto-clear
- **LOW**: Position field in plaintext, no namespace in XML export

## Documentation
- `README.md` — main project overview (comprehensive: architecture, PDn protection, compliance, threat model)
- `docs/SECURITY.md` — cryptography spec, supported versions, vulnerability reporting, secure deployment
- `docs/HARDENING.md` — Windows hardening guide (BitLocker, antivirus, firewall, restricted users, audit)
- `docs/OPSEC_GUIDE.md` — operational security guide (Mermaid diagrams, key rotation, incident response)
- `docs/API_MINTTRUD.md` — Mintrud API reference
- `docs/Техническое_задание.md` — full TS with section 9 (ИБ, model угроз, требования к окружению/хранению/доступу)
- `reports/hardening_report.md` — v3.1.0 security audit report (18 vulnerabilities fixed)
- `reports/compliance_audit.md` — 152-ФЗ / ПП 1119 compliance audit (юридико-технический аудит)
- `reports/threat_model.md` — STRIDE threat model (8 components, 48 threat/mitigation pairs)
- `reports/data_flow.md` — 11 data flows, data matrix, storage table, deletion scheme
- `reports/risk_register.md` — 24 risks with probability/consequence scoring
- `reports/security_checklist.md` — 7 checklists (deploy, daily, weekly, monthly, incident, disposal, personnel)
- `reports/dpia.md` — Data Protection Impact Assessment (ОВЗД по 152-ФЗ)
- `CHANGELOG.md` — version history
