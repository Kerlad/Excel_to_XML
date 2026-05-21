# Changelog

## v2.2.0 "Logging & Observability"

### Logging System Overhaul
- **Improved log format**: `timestamp | thread | level | module | message` — thread name and module path for easier debugging
- **Increased rotation**: `backup_count` 3→5 (5 rotating files × 5MB = 25MB max history)
- **`tail_log()` utility**: Efficiently reads last N lines from file using `seek()` (never loads entire file)
- **`get_log_files()` utility**: Lists all log files including rotated backups sorted by recency

### Log Viewer (LogViewerDialog)
- **New file**: `utils/log_viewer_dialog.py` — full-featured in-app log viewer
- **Tail-based loading**: Reads from end of file using seek, supports files of any size
- **Auto-refresh**: QTimer-based, every 2 seconds, reads only new bytes since last position
- **Level filter**: Combo box for DEBUG/INFO/WARNING/ERROR/CRITICAL
- **Text search**: Real-time case-insensitive filtering
- **Log highlighting**: QSyntaxHighlighter with color-coded levels (DEBUG=gray, WARNING=orange, ERROR=red, CRITICAL=bold red bg)
- **Smart auto-scroll**: Tracks scrollbar position — disables auto-scroll when user scrolls up
- **Actions**: Clear logs (with confirmation), Open log folder, Save ZIP archive, Copy all
- **Status bar**: Shows "shown / buffer total" with active filters

### Toolbar & Menu
- **QToolBar**: New toolbar with buttons: О программе, Настройки, Помощь, Логи
- **Menu**: New "Инструменты → Просмотр логов" menu item
- Non-movable, non-floatable toolbar placed between menu bar and tab widget

## v2.1.0 "Stable XLSX Import"

### XLSX Import Stability
- **Threaded import**: XLSX loading moved to `QThread` — UI stays responsive even on large files
- **Real progress reporting**: `ExcelImportWorker` emits `progress(current, total)` and `status_message` signals; progress bar shows actual row count
- **Cancel button**: "✕ Отменить импорт" with graceful cancellation — thread stops cleanly, UI resets
- **Streaming**: Always uses `openpyxl read_only=True` — workbook never fully loaded into memory
- **Explicit resource cleanup**: Workbook closed via `try/finally`, no stale file handles
- **Limits enforced**: File size (`MAX_XLSX_FILE_SIZE_MB=10`) checked before open; row count (`MAX_XLSX_ROWS=100000`) checked during streaming
- **Logging**: Full INFO/WARNING/ERROR logging for every import stage
- **Custom exception**: `ImportCancelledError` for clean cancellation handling
- **Integration**: `data_entry_tab.py` uses `ExcelImportWorker` via `QThread`, not direct `load_xlsx()` call
- **Backward compatible**: `load_xlsx()` API extended with optional `progress_callback` and `cancel_check` parameters

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
