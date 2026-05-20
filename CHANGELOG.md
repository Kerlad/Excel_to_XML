# Changelog

## v2.0.0 "Performance & Virtualization"

### Performance Improvements
- **Model/View architecture**: Replaced QTableWidget with QTableView + QAbstractTableModel in:
  - `data_view_tab.py` — DataViewTableModel with virtual scrolling for 5000+ records
  - `exam_journal_tab.py` — ExamJournalTableModel with deferred model reset
- **MultiColumnFilterProxyModel**: Text filtering now searches all columns via overridden `filterAcceptsRow()` instead of row-by-row iteration
- **Batch DB queries**: `EmployeeProgramsRepo.get_by_employee_ids()` and `EmployeesRepo.get_all_with_programs()` reduce N+1 queries to single JOIN
- **SQL-level filtering**: `ExamJournalRepo.search()` uses WHERE clause for set_id, status, date ranges (uses indexes)
- **PRAGMA optimization**: `synchronous=NORMAL`, 8MB cache, `temp_store=MEMORY`, `PRAGMA optimize` on app close
- **DB schema indexes**: Composite index `idx_ep_employee_program`, date indexes on `exam_journal`
- **Fernet caching**: Singleton cipher + LRU encrypt/decrypt caches avoid re-deriving keys
- **Workers**: `ExcelImportWorker`, `XmlGenerationWorker`, `ApiBulkQueryWorker`, `PlanGenerationWorker` for background threading
- **LRU caches**: Summary cache and API response caches with TTL in `utils/cache.py`
- **`--profile` CLI flag**: Enables cProfile profiling, saves `profile.prof` to log directory
- **Read-only XLSX import**: Files > 512 KB use `openpyxl read_only=True` to avoid loading entire workbook

## v1.3.0 "Security & UX polish"

### Security Improvements (from v1.2.4)
- Added `check_master_key_security()` — detects DPAPI/raw key mode
- Added `create_master_key_backup()` / `restore_master_key_backup()` for master.key
- Added security status indicator and backup button in AboutDialog
- Added `validate_api_key_remote()` — auto-tests API key on save via server request
- Replaced `xml.etree.ElementTree` with `defusedxml` in all parsers (XXE protection)
- Added `security_audit()` call on startup — logs master.key, API key, DB encryption status
- Database backups now use password-protected ZIP (SHA256 of master key)
- Added color-coded API key indicator in StatusBar (green/red circle)
- Updated `docs/SECURITY.md` with complete architecture documentation

### UX Improvements (v1.3.0)
- **Centralized error handling**: `utils/error_utils.py` — `show_error_dialog()` with traceback details
- **Toast notifications**: `utils/toast.py` — animated sliding notifications (info/success/warning/error)
- **Visual field validation**: `utils/field_validators.py` — `ValidatedLineEdit` with red border + tooltip
- All dialogs now inherit from `BaseDialog` (PlanDialog, EmployeeAddDialog, EmployeeEditDialog, EditDialog, ProgramsDialog)
- Improved AboutDialog with security section and master.key backup button
- Enhanced StatusBar with version display, progress bar, and better API key indicator
- **Drag & Drop** file loading on DataEntry tab (XLSX/XML)
- **Copy SNILS** on double-click in DataView tab (column 3)
- Auto-save notifications via Toast

### Code Quality
- Added type hints to `utils/crypto.py`, `db/database.py`, `utils/app_paths.py`
- Added `show_progress()` / `show_progress_indeterminate()` helpers to MainWindow
- Improved docstrings across key modules
- Added `QCoreApplication.processEvents()` for UI responsiveness during long operations

## v1.2.0
- Added checkbox "Обучение по программам В (№6-29) — 1 раз в 3 года" on Employee Summary tab
- When unchecked: programs 6-29 use 1-year training period instead of 3 years
- Dynamic recalculation of employee statuses, training plans, current snapshot, and trained report
- Modular implementation in `utils/training_rules.py` — easily removable
- Updated help, README, and technical specification docs

## v1.1.0
- Added .sig file selection field for electronic signature on Data Transfer tab
- Added red "Отправить XML и ПОДПИСАТЬ" button for sending XML with signature to РОЛ
- Implemented .sig file inclusion in .olot archive (ZIP with Data.xml + signature)
- Added `<NeedSend>true</NeedSend>` flag for immediate РОЛ forwarding in signed mode
- Added confirmation dialog before signed send
- Response parsing includes `<SendEducatedPerson>` and `<Message>` elements

## v1.0.1
- Documentation restructure: README split into main + docs/SECURITY.md + docs/API_MINTTRUD.md
- Updated Техническое_задание_2.md with implemented features
- Added app icon to README

## v1.0.0
- Initial release: Employee Summary, Training Plan, XML generation, Mintrud API, encryption, themes
