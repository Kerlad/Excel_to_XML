# Project Context for AI Agents

## Tech Stack
- Python 3.12, PySide6, SQLite (via custom DatabaseManager)
- openpyxl, lxml, cryptography, dateutil, requests
- PyInstaller for EXE builds

## Build & Test
- Tests: `py -m pytest tests -v`
- Build EXE: Remove `dist\ExcelXML-Mintrud`, then `py -m PyInstaller ExcelXML-Mintrud.spec`
- EXE output: `dist\ExcelXML-Mintrud\`

## Key Architecture
- `importers/` — XLSX/XML file loading (employees import; `.xls` removed, use `.xlsx` only)
  - XLSX uses `openpyxl read_only=True` (streaming), background `QThread`, progress reporting, cancel support
  - Limits: `MAX_XLSX_FILE_SIZE_MB=10`, `MAX_XLSX_ROWS=100000`
- `exporters/` — XML/XLSX generation
- `api/` — Mintrud API client (mintrud_api.py, payload_builder.py, response_parser.py, backends/)
- `db/` — SQLite via DatabaseManager, EmployeesRepo, EmployeeProgramsRepo
- `tabs/` — UI tabs: employee_summary_tab, data_entry_tab, data_transfer_tab, exam_journal_tab
- `utils/` — crypto, proxy_manager, logger, audit, app_paths, log_viewer_dialog

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
| **`close_thread_connection()`** | **NEW** — closes current thread's connection, removes from `_thread_connections` dict. Call in background threads at end of `run()`. |
| **`close()`** | Instance method — delegates to `close_thread_connection()` |
| **`close_all()`** | **NEW** — classmethod, closes ALL tracked connections, clears dict + thread-local. Idempotent. |

### Rules for Background Threads
- **Always** call `DatabaseManager.close_thread_connection()` at the end of `QThread.run()` if the thread used the database
- Currently applied in: `tabs/employee_summary_tab.py:ApiQueryThread.run()`
- Connections created in tests are cleaned up by fixture teardown calling `db.close_all()`

### Error Handling
- `DatabaseLockError` — raised after `_BUSY_RETRIES` exhausted (all retries got "database is locked")
- Lock retries: 3 attempts, 100ms delay between retries
- Logging: connection open/close at DEBUG, rollback at ERROR, lock timeout at WARNING
- `except BaseException` changed to `except Exception` — no longer catches `KeyboardInterrupt`/`SystemExit`

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

## Key Files
- `tabs/employee_summary_tab.py` — main tab for registry sync, plan, stats
- `tabs/data_entry_tab.py` — XML/XLSX import tab
- `tabs/data_transfer_tab.py` — API send/query tab
- `utils/constants.py` — shared constants (VALID_PROGRAMS, PROGRAM_TITLES)
- `tabs/programs_dialog.py` — training programs editor dialog
- `api/mintrud_api.py` — MintrudClient class
- `api/backends/` — transport backends (Requests, WinINET)
- `utils/crypto.py` — Fernet + DPAPI encryption
- `utils/audit.py` — audit logging
- `utils/logger.py` — SensitiveDataFilter
- `utils/training_rules.py` — training period rules (program A vs B period, easily removable)
- `network/client.py` — network diagnostics
- `db/employee_programs_repo.py` — program data per employee
- `db/employees_repo.py` — employee CRUD

## Documentation
- `README.md` — main project overview
- `docs/SECURITY.md` — security architecture (encryption, DPAPI, logging)
- `docs/API_MINTTRUD.md` — Mintrud API reference
- `docs/Техническое_задание_2.md` — full technical specification (TZ)
- `CHANGELOG.md` — version history
