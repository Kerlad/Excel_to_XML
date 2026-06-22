# Changelog

## v3.5.0 "UX: Toasts, Unified Buttons & Hotkeys"

### Changes

1. **Toast notifications restored & fixed** (`utils/toast.py`)
   - Fixed the white-text-on-transparent-background bug via QPainter-based rounded background (works in light & dark themes)
   - Success and empty-state confirmations now use non-blocking toasts instead of modal `QMessageBox`
   - Affected tabs: `data_entry`, `data_view`, `data_transfer`, `exam_journal`, `employee_summary`, `protocol`
   - Dialogs with file paths / detailed summaries intentionally kept modal

2. **Unified button styling** (design system)
   - Buttons use design-system selectors (`primary` / `success` / `danger` properties, objectNames) instead of hardcoded inline colors
   - Removed off-palette `#4169E1`; aligned to palette `#4A90E2`
   - `data_entry_tab._btn_style()` neutralized; About "Сообщить об ошибке" button uses `dialogDangerBtn`

3. **Keyboard shortcuts** (`main.py`)
   - `Ctrl+1..7` switch tabs; `Ctrl+T` template; `Ctrl+E` export; `Ctrl+L` lock; `Ctrl+D` theme; `F1` help

## v3.4.0 "Per-Program Reports & Table Fixes"

### Changes (2026-05-28)

1. **Table header freeze** (`tabs/employee_summary_tab.py`)
   - `setSortingEnabled(False)` — manual sort via `sectionClicked`
   - Header rows (0-1) are preserved during sort, only data rows (2+) sorted
   - Sub-header row height reduced from 30px to 15px
   - Sort state tracked via `_sort_column` and `_sort_order`

2. **Export reads visible rows only** (`_export_xlsx()`)
   - Now reads from table widget rows (row 2+) instead of `EmployeesRepo.get_all()`
   - Deleted/filtered rows are excluded from exports

3. **Toast replaced** with `safe_message_box()` for export save confirmations
   - Fixes white-text-on-transparent-background issue on Windows

4. **Per-program reports** (`_show_current_snapshot`, `_generate_plan`)
   - Current Situation: one row per employee **per program** with per-program expiry
   - Plan reports: same per-program approach with individual expiry date filtering
   - Added "Название" (program name) column to PlanDialog table (10 columns)
   - Added "Название" column to XLSX export in PlanDialog

5. **Delete all app data** (`main.py`, `utils/security_dialog.py`)
   - Menu: `Инструменты → Удалить все данные приложения`
   - Button in Security dialog ("Безопасность")
   - Requires typing "УДАЛИТЬ" confirmation
   - Deletes ALL files from `%APPDATA%\Excel_to_XML`
   - Audit event: `FACTORY_RESET`

6. **Removed dead code**: `_get_program_data_for_status()` (no longer needed)

## v3.3.0 "Corporate Proxy Support"

### Corporate Proxy & SSL Inspection (2026-05-26)

1. **Auto-detection of corporate environment** (`utils/proxy_manager.py`)
   - Detects proxies with `.rzd`, `.oao`, `.corp`, `.company` domains
   - `is_corporate_proxy()` / `detect_proxy_and_env()` — used by all backends
   - Automatically forces WinINET backend in corporate environments (best Negotiate/Kerberos)

2. **SSL fallback with user confirmation** (`api/mintrud_api.py`)
   - When ALL backends fail with Schannel 10013 / SSL handshake error → returns `ssl_error_detected=True`
   - UI offers to disable TLS verification with explicit security warning
   - Retry with `verify=False` is logged via `log_audit("TLS_WARNING", ...)`
   - No silent TLS disable — user must confirm each time

3. **WinINET backend hardened** (`api/backends/wininet_backend.py`)
   - `SECURITY_FLAG_IGNORE_ALL_CERT_ERRORS` set both before and after `Open()`
   - New `_is_schannel_error()` — detects Schannel 10013, 0x80090326
   - Broad exception catching for COM edge cases
   - Robust multipart boundary building (explicit bytes, type-safe)

4. **Diagnostics improvement** (`network/client.py`)
   - `is_schannel_10013_error()` — detects the error in Ru/En
   - `get_schannel_recommendation()` — user-friendly instructions
   - `get_network_diagnostics()` now reports: `is_corporate_env`, `schannel_10013_detected`, `ssl_inspection_detected`

5. **UI improvements** (`tabs/data_transfer_tab.py`)
   - When SSL error detected → dialog: "Обнаружена SSL-инспекция. Отключить TLS?"
   - Test connection shows "Корпоративная среда: Да/Нет" and "SSL-инспекция: Да/Нет"
   - Audit log fixes: `%s` formatting instead of f-strings in sensitive events

6. **Documentation** (`docs/DEPLOYMENT.md`)
   - New section §9 "Корпоративные прокси с SSL Inspection"
   - 3 solutions: disable TLS / install corporate CA / WinHTTP proxy
   - Transport backends comparison table
   - Audit events reference (TLS_WARNING, TLS_ERROR, BACKEND_CHANGE, PROXY_CHANGE)

## v3.2.0 "Security Hardening"

### Cryptographic Security (2026-05-24)

1. **Removed in-memory PD decrypt cache** (`utils/crypto.py`)
   - `_ENCRYPT_CACHE` (2000 entries of plaintext PDn in RAM) removed
   - Replaced with `_NON_PD_CACHE` used only when `cache_ok=True` is explicitly passed
   - `decrypt_value()` now defaults to `cache_ok=False` — always calls Fernet for PD fields
   - Tests updated: verify Fernet is called on every `decrypt_value()` call without `cache_ok`

2. **Extended metadata HMAC to 128-bit** (`utils/crypto.py`)
   - `_compute_metadata_hmac()` now returns 32 hex chars (was 16) — NIST SP 800-107 compliant
   - Added `_HMAC_TAG_LENGTH = 32` and `_HMAC_TAG_LENGTH_LEGACY = 16` constants
   - Legacy 64-bit HMAC auto-migrates to 128-bit on first integrity check

3. **Zero old key material after rotation** (`utils/crypto.py`)
   - `rotate_master_key()` now wraps old key in `bytearray` for mutability
   - `try/finally` block guarantees `_zero_memory()` / `_zero_memory_bytes()` always called
   - Old key and old encoded key zeroed regardless of success or rollback

4. **Strengthened backup password to 256-bit** (`utils/crypto.py`, `db/database.py`)
   - PBKDF2 iterations increased from 100K to 600K (matching passphrase derivation)
   - Key length increased from 16 bytes (64-bit) to 32 bytes (256-bit) → 64 hex chars
   - Salt updated to `EXCEL_XML_BACKUP_V4_SALT_2024`
   - Added NOTE about key rotation making old backups unrecoverable

5. **Blocked plaintext master key when PD data exists** (`utils/crypto.py`)
   - New `_has_any_encrypted_data()` checks `workers_data` for encrypted records
   - `_load_existing_key()` now raises `CryptoProductionModeError` if plaintext key found AND PD records exist in DB — regardless of dev/prod mode

6. **Required explicit confirmation before disabling TLS** (`api/mintrud_api.py`, `tabs/data_transfer_tab.py`)
   - Confirmation dialog now defaults to "No" and explicitly warns about PD data interception risk
   - TLS setting saved immediately after confirmation (not on batch save)
   - `TLS_WARNING` audit event logged at `MintrudApiClient` initialization if TLS disabled
   - Removed stale TODO comment

## v3.1.0 "Version Bump"

### Version Update (2026-05-22)
- Application version updated from 3.0.0 to 3.1.0 across all sources
- Updated VERSION constant, version_info.txt, documentation headers, and report metadata

## v3.0.1 "Security Audit & Compliance"

### Documentation (2026-05-22)
- **SECURITY_AUDIT_REPORT.md** — Full security audit report: 1 CRITICAL, 17 HIGH, 39 MEDIUM findings
- **COMPLIANCE.md** — Comprehensive 152-ФЗ / ПП №1119 / ФСТЭК №21 compliance matrix
- **PRIVACY.md** — Privacy policy document per 152-ФЗ (privacy-by-design)
- **DEPLOYMENT.md** — Secure deployment guide (hardened)
- **GAP_ANALYSIS.md** — Gap analysis matrix across 48 requirements
- **AGENTS.md** — Updated with audit findings and compliance requirements

### Security Audit Findings Summary
- **CRITICAL**: Audit HMAC is NEVER verified (security theater)
- **HIGH**: 17/34 audit events never emitted (dead code); SNILS leak in xlsx_importer error messages
- **HIGH**: Master key lives in module-level global, not zeroed; no thread safety in crypto
- **HIGH**: XML pattern in SensitiveDataFilter is broken (trailing regex anchor)
- **MEDIUM**: TOCTOU in XSD validation (file read twice); PKWARE ZipCrypto for backups
- **MEDIUM**: No retention policy, no secure delete, no clipboard auto-clear

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
