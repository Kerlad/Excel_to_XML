import logging
from datetime import datetime
from typing import List, Optional, Dict

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class EmployeesRepo:
    TABLE = "employees"

    @staticmethod
    def get_all() -> List[dict]:
        db = DatabaseManager.get_instance()
        return db.fetchall(f"SELECT * FROM {EmployeesRepo.TABLE} ORDER BY last_name, first_name")

    @staticmethod
    def get_by_id(emp_id: int) -> Optional[dict]:
        db = DatabaseManager.get_instance()
        return db.fetchone(f"SELECT * FROM {EmployeesRepo.TABLE} WHERE id = ?", (emp_id,))

    @staticmethod
    def get_by_snils(snils: str) -> Optional[dict]:
        db = DatabaseManager.get_instance()
        return db.fetchone(f"SELECT * FROM {EmployeesRepo.TABLE} WHERE snils = ?", (snils,))

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
                    SET last_name=?, first_name=?, middle_name=?, position=?,
                        required_programs=?, updated_at=?
                    WHERE snils=?
                """, (
                    employee.get('last_name', ''),
                    employee.get('first_name', ''),
                    employee.get('middle_name', ''),
                    employee.get('position', ''),
                    employee.get('required_programs', ''),
                    now,
                    snils,
                ))
                return existing['id']
            else:
                cur = conn.execute(f"""
                    INSERT INTO {EmployeesRepo.TABLE}
                    (snils, last_name, first_name, middle_name, position, required_programs,
                     last_sync, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snils,
                    employee.get('last_name', ''),
                    employee.get('first_name', ''),
                    employee.get('middle_name', ''),
                    employee.get('position', ''),
                    employee.get('required_programs', ''),
                    employee.get('last_sync'),
                    now,
                    now,
                ))
                return cur.lastrowid

    @staticmethod
    def upsert_many(employees: List[dict]) -> int:
        count = 0
        for emp in employees:
            EmployeesRepo.upsert(emp)
            count += 1
        return count

    @staticmethod
    def update_sync(emp_id: int, sync_date: str):
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute(
                f"UPDATE {EmployeesRepo.TABLE} SET last_sync = ?, updated_at = datetime('now') WHERE id = ?",
                (sync_date, emp_id)
            )

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
        db = DatabaseManager.get_instance()
        row = db.fetchone(f"SELECT COUNT(DISTINCT snils) as cnt FROM {EmployeesRepo.TABLE}")
        return row['cnt'] if row else 0

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
