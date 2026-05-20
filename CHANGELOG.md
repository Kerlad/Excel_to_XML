# Changelog

## v1.0.0
- Employee Summary tab
- Training Plan generation
- Monitoring dashboard
- XML generation compliant with educated_person_import_v1.0.9.xsd
- Mintrud API integration (send XML, query by SetId/SNILS)
- Security hardening (field-level encryption, Fernet + DPAPI)
- AppData runtime migration
- Dual HTTP transport (requests + WinINet) with auto fallback
- Proxy support (off/auto/manual)
- Protocol generation from DOCX template
- Exam journal with status tracking
- Theme support (light/dark)
- Multi-program support per employee

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
- **Note:** This functionality has not been tested due to lack of a `.sig` file
- Updated help, README, and technical specification docs

## v1.0.1
- Documentation restructure: README split into main + docs/SECURITY.md + docs/API_MINTTRUD.md
- Updated Техническое_задание_2.md with implemented features (employee-level status, current snapshot, employee-level plan, transport backends, audit, backup, API format, network diagnostics)
- Added app icon to README
