- [ ] Perform focused security hardening, validation improvements, code cleanup and test preparation.

  Project:
  Python desktop application (PySide6 + SQLite + requests + WinINet + Mintrud API integration).

  IMPORTANT:
  - do NOT modify repository structure
  - do NOT touch git/github configuration
  - do NOT change business logic
  - do NOT remove requests backend
  - do NOT remove wininet backend
  - preserve current architecture

  Goal:
  Improve security, code quality, validation and maintainability based on audit review.

  ==================================================
  SECTION 1. SECURITY IMPROVEMENTS
  ==================================================

  1.1 Improve fallback encryption mode

  File:
  utils/crypto.py

  Current behavior:
  If DPAPI unavailable, master.key is stored as plaintext fallback.

  Current code:
  kf.write_bytes(raw)

  Problem:
  Reduced security if AppData compromised.

  Required:
  Keep current fallback architecture (NO master password dialogs).

  Implement improvements:

  1. Keep fallback key generation.

  2. Add file permission hardening where possible.

  For Windows:
  restrict file access to current user only if possible.

  3. Improve logging.

  Keep warning:
  "DPAPI unavailable, using local fallback key (reduced security)"

  4. Document fallback mode in code comments.

  IMPORTANT:
  - do NOT add password prompts
  - do NOT introduce UX changes
  - do NOT break existing keys

  Goal:
  safe degraded mode without usability issues.

  --------------------------------------------------

  1.2 Differentiate decrypt warnings

  File:
  utils/crypto.py

  Current:
  logger.warning("Decrypt failed")

  Problem:
  Cannot distinguish source of failure.

  Replace with:

  - logger.warning("Decrypt value failed")
  - logger.warning("Decrypt data failed")

  ==================================================
  SECTION 2. INPUT VALIDATION
  ==================================================

  2.1 SNILS validation hardening

  File:
  api/mintrud_api.py

  Current:
  snils.replace('-', '').replace(' ', '')

  Problem:
  Insufficient validation.

  Implement:

  1. Normalize SNILS:
  remove all non-digits.

  Example:
  re.sub(r"\D", "", snils)

  2. Validate strict format:
  11 digits only.

  Example:
  if not re.fullmatch(r"\d{11}", snils_clean):
      raise ValueError("Invalid SNILS format")

  3. Reject invalid values early.

  Goal:
  prevent malformed requests.

  --------------------------------------------------

  2.2 XML escaping

  Audit all XML generation and API payload creation.

  If XML values inserted manually:

  escape user values using safe XML escaping.

  Example:
  xml.sax.saxutils.escape()

  or equivalent XML-safe generation.

  Fields to review:
  - SNILS
  - names
  - organization data
  - free text values

  Goal:
  prevent malformed XML and injection issues.

  ==================================================
  SECTION 3. CODE CLEANUP
  ==================================================

  3.1 Theme palette deduplication

  File:
  main.py

  Problem:
  Theme palette logic duplicated.

  Likely duplicated in:
  - __init__
  - _apply_theme

  Refactor:

  Create helper:

  def _create_palette(theme: str):
      ...

  Use helper in all theme application locations.

  Goal:
  single source of theme palette logic.

  IMPORTANT:
  No visual behavior changes.

  --------------------------------------------------

  3.2 Refactor validate_row()

  File:
  xlsx_importer.py

  Problem:
  validate_row() too large (~150 lines).

  Refactor into field validators.

  Suggested structure:

  class FieldValidator:
      @staticmethod
      def validate_snils(...)

      @staticmethod
      def validate_program(...)
      
      @staticmethod
      def validate_date(...)
      
      @staticmethod
      def validate_required(...)

  Then simplify validate_row().

  Goal:
  - smaller function
  - easier testing
  - easier maintenance

  IMPORTANT:
  Preserve current validation behavior.

  ==================================================
  SECTION 4. TEST PREPARATION
  ==================================================

  4.1 Add test dependencies

  Create or update:

  requirements-dev.txt

  Include:
  pytest>=7.0
  pytest-cov>=4.0
  pytest-mock>=3.10

  --------------------------------------------------

  4.2 Add minimal smoke tests

  Create tests for critical logic.

  Required:

  tests/test_crypto.py
  tests/test_database.py
  tests/test_xml.py

  --------------------------------------------------

  4.3 Crypto tests

  Implement:

  1. encrypt/decrypt roundtrip

  Test:
  encrypt_value()
  decrypt_value()

  2. encrypt_data/decrypt_data roundtrip

  3. corrupted payload handling

  Expected:
  returns safe fallback
  does not crash

  --------------------------------------------------

  4.4 Database tests

  Implement basic tests:

  - create DB
  - insert employee
  - retrieve employee
  - encrypted fields persisted

  --------------------------------------------------

  4.5 XML tests

  Implement:

  - XML generation
  - required fields present
  - XML escaping works
  - malformed values handled safely

  ==================================================
  SECTION 5. MANUAL QA CHECKS
  ==================================================

  Add checklist or notes for manual testing.

  Required manual checks:

  1. XML temp cleanup

  Verify:
  temporary XML files deleted after:
  - export
  - send

  2. Large import

  Test:
  - 100 employees
  - 1000 employees
  - 5000 employees

  Check:
  - no UI freeze
  - no crashes

  3. Proxy auth

  Test:
  - no proxy
  - proxy without auth
  - proxy with auth
  - invalid credentials

  4. Backup/restore

  Verify:
  - backup creation
  - restore
  - encrypted fields preserved

  ==================================================
  SECTION 6. OPTIONAL CODE QUALITY IMPROVEMENTS
  ==================================================

  Apply only if trivial and safe.

  1. Improve type hints where obvious.

  Examples:
  Sequence[Any]
  Optional[str]

  2. Review broad except Exception blocks.

  Keep broad catches only where justified:
  - crypto
  - network
  - UI boundaries

  Avoid unnecessary broad catches elsewhere.

  IMPORTANT:
  No major typing refactor.
  No mypy overhaul.

  ==================================================
  SECTION 7. FINAL OUTPUT
  ==================================================

  Return:

  1. Security improvements applied
  2. Validation improvements applied
  3. Refactoring completed
  4. Tests added
  5. Manual QA checklist results
  6. Remaining technical debt
  7. Any unresolved risks

---



STEP 2

Perform repository cleanup and Git hygiene hardening.

Project:
Python desktop application (PySide6 + SQLite + requests + WinINet).

Goal:
Make repository clean, maintainable, and suitable for:
- corporate internal use
- public GitHub portfolio
- project defense / presentation

IMPORTANT:
Do NOT break code.
Do NOT change business logic.
Focus only on repository structure, Git hygiene, documentation and project organization.

==================================================
1. REPOSITORY STRUCTURE CLEANUP
==================================================

Reorganize repository root.

Target structure:

Excel_to_XML/
├─ api/
├─ db/
├─ models/
├─ services/
├─ ui/
├─ utils/
├─ docs/
├─ resources/
├─ templates/
├─ tests/
├─ build/              (ignored)
├─ dist/               (ignored)
├─ README.md
├─ CHANGELOG.md
├─ requirements.txt
├─ .gitignore
├─ main.py

Tasks:

1. Move documentation files into docs/

Move:
- API.pdf
- technical specifications
- project notes
- manuals

Target:
docs/

--------------------------------------------------

2. Move templates into templates/

Move:
- Protokol_proverki_znanii_OT.docx
- XML templates
- report templates

Target:
templates/

--------------------------------------------------

3. Move static assets into resources/

Move:
- ico.ico
- images
- icons
- diagrams

Target:
resources/

--------------------------------------------------

4. Review root files.

Review:
- Launcher.cs
- err.txt
- out.txt

Rules:
- remove obsolete files
- move relevant files
- delete debug artifacts

==================================================
2. GITIGNORE HARDENING
==================================================

Review and improve .gitignore.

Ensure ignored:

# Python
__pycache__/
*.pyc
*.pyo

# Build
build/
dist/

# Runtime
log/
logs/
temp/
tmp/
backups/
generated/
exports/

# Databases
*.db
*.db.*
*.sqlite

# Secrets
master.key
api_key.json
org_settings.json
proxy_settings.json
commission_data.json

# XML
*.xml

# Logs
*.log

# Debug
err.txt
out.txt
*.tmp
*.bak

# OS
.DS_Store
Thumbs.db

IMPORTANT:
Do not ignore required templates/resources.

==================================================
3. REMOVE TRACKED RUNTIME FILES
==================================================

Audit repository for tracked files that should not be versioned.

Remove from git tracking if found:

- app_data.db
- master.key
- logs
- backups
- temp files
- xml outputs
- debug outputs
- generated reports

Preserve local files.

Equivalent actions:
git rm --cached where needed.

==================================================
4. DOCUMENTATION IMPROVEMENT
==================================================

Update README.md.

README should be concise and professional.

Required sections:

1. Project overview

2. Features
- Excel import
- employee summary
- training plan
- XML generation
- API integration
- monitoring

3. Architecture
- PySide6
- SQLite
- requests
- WinINet

4. Security
- field encryption
- DPAPI
- AppData runtime storage

5. Installation

6. Build instructions

7. Troubleshooting

8. Project structure

Keep README concise.

Move detailed docs to:
docs/

==================================================
5. ADD CHANGELOG
==================================================

Create CHANGELOG.md

Structure:

# Changelog

## v1.0.0
- Employee Summary
- Training Plan
- Monitoring
- XML generation
- Mintrud API integration
- Security hardening
- AppData runtime migration
- DPAPI support

==================================================
6. OPTIONAL TEST STRUCTURE
==================================================

Create tests/ directory.

If tests absent:
create placeholder structure.

Example:
tests/
- test_crypto.py
- test_database.py
- test_xml.py

Do not implement full tests unless trivial.

==================================================
7. FINAL REPOSITORY AUDIT
==================================================

Perform final audit.

Check:
- repository root cleanliness
- ignored files
- tracked secrets
- runtime artifacts
- documentation consistency

Return:

1. Files moved
2. Files deleted
3. .gitignore changes
4. README changes
5. Remaining cleanup recommendations
6. Final repository structure tree