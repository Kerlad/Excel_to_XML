1. Perform final stabilization, cleanup and testing of the project.

   Project:
   Windows desktop application (PySide6 + SQLite + requests + WinINet + PyInstaller)
   for occupational safety registry, employee training tracking,
   XML generation and Mintrud API integration.

   Current status:
   - antivirus false positives resolved
   - AppData storage enabled
   - SQLite plain DB
   - field-level encryption implemented
   - DPAPI master key implemented
   - requests + wininet only

   Goal:
   Finalize project for production/corporate deployment.

   IMPORTANT:
   Do NOT break existing functionality.
   Do NOT reintroduce antivirus false positives.
   Do NOT remove requests or wininet backends.

   ==================================================
   SECTION 1. FINAL CODE CLEANUP
   ==================================================

   1.1 Remove ambiguous base directory logic

   File:
   utils/app_paths.py

   Problem:
   get_base_dir() still points to executable/project directory
   and can be accidentally reused for runtime storage.

   Action:
   - audit all usages of get_base_dir()
   - ensure it is NOT used for:
     - logs
     - db
     - temp
     - configs
     - backups

   If used only for resources:
   rename:

   get_base_dir()
   -> get_resource_dir()

   or equivalent.

   Goal:
   runtime storage only in AppData.

   --------------------------------------------------

   1.2 Reduce crypto log noise

   File:
   utils/crypto.py

   Current:
   decrypt failures log detailed exception text.

   Replace:

   logger.error(f"Decrypt failed: {e}")

   with safer production logging:

   logger.warning("Decrypt failed")

   Avoid noisy crypto stack traces.

   --------------------------------------------------

   1.3 Harden DPAPI fallback handling

   Files:
   utils/crypto.py

   Problem:
   DPAPI helpers catch only ImportError.

   Need:
   catch broader exceptions:

   - permission issues
   - profile corruption
   - domain restrictions
   - DPAPI failures

   Use:

   except Exception as e:

   with safe fallback.

   Log concise warning.

   --------------------------------------------------

   1.4 Validate master.key fallback mode

   If DPAPI unavailable:
   master.key stored raw.

   This is acceptable fallback.

   Required:
   - document fallback mode
   - log warning once
   - optionally expose UI warning

   Text:
   "DPAPI unavailable, using local fallback key (reduced security)."

   ==================================================
   SECTION 2. STORAGE AND FILE SECURITY
   ==================================================

   2.1 Audit runtime storage

   Verify ALL runtime files stored only in:

   %APPDATA%/Excel_to_XML/

   Check:
   - app_data.db
   - logs
   - settings
   - backups
   - master.key
   - temp files if persistent

   Forbidden:
   runtime files near executable.

   --------------------------------------------------

   2.2 XML temp cleanup

   Audit XML generation/export.

   Temporary XML files may contain personal data.

   Requirements:
   - create in temp dir
   - auto cleanup after send/export

   Use:
   NamedTemporaryFile(delete=True)

   or explicit cleanup.

   Verify no temp XML remains after operation.

   --------------------------------------------------

   2.3 Temporary DOCX/protocol cleanup

   Audit generated protocol or report temp files.

   Temporary files:
   - auto cleanup if transient

   Persistent exports:
   - only user-selected destination.

   ==================================================
   SECTION 3. SECURITY HARDENING
   ==================================================

   3.1 Logging audit

   Verify logs never contain:

   - SNILS
   - FIO
   - proxy passwords
   - tokens
   - API keys
   - XML payloads

   Audit all logger calls.

   Verify masking works.

   Examples:
   14566772094 -> 145****094

   --------------------------------------------------

   3.2 Proxy credential security

   Current:
   proxy credentials encrypted in config.

   Acceptable.

   But improve:

   Document recommendation:
   future migration to Windows Credential Manager.

   Do not break current storage.

   --------------------------------------------------

   3.3 API key handling

   Verify:
   API keys are not bundled in repository/build.

   On first launch:
   generate empty/default config.

   Do not ship real/test API keys.

   --------------------------------------------------

   3.4 Backup verification

   Verify backups preserve encrypted fields.

   Ensure backups do NOT create plaintext exports.

   ==================================================
   SECTION 4. NETWORK ROBUSTNESS
   ==================================================

   4.1 Requests backend optimization

   Problem:
   requests sessions may be recreated too often.

   Implement persistent:

   requests.Session()

   Reuse session for batch operations.

   --------------------------------------------------

   4.2 Retry policy

   Add retry strategy:

   - retries=3
   - exponential backoff

   For:
   - registry API
   - Mintrud API
   - network instability

   --------------------------------------------------

   4.3 Manual proxy auth testing

   Verify requests backend supports:

   http://username:password@host:port

   Manual proxy mode must work.

   --------------------------------------------------

   4.4 TLS policy

   Verify:
   TLS verify=True default.

   No silent verify=False fallback.

   Only explicit setting/UI option allowed.

   ==================================================
   SECTION 5. DATABASE STABILITY
   ==================================================

   5.1 SQLite settings

   Verify:

   PRAGMA journal_mode=WAL;
   PRAGMA foreign_keys=ON;
   PRAGMA synchronous=FULL or NORMAL;

   Ensure no regressions.

   --------------------------------------------------

   5.2 Graceful DB shutdown

   Ensure:
   all sqlite connections closed on exit.

   Implement/verify:

   DatabaseManager.close_all()

   Call on app shutdown.

   ==================================================
   SECTION 6. FUNCTIONAL TESTING
   ==================================================

   Perform functional test audit.

   ==================================================
   6.1 Employee Summary (2.7)
   ==================================================

   Test:
   - Excel import
   - manual employee add/edit
   - employee search by SNILS
   - duplicate detection
   - encrypted storage
   - registry sync
   - status updates
   - filters
   - exports

   Verify:
   all flows work.

   ==================================================
   6.2 Training Plan (2.8)
   ==================================================

   Test:
   - generate next year plan
   - overdue detection
   - recommendations
   - filtering
   - export if applicable

   Verify business logic.

   ==================================================
   6.3 Journal
   ==================================================

   Test:
   - add/edit records
   - filters
   - status logic
   - SetId
   - exports

   ==================================================
   6.4 Monitoring
   ==================================================

   Test:
   - logs visible
   - refresh
   - filters
   - statuses

   ==================================================
   6.5 XML workflow
   ==================================================

   Test:
   - XML generation
   - validation
   - send flow
   - temp cleanup

   ==================================================
   SECTION 7. LOAD TESTING
   ==================================================

   Run basic performance/load testing.

   Test with:

   Employees:
   - 100
   - 1000
   - 5000+

   Verify:
   - import speed
   - search speed
   - filtering speed
   - UI responsiveness

   Test batch API requests.

   Verify:
   - no UI freeze
   - worker threads work
   - progress bars update

   ==================================================
   SECTION 8. UI TESTING
   ==================================================

   Verify long operations use worker threads:

   - Excel import
   - API sync
   - XML generation

   UI requirements:
   - no freeze
   - progress indicators
   - cancel buttons if applicable

   ==================================================
   SECTION 9. TECHNICAL SPECIFICATION UPDATE
   ==================================================

   Update attached technical specification.

   Replace obsolete architecture references.

   Remove obsolete requirements:

   - app_data.db.enc
   - DB encrypt on shutdown
   - DB decrypt on startup

   Replace with:

   Architecture:
   - plain SQLite DB
   - field-level encryption
   - DPAPI master key
   - AppData runtime storage

   Runtime path:
   %APPDATA%/Excel_to_XML/

   Update sections 2.7 and 2.8 if implementation changed.

   ==================================================
   SECTION 10. README UPDATE
   ==================================================

   Update README.md.

   Add/update:

   1. Architecture overview
   2. Security model:
      - field-level encryption
      - DPAPI
      - AppData storage

   3. Corporate network support:
      - requests
      - wininet
      - proxy support

   4. Build instructions:
      - PyInstaller
      - no UPX
      - onedir

   5. Runtime paths

   6. Troubleshooting:
      - proxy issues
      - logs
      - TLS

   7. Security notes:
      - fallback key mode
      - storage model

   ==================================================
   SECTION 11. FINAL OUTPUT
   ==================================================

   Return:

   1. Bugs fixed
   2. Remaining issues
   3. Functional test results
   4. Load test results
   5. Missing TЗ features
   6. Updated TЗ summary на русском
   7. Updated README summary на русском
   8. Production readiness assessment
   9. Recommended next improvements