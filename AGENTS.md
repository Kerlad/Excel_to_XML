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
- `exporters/` — XML/XLSX generation
- `api/` — Mintrud API client (mintrud_api.py, payload_builder.py, response_parser.py, backends/)
- `db/` — SQLite via DatabaseManager, EmployeesRepo, EmployeeProgramsRepo
- `tabs/` — UI tabs: employee_summary_tab, data_entry_tab, data_transfer_tab, exam_journal_tab
- `utils/` — crypto, proxy_manager, logger, audit, app_paths

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
