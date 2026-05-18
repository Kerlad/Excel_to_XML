import logging
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class WorkersDataRepo:
    TABLE = "workers_data"

    @staticmethod
    def get_all():
        db = DatabaseManager.get_instance()
        return db.fetchall(f"SELECT * FROM {WorkersDataRepo.TABLE} ORDER BY id")

    @staticmethod
    def get_by_id(record_id: int):
        db = DatabaseManager.get_instance()
        return db.fetchone(f"SELECT * FROM {WorkersDataRepo.TABLE} WHERE id = ?", (record_id,))

    @staticmethod
    def get_existing_keys():
        db = DatabaseManager.get_instance()
        rows = db.fetchall(f"SELECT snils, program FROM {WorkersDataRepo.TABLE}")
        return {(row['snils'], str(row['program'])) for row in rows}

    @staticmethod
    def add(record: dict) -> int:
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            cur = conn.execute(f"""
                INSERT INTO {WorkersDataRepo.TABLE}
                (last_name, first_name, middle_name, snils, position,
                 employer_inn, employer_title, tc_inn, tc_title,
                 result, program, date, protocol)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get('last_name', ''),
                record.get('first_name', ''),
                record.get('middle_name', ''),
                record.get('snils', ''),
                record.get('position', ''),
                record.get('employer_inn', ''),
                record.get('employer_title', ''),
                record.get('tc_inn', ''),
                record.get('tc_title', ''),
                record.get('result', ''),
                int(record.get('program', 0)),
                record.get('date', ''),
                record.get('protocol', ''),
            ))
            return cur.lastrowid

    @staticmethod
    def add_many(records: list) -> int:
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.executemany(f"""
                INSERT INTO {WorkersDataRepo.TABLE}
                (last_name, first_name, middle_name, snils, position,
                 employer_inn, employer_title, tc_inn, tc_title,
                 result, program, date, protocol)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(
                r.get('last_name', ''),
                r.get('first_name', ''),
                r.get('middle_name', ''),
                r.get('snils', ''),
                r.get('position', ''),
                r.get('employer_inn', ''),
                r.get('employer_title', ''),
                r.get('tc_inn', ''),
                r.get('tc_title', ''),
                r.get('result', ''),
                int(r.get('program', 0)),
                r.get('date', ''),
                r.get('protocol', ''),
            ) for r in records])
        return len(records)

    @staticmethod
    def update(record_id: int, record: dict):
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute(f"""
                UPDATE {WorkersDataRepo.TABLE}
                SET last_name=?, first_name=?, middle_name=?, snils=?, position=?,
                    employer_inn=?, employer_title=?, tc_inn=?, tc_title=?,
                    result=?, program=?, date=?, protocol=?,
                    updated_at=datetime('now')
                WHERE id=?
            """, (
                record.get('last_name', ''),
                record.get('first_name', ''),
                record.get('middle_name', ''),
                record.get('snils', ''),
                record.get('position', ''),
                record.get('employer_inn', ''),
                record.get('employer_title', ''),
                record.get('tc_inn', ''),
                record.get('tc_title', ''),
                record.get('result', ''),
                int(record.get('program', 0)),
                record.get('date', ''),
                record.get('protocol', ''),
                record_id,
            ))

    @staticmethod
    def delete(record_id: int):
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute(f"DELETE FROM {WorkersDataRepo.TABLE} WHERE id = ?", (record_id,))

    @staticmethod
    def clear():
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute(f"DELETE FROM {WorkersDataRepo.TABLE}")

    @staticmethod
    def count() -> int:
        db = DatabaseManager.get_instance()
        row = db.fetchone(f"SELECT COUNT(*) as cnt FROM {WorkersDataRepo.TABLE}")
        return row['cnt'] if row else 0
