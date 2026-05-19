Perform final production hardening, documentation synchronization and release audit.

Project:
Windows desktop application (PySide6 + SQLite + requests + WinINet + PyInstaller)
for occupational safety registry, employee training management,
XML generation and Mintrud API integration.

Current state:
- antivirus false positives resolved
- runtime storage moved to AppData
- SQLite architecture stable
- field-level encryption implemented
- DPAPI key management implemented
- requests + wininet networking active

Goal:
Prepare final production-ready release.

IMPORTANT:
- do NOT break existing business logic
- do NOT remove requests backend
- do NOT remove wininet backend
- do NOT reintroduce antivirus triggers
- preserve current architecture

==================================================
SECTION 1. FINAL CODE HARDENING
==================================================

1.1 Safe decrypt_data()

File:
utils/crypto.py

Problem:
decrypt_data() may raise exceptions if:
- corrupted encrypted payload
- invalid JSON
- key mismatch

Required:
wrap decrypt_data() in safe try/except.

Behavior:
- log warning only
- do not crash app
- return safe fallback

Recommended:

try:
    ...
except Exception:
    logger.warning("Decrypt data failed")
    return {}

Goal:
encryption failures must not break application flow.

--------------------------------------------------

1.2 DPAPI robustness audit

File:
utils/crypto.py

Audit all DPAPI functions.

Verify:
- exceptions handled safely
- fallback key generation stable
- no crash if:
  - domain policy blocks DPAPI
  - profile corrupted
  - permissions insufficient

If DPAPI unavailable:
- generate random local key
- store master.key
- log one warning only

Avoid repetitive warnings.

Message:
"DPAPI unavailable, using local fallback key (reduced security)."

--------------------------------------------------

1.3 Crypto logging hygiene

Audit crypto logs.

Ensure logs do NOT expose:
- encrypted blobs
- stack traces with sensitive info

Use concise warnings only.

Examples:
GOOD:
logger.warning("Decrypt failed")

BAD:
logger.error(f"Decrypt failed: {exception}")

==================================================
SECTION 2. NETWORK AND PROXY STABILITY
==================================================

2.1 Requests send() exception handling

File:
api/backends/requests_backend.py

Problem:
send() may not catch all exceptions.

Fix:
replace narrow exception handling with:

except Exception as e:
    return False, 0, b'', str(e)

Ensure all network failures handled safely.

--------------------------------------------------

2.2 Retry policy audit

Review Retry configuration.

Current retry may include POST.

Risk:
POST retries may duplicate XML submissions.

Action:
review allowed_methods.

Preferred:
["HEAD", "GET", "OPTIONS"]

Only allow POST retry if API is idempotent or safe.

Document decision.

--------------------------------------------------

2.3 Persistent requests session

Verify requests.Session() reused.

Requirements:
- single persistent session
- proper close on shutdown

Avoid session recreation for batch operations.

--------------------------------------------------

2.4 Proxy manual auth audit

Verify manual proxy mode works with:

http://username:password@host:port

Test:
- authenticated proxy
- unauthenticated proxy
- invalid credentials

Ensure graceful errors.

--------------------------------------------------

2.5 TLS verification policy

Verify:
- TLS verify=True default
- no hidden verify=False fallback

Disable verify only by explicit setting.

==================================================
SECTION 3. STORAGE AND FILE SECURITY
==================================================

3.1 Runtime storage audit

Verify ALL runtime files stored only in:

%APPDATA%/Excel_to_XML/

Files:
- app_data.db
- logs
- backups
- settings
- master.key
- temp if persistent

Forbidden:
runtime files near executable.

--------------------------------------------------

3.2 XML temp file cleanup

Audit XML workflow.

Temporary XML files may contain personal data.

Requirements:
- create in temp directory
- auto delete after send/export

Verify:
no temp XML remains after operation.

--------------------------------------------------

3.3 Temporary reports cleanup

Audit temporary files:
- DOCX
- protocols
- reports

Temporary files:
cleanup after use.

Persistent exports:
save only to user-selected path.

--------------------------------------------------

3.4 Backup audit

Verify DB backups.

Requirements:
- backups preserve encrypted fields
- no plaintext exports created unintentionally

==================================================
SECTION 4. LOGGING AND AUDIT
==================================================

4.1 Sensitive logging audit

Verify logs never contain:

- SNILS
- FIO
- proxy passwords
- tokens
- API keys
- XML payloads
- authorization headers

Audit all logger calls.

Mask examples:

14566772094 -> 145****094

--------------------------------------------------

4.2 Log rotation

Audit logging handlers.

If missing:
implement rotation.

Preferred:
RotatingFileHandler or TimedRotatingFileHandler

Prevent unlimited log growth.

Recommended:
- maxBytes
- backupCount

--------------------------------------------------

4.3 Logging levels

Production default:
INFO

DEBUG:
only via explicit debug setting.

==================================================
SECTION 5. DATABASE STABILITY
==================================================

5.1 SQLite configuration audit

Verify:

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=FULL or NORMAL;

Ensure settings applied consistently.

--------------------------------------------------

5.2 DB shutdown

Verify all DB connections close correctly.

Use:
DatabaseManager.close_all()

Call on app exit.

--------------------------------------------------

5.3 Large dataset stability

Test database with:

- 100 employees
- 1000 employees
- 5000+ employees

Verify:
- search
- filtering
- imports
- journal
- planning

No crashes or major slowdown.

==================================================
SECTION 6. FUNCTIONAL TESTING
==================================================

6.1 Employee Summary (2.7)

Test:

- Excel import
- manual add/edit
- employee search by SNILS
- duplicate detection
- encrypted persistence
- registry sync
- status logic
- filters
- exports

Verify full workflow.

--------------------------------------------------

6.2 Training Plan (2.8)

Test:

- generate next year plan
- overdue detection
- recommendations
- filters
- export

Verify business rules.

--------------------------------------------------

6.3 Journal

Test:

- add/edit/delete
- filters
- statuses
- SetId
- exports

--------------------------------------------------

6.4 Monitoring

Test:

- logs display
- refresh
- filters
- statuses

--------------------------------------------------

6.5 XML workflow

Test:

- XML generation
- validation
- send
- temp cleanup

==================================================
SECTION 7. UI/PERFORMANCE TESTING
==================================================

7.1 Long-running tasks

Verify worker threads for:

- Excel import
- API sync
- XML generation
- batch requests

UI requirements:
- no freeze
- progress bar
- status updates

--------------------------------------------------

7.2 Large tables

Verify performance for:
- employee summary
- journal

Large datasets must remain usable.

==================================================
SECTION 8. TECHNICAL SPECIFICATION SYNCHRONIZATION
==================================================

Update technical specification to match actual architecture.

Remove obsolete references:

- app_data.db.enc
- encrypt DB on shutdown
- decrypt DB on startup
- JSON storage architecture
- workers_data.json
- exam_journal.json
- httpx
- urllib
- pycurl

Replace with actual architecture:

Storage:
- plain SQLite app_data.db

Encryption:
- field-level encryption
- SNILS
- names

Key management:
- DPAPI
- master.key

Runtime storage:
%APPDATA%/Excel_to_XML/

Networking:
- requests
- wininet fallback

--------------------------------------------------

8.1 Section 2.7 / 2.8 review

Resolve ambiguity:

Current TЗ references:
- current year plan
- next year plan

Document actual implemented behavior.

If both supported:
describe both clearly.

--------------------------------------------------

8.2 Section numbering audit

Verify numbering consistency across TЗ.

==================================================
SECTION 9. README UPDATE
==================================================

Update README.md.

Required sections:

1. Architecture overview
   - PySide6
   - SQLite
   - repositories

2. Security model
   - field encryption
   - DPAPI
   - AppData

3. Corporate networking
   - requests
   - wininet
   - proxy support

4. Build instructions
   - PyInstaller
   - no UPX
   - onedir

5. Runtime paths

6. Troubleshooting
   - proxy
   - TLS
   - logs

7. Security notes
   - fallback key mode
   - storage model

==================================================
SECTION 10. RELEASE READINESS REPORT
==================================================

Return:

1. Bugs fixed
2. Remaining issues
3. Security issues
4. Functional test results
5. Load test results
6. Missing TЗ items
7. Updated ТЗ summary на русском языке
8. Updated README summary на русском языке
9. Production readiness score
10. Recommended next improvements