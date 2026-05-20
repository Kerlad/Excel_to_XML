import logging
from .database import DatabaseManager

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS workers_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    last_name_enc TEXT NOT NULL DEFAULT '',
    first_name_enc TEXT NOT NULL DEFAULT '',
    middle_name_enc TEXT NOT NULL DEFAULT '',
    snils_enc TEXT NOT NULL DEFAULT '',
    snils_hash TEXT NOT NULL DEFAULT '',
    position TEXT NOT NULL DEFAULT '',
    employer_inn TEXT NOT NULL DEFAULT '',
    employer_title TEXT NOT NULL DEFAULT '',
    tc_inn TEXT NOT NULL DEFAULT '',
    tc_title TEXT NOT NULL DEFAULT '',
    result TEXT NOT NULL DEFAULT '',
    program INTEGER NOT NULL DEFAULT 0,
    date TEXT NOT NULL DEFAULT '',
    protocol TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_workers_snils_hash ON workers_data(snils_hash);
CREATE INDEX IF NOT EXISTS idx_workers_program ON workers_data(program);

CREATE TABLE IF NOT EXISTS exam_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    send_date TEXT NOT NULL DEFAULT '',
    set_id TEXT NOT NULL DEFAULT '',
    xml_file TEXT NOT NULL DEFAULT '',
    last_name_enc TEXT NOT NULL DEFAULT '',
    first_name_enc TEXT NOT NULL DEFAULT '',
    middle_name_enc TEXT NOT NULL DEFAULT '',
    snils_enc TEXT NOT NULL DEFAULT '',
    snils_hash TEXT NOT NULL DEFAULT '',
    position TEXT NOT NULL DEFAULT '',
    program_id TEXT NOT NULL DEFAULT '',
    program_title TEXT NOT NULL DEFAULT '',
    exam_date TEXT NOT NULL DEFAULT '',
    protocol TEXT NOT NULL DEFAULT '',
    result TEXT NOT NULL DEFAULT '',
    base_no TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_exam_journal_snils_hash ON exam_journal(snils_hash);
CREATE INDEX IF NOT EXISTS idx_exam_journal_setid ON exam_journal(set_id);
CREATE INDEX IF NOT EXISTS idx_exam_journal_status ON exam_journal(status);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snils_enc TEXT UNIQUE NOT NULL,
    snils_hash TEXT UNIQUE NOT NULL,
    last_name_enc TEXT NOT NULL DEFAULT '',
    first_name_enc TEXT NOT NULL DEFAULT '',
    middle_name_enc TEXT NOT NULL DEFAULT '',
    position TEXT NOT NULL DEFAULT '',
    required_programs TEXT NOT NULL DEFAULT '',
    last_sync TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_employees_snils_hash ON employees(snils_hash);

CREATE TABLE IF NOT EXISTS employee_programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    program_id INTEGER NOT NULL,
    need_training INTEGER NOT NULL DEFAULT 0,
    exam_date TEXT,
    protocol TEXT,
    base_no TEXT,
    result INTEGER,
    status TEXT,
    updated_at TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    UNIQUE(employee_id, program_id)
);

CREATE INDEX IF NOT EXISTS idx_ep_employee ON employee_programs(employee_id);
CREATE INDEX IF NOT EXISTS idx_ep_program ON employee_programs(program_id);
CREATE INDEX IF NOT EXISTS idx_ep_status ON employee_programs(status);
"""


def create_schema():
    db = DatabaseManager.get_instance()
    with db.transaction() as conn:
        conn.executescript(SCHEMA_SQL)
        try:
            conn.execute(
                "DELETE FROM workers_data WHERE id NOT IN "
                "(SELECT MIN(id) FROM workers_data GROUP BY snils_hash, program, date)"
            )
        except Exception:
            pass
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_workers_unique "
                "ON workers_data(snils_hash, program, date)"
            )
        except Exception as e:
            logger.warning("Could not create unique index on workers_data: %s", e)
    logger.info("Schema created/verified")
