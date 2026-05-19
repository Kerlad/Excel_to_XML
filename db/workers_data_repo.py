import logging
from .database import DatabaseManager
from utils.crypto import encrypt_value, decrypt_value, hash_for_search

logger = logging.getLogger(__name__)


def _encrypt_row(r: dict) -> dict:
    return dict(r) if 'last_name_enc' not in r else {
        'id': r['id'], 'last_name': decrypt_value(r['last_name_enc']),
        'first_name': decrypt_value(r['first_name_enc']),
        'middle_name': decrypt_value(r['middle_name_enc']),
        'snils': decrypt_value(r['snils_enc']),
        'position': r['position'], 'employer_inn': r['employer_inn'],
        'employer_title': r['employer_title'], 'tc_inn': r['tc_inn'],
        'tc_title': r['tc_title'], 'result': r['result'],
        'program': r['program'], 'date': r['date'], 'protocol': r['protocol'],
        'created_at': r['created_at'], 'updated_at': r['updated_at'],
    }


class WorkersDataRepo:
    TABLE = "workers_data"

    @staticmethod
    def get_all():
        db = DatabaseManager.get_instance()
        return [_encrypt_row(r) for r in db.fetchall(f"SELECT * FROM {WorkersDataRepo.TABLE} ORDER BY id")]

    @staticmethod
    def get_by_id(rid: int):
        db = DatabaseManager.get_instance()
        r = db.fetchone(f"SELECT * FROM {WorkersDataRepo.TABLE} WHERE id = ?", (rid,))
        return _encrypt_row(r) if r else None

    @staticmethod
    def get_existing_keys():
        db = DatabaseManager.get_instance()
        rows = db.fetchall(f"SELECT snils_hash, program FROM {WorkersDataRepo.TABLE}")
        return {(r['snils_hash'], str(r['program'])) for r in rows}

    @staticmethod
    def add(record: dict) -> int:
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            cur = conn.execute(f"""
                INSERT INTO {WorkersDataRepo.TABLE}
                (last_name_enc, first_name_enc, middle_name_enc, snils_enc, snils_hash,
                 position, employer_inn, employer_title, tc_inn, tc_title,
                 result, program, date, protocol)
                VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?)
            """, (
                encrypt_value(record.get('last_name','')),
                encrypt_value(record.get('first_name','')),
                encrypt_value(record.get('middle_name','')),
                encrypt_value(record.get('snils','')),
                hash_for_search(record.get('snils','')),
                record.get('position',''), record.get('employer_inn',''),
                record.get('employer_title',''), record.get('tc_inn',''),
                record.get('tc_title',''), record.get('result',''),
                int(record.get('program',0)), record.get('date',''),
                record.get('protocol',''),
            ))
            return cur.lastrowid

    @staticmethod
    def add_many(records: list) -> int:
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.executemany(f"""
                INSERT INTO {WorkersDataRepo.TABLE}
                (last_name_enc, first_name_enc, middle_name_enc, snils_enc, snils_hash,
                 position, employer_inn, employer_title, tc_inn, tc_title,
                 result, program, date, protocol)
                VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?)
            """, [(
                encrypt_value(r.get('last_name','')),
                encrypt_value(r.get('first_name','')),
                encrypt_value(r.get('middle_name','')),
                encrypt_value(r.get('snils','')),
                hash_for_search(r.get('snils','')),
                r.get('position',''), r.get('employer_inn',''),
                r.get('employer_title',''), r.get('tc_inn',''),
                r.get('tc_title',''), r.get('result',''),
                int(r.get('program',0)), r.get('date',''), r.get('protocol',''),
            ) for r in records])
        return len(records)

    @staticmethod
    def update(rid: int, record: dict):
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute(f"""
                UPDATE {WorkersDataRepo.TABLE}
                SET last_name_enc=?, first_name_enc=?, middle_name_enc=?,
                    snils_enc=?, snils_hash=?, position=?, employer_inn=?,
                    employer_title=?, tc_inn=?, tc_title=?, result=?,
                    program=?, date=?, protocol=?, updated_at=datetime('now')
                WHERE id=?
            """, (
                encrypt_value(record.get('last_name','')),
                encrypt_value(record.get('first_name','')),
                encrypt_value(record.get('middle_name','')),
                encrypt_value(record.get('snils','')),
                hash_for_search(record.get('snils','')),
                record.get('position',''), record.get('employer_inn',''),
                record.get('employer_title',''), record.get('tc_inn',''),
                record.get('tc_title',''), record.get('result',''),
                int(record.get('program',0)), record.get('date',''),
                record.get('protocol',''), rid,
            ))

    @staticmethod
    def delete(rid: int):
        DatabaseManager.get_instance().execute(
            f"DELETE FROM {WorkersDataRepo.TABLE} WHERE id = ?", (rid,))

    @staticmethod
    def clear():
        DatabaseManager.get_instance().execute(f"DELETE FROM {WorkersDataRepo.TABLE}")

    @staticmethod
    def count() -> int:
        r = DatabaseManager.get_instance().fetchone(f"SELECT COUNT(*) as cnt FROM {WorkersDataRepo.TABLE}")
        return r['cnt'] if r else 0
