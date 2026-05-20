import logging
from datetime import datetime
from typing import List, Optional

from .database import DatabaseManager
from utils.crypto import encrypt_value, decrypt_value, hash_for_search

logger = logging.getLogger(__name__)


def _decrypt_emp(r: dict) -> dict:
    return {
        'id': r['id'],
        'snils': decrypt_value(r['snils_enc']),
        'last_name': decrypt_value(r['last_name_enc']),
        'first_name': decrypt_value(r['first_name_enc']),
        'middle_name': decrypt_value(r['middle_name_enc']),
        'position': r['position'],
        'required_programs': r['required_programs'],
        'last_sync': r['last_sync'],
        'created_at': r['created_at'],
        'updated_at': r['updated_at'],
    }


class EmployeesRepo:
    TABLE = "employees"

    @staticmethod
    def get_all(**kwargs) -> List[dict]:
        db = DatabaseManager.get_instance()
        return [_decrypt_emp(r) for r in db.fetchall(f"SELECT * FROM {EmployeesRepo.TABLE} ORDER BY last_name_enc, first_name_enc")]

    @staticmethod
    def get_by_id(emp_id: int) -> Optional[dict]:
        db = DatabaseManager.get_instance()
        r = db.fetchone(f"SELECT * FROM {EmployeesRepo.TABLE} WHERE id = ?", (emp_id,))
        return _decrypt_emp(r) if r else None

    @staticmethod
    def get_by_snils(snils: str) -> Optional[dict]:
        db = DatabaseManager.get_instance()
        r = db.fetchone(f"SELECT * FROM {EmployeesRepo.TABLE} WHERE snils_hash = ?", (hash_for_search(snils),))
        return _decrypt_emp(r) if r else None

    @staticmethod
    def upsert(employee: dict) -> int:
        db = DatabaseManager.get_instance()
        snils = employee.get('snils', '')
        existing = EmployeesRepo.get_by_snils(snils)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with db.transaction() as conn:
            if existing:
                conn.execute(f"""
                    UPDATE {EmployeesRepo.TABLE}
                    SET last_name_enc=?, first_name_enc=?, middle_name_enc=?,
                        snils_enc=?, snils_hash=?, position=?,
                        required_programs=?, updated_at=?
                    WHERE id=?
                """, (
                    encrypt_value(employee.get('last_name','')),
                    encrypt_value(employee.get('first_name','')),
                    encrypt_value(employee.get('middle_name','')),
                    encrypt_value(snils), hash_for_search(snils),
                    employee.get('position',''),
                    employee.get('required_programs',''), now, existing['id'],
                ))
                return existing['id']
            else:
                cur = conn.execute(f"""
                    INSERT INTO {EmployeesRepo.TABLE}
                    (snils_enc, snils_hash, last_name_enc, first_name_enc, middle_name_enc,
                     position, required_programs, last_sync, created_at, updated_at)
                    VALUES (?,?,?,?,?, ?,?,?,?,?)
                """, (
                    encrypt_value(snils), hash_for_search(snils),
                    encrypt_value(employee.get('last_name','')),
                    encrypt_value(employee.get('first_name','')),
                    encrypt_value(employee.get('middle_name','')),
                    employee.get('position',''), employee.get('required_programs',''),
                    employee.get('last_sync'), now, now,
                ))
                return cur.lastrowid

    @staticmethod
    def update_sync(emp_id: int, sync_date: str):
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute(
                f"UPDATE {EmployeesRepo.TABLE} SET last_sync=?, updated_at=datetime('now') WHERE id=?",
                (sync_date, emp_id))

    @staticmethod
    def delete(emp_id: int):
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute(f"DELETE FROM {EmployeesRepo.TABLE} WHERE id = ?", (emp_id,))
            conn.execute(f"DELETE FROM employee_programs WHERE employee_id = ?", (emp_id,))

    @staticmethod
    def clear():
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute("DELETE FROM employee_programs")
            conn.execute(f"DELETE FROM {EmployeesRepo.TABLE}")

    @staticmethod
    def count() -> int:
        r = DatabaseManager.get_instance().fetchone(f"SELECT COUNT(DISTINCT snils_hash) as cnt FROM {EmployeesRepo.TABLE}")
        return r['cnt'] if r else 0

    @staticmethod
    def get_with_programs(emp_id: int) -> List[dict]:
        db = DatabaseManager.get_instance()
        return db.fetchall("""
            SELECT e.*, ep.program_id, ep.need_training, ep.exam_date,
                   ep.protocol as ep_protocol, ep.base_no, ep.result as ep_result,
                   ep.status as ep_status, ep.updated_at as ep_updated_at
            FROM employees e
            LEFT JOIN employee_programs ep ON e.id = ep.employee_id
            WHERE e.id = ?
            ORDER BY ep.program_id
        """, (emp_id,))

    @staticmethod
    def get_all_with_programs() -> dict:
        """PERFORMANCE: batch load ALL employees with their programs in ONE query.
        Returns dict mapping employee_id -> {emp_dict, programs: [...]}"""
        db = DatabaseManager.get_instance()
        rows = db.fetchall("""
            SELECT e.*, ep.program_id, ep.need_training, ep.exam_date,
                   ep.protocol as ep_protocol, ep.base_no, ep.result as ep_result,
                   ep.status as ep_status, ep.updated_at as ep_updated_at
            FROM employees e
            LEFT JOIN employee_programs ep ON e.id = ep.employee_id
            ORDER BY e.last_name_enc, e.first_name_enc, ep.program_id
        """)
        result = {}
        for r in rows:
            eid = r['id']
            if eid not in result:
                result[eid] = {'emp': _decrypt_emp(r), 'programs': []}
            if r['program_id'] is not None:
                result[eid]['programs'].append({
                    'program_id': r['program_id'],
                    'need_training': r['need_training'],
                    'exam_date': r['exam_date'],
                    'protocol': r['ep_protocol'],
                    'base_no': r['base_no'],
                    'result': r['ep_result'],
                    'status': r['ep_status'],
                    'updated_at': r['ep_updated_at'],
                })
        return result
