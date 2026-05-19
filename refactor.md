Perform full final refactor, audit and production hardening of the project.

Project:
Windows desktop application (PySide6 + SQLite + requests + WinINet + PyInstaller)
for occupational safety training registry, XML generation and Mintrud API integration.

Current state:
- antivirus false positives resolved
- runtime moved to AppData
- full DB encryption removed
- field-level encryption implemented
- SQLite storage active
- requests + wininet only

Goal:
Finalize project for stable corporate use.

Requirements:
- do NOT break business logic
- do NOT remove requests backend
- do NOT remove wininet backend
- preserve existing UI flows
- preserve SQLite architecture
- preserve field-level encryption of personal data

==================================================
SECTION 1. CODE SECURITY CLEANUP
==================================================

1.1 Remove obsolete dangerous crypto functions

File:
utils/crypto.py

Delete completely:
- encrypt_file()
- decrypt_file()

These functions are obsolete after field-level encryption
and resemble ransomware-like behavior.

No file encryption lifecycle should remain anywhere.

Search whole project for:
- encrypt_file(
- decrypt_file(
- unlink(
- remove(

and verify no obsolete encryption workflow remains.

--------------------------------------------------

1.2 Harden decrypt behavior

In decrypt_value():

Current behavior may return encrypted blob on failure.

Bad:
return enc

Replace with:
- return empty string or safe placeholder
- generic error logging only

Required:
decrypt failures must not leak encrypted blobs to UI.

Example:
return ""

--------------------------------------------------

1.3 Improve fallback key generation

Current fallback based on USERNAME hash is weak.

Remove any logic like:
SHA256(USERNAME)

If DPAPI unavailable:
- generate random 32-byte key
- store locally in AppData/master.key

Use:
os.urandom(32)

Do not derive crypto keys from:
- username
- computer name
- domain name

==================================================
SECTION 2. CORPORATE STORAGE SECURITY
==================================================

2.1 AppData path correctness

Replace hardcoded:
Path.home()/AppData/Roaming

with:

os.environ.get("APPDATA")

Fallback allowed only if APPDATA unavailable.

Target runtime directory:

%APPDATA%/Excel_to_XML/

--------------------------------------------------

2.2 Runtime files location

Ensure ONLY runtime files stored in AppData:

- app_data.db
- logs/
- backups/
- master.key
- settings/
- api configs

Nothing runtime-related near executable.

Forbidden:
./data
./logs
./temp
local sqlite near exe

--------------------------------------------------

2.3 Remove bundled runtime configs

Do not ship in repository/build:
- api_key.json
- org_settings.json
- commission_data.json
- proxy settings

Instead:
generate defaults on first launch.

Allowed:
*.example templates only.

==================================================
SECTION 3. PERSONAL DATA SECURITY
==================================================

3.1 Verify field-level encryption coverage

Sensitive fields MUST be encrypted:

workers_data:
- snils
- last_name
- first_name
- middle_name

employees:
- snils
- names

exam_journal:
- snils
- names

Optional:
- protocol
- base_no

Verify all repositories consistently use:
encrypt_value()
decrypt_value()

--------------------------------------------------

3.2 Searchable hashes

Sensitive searchable fields require hashes.

Ensure:
snils_hash exists wherever SNILS searched.

Use:
SHA256(normalized_snils)

Search only by hash.

Do not search decrypted values.

--------------------------------------------------

3.3 Backup validation

Database backups must preserve encrypted fields.

Verify backups do not create plaintext exports.

Since DB is field-encrypted:
backup of DB is allowed.

But ensure no plaintext serialization.

==================================================
SECTION 4. PROXY AND NETWORK SECURITY
==================================================

4.1 Keep only approved backends

Allowed:
- requests
- wininet

Remove all dead network code if still present.

Forbidden:
- httpx
- urllib backend
- pycurl
- ntlm experimental backends

--------------------------------------------------

4.2 Manual proxy auth

Audit manual proxy mode.

Requests backend must support:

http://username:password@host:port

or equivalent auth handling.

Currently manual auth may be incomplete.

Fix.

--------------------------------------------------

4.3 Proxy credential storage

Audit proxy password storage.

Preferred:
Windows Credential Manager.

If not implemented:
centralize encryption using utils.crypto.

Do not keep separate crypto implementations.

Remove local crypto logic from proxy manager.

--------------------------------------------------

4.4 Network hardening

Verify:
- TLS verify=True by default
- no silent SSL disable
- explicit UI option only

Requests:
- timeout configured
- retry policy
- backoff

Recommended:
retries=3

==================================================
SECTION 5. LOGGING AND AUDIT
==================================================

5.1 Logging sanitization

Logs must never contain:
- SNILS
- FIO
- API keys
- tokens
- proxy passwords
- XML payloads

Implement or verify:
mask_sensitive()

Examples:
14566772094 -> 145****094

--------------------------------------------------

5.2 Logging verbosity

Production default:
INFO

DEBUG only via settings/debug mode.

Avoid root logger DEBUG by default.

--------------------------------------------------

5.3 Audit trail

Add/verify audit log.

Record:
- send_xml
- query_registry
- import_excel
- generate_plan

Fields:
- timestamp
- action
- user
- set_id if exists

Do NOT log personal data.

==================================================
SECTION 6. DATABASE STABILITY
==================================================

6.1 SQLite pragmas

Verify:

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

Recommended:
PRAGMA synchronous=NORMAL

or FULL.

--------------------------------------------------

6.2 Graceful shutdown

Ensure sqlite connections close properly.

Add:
DatabaseManager.close_all()

Use on app shutdown.

Avoid dangling connections.

--------------------------------------------------

6.3 Persistent sessions

Requests backend currently may recreate sessions.

Use persistent:
requests.Session()

Reuse for batch requests.

==================================================
SECTION 7. FILE/TEMP SECURITY
==================================================

7.1 XML temporary files

Audit XML generation.

Temporary XML files containing personal data must:
- use temp dir
- auto cleanup after send/export

Avoid persistent temp XML.

--------------------------------------------------

7.2 Temporary DOCX/protocol files

Check protocol generation.

Temp files must not accumulate.

Cleanup after use if temporary.

==================================================
SECTION 8. UI / PERFORMANCE
==================================================

8.1 Large tables

Audit all large tables.

For large datasets:
use:
QTableView + model

Avoid QTableWidget for:
- employee summary
- journal

--------------------------------------------------

8.2 Background tasks

Long operations must run in worker threads:
- API requests
- batch registry sync
- Excel import
- XML generation

UI must not freeze.

Add:
- progress bars
- cancel buttons

==================================================
SECTION 9. TECHNICAL SPECIFICATION AUDIT
==================================================

Compare codebase with attached technical specification.

Find:
- missing features
- partially implemented sections
- mismatches

Focus especially:

2.7 Employee Summary:
- employee import
- registry sync
- status logic
- filters
- exports

2.8 Training Plan:
- next year plan generation
- overdue logic
- recommendations

Journal:
- status filters
- SetId
- export

Monitoring:
- logs
- filtering
- refresh

--------------------------------------------------

Update technical specification according to implemented architecture changes.

Required TЗ changes:

1. Replace full DB encryption requirements
(old app_data.db.enc lifecycle)

WITH:

Field-level encryption:
- SNILS
- FIO

Plain SQLite:
app_data.db

2. Update storage requirements:

Runtime path:
%APPDATA%/Excel_to_XML/

3. Update key management:

DPAPI + master.key.

4. Remove obsolete requirements referencing:
- db encrypt on shutdown
- db decrypt on startup

Modify TЗ accordingly.

==================================================
SECTION 10. README UPDATE
==================================================

Update README.md.

Add/update:

1. Architecture overview:
- PySide6
- SQLite
- repositories
- encryption model

2. Security model:
- field-level encryption
- DPAPI
- AppData storage

3. Corporate network support:
- requests
- wininet
- proxy autodetection

4. Build instructions:
- PyInstaller settings
- no UPX
- onedir build

5. Runtime storage locations.

6. Troubleshooting:
- proxy issues
- TLS issues
- logs location

==================================================
SECTION 11. FINAL OUTPUT
==================================================

Return:

1. Critical issues found
2. Security issues found
3. Bugs found
4. Missing TЗ features
5. Files changed
6. Updated TЗ summary
7. Updated README summary
8. Final architecture summary
9. Production readiness assessment
10. Вся документация - на русском языке