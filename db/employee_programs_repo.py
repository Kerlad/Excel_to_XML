import logging
from datetime import datetime
from typing import List, Optional
from dateutil.relativedelta import relativedelta

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class EmployeeProgramsRepo:
    TABLE = "employee_programs"

    @staticmethod
    def get_by_employee(employee_id: int) -> List[dict]:
        db = DatabaseManager.get_instance()
        return db.fetchall(
            f"SELECT * FROM {EmployeeProgramsRepo.TABLE} WHERE employee_id = ? ORDER BY program_id",
            (employee_id,))

    @staticmethod
    def get_by_employee_ids(employee_ids: List[int]) -> dict:
        """PERFORMANCE: batch load programs for multiple employees in ONE query.
        Returns a dict mapping employee_id -> list of program dicts."""
        if not employee_ids:
            return {}
        db = DatabaseManager.get_instance()
        placeholders = ','.join('?' for _ in employee_ids)
        rows = db.fetchall(
            f"SELECT * FROM {EmployeeProgramsRepo.TABLE} "
            f"WHERE employee_id IN ({placeholders}) ORDER BY employee_id, program_id",
            tuple(employee_ids))
        result: dict = {}
        for r in rows:
            eid = r['employee_id']
            if eid not in result:
                result[eid] = []
            result[eid].append(r)
        return result

    @staticmethod
    def get(employee_id: int, program_id: int) -> Optional[dict]:
        db = DatabaseManager.get_instance()
        return db.fetchone(
            f"SELECT * FROM {EmployeeProgramsRepo.TABLE} WHERE employee_id = ? AND program_id = ?",
            (employee_id, program_id))

    @staticmethod
    def upsert(employee_id: int, program_data: dict):
        db = DatabaseManager.get_instance()
        program_id = program_data.get('program_id', 0)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        existing = EmployeeProgramsRepo.get(employee_id, program_id)
        status = program_data.get('status')
        if not status:
            status = EmployeeProgramsRepo._calc_status(
                program_data.get('exam_date'), program_data.get('result'))
        with db.transaction() as conn:
            if existing:
                conn.execute(f"""
                    UPDATE {EmployeeProgramsRepo.TABLE}
                    SET need_training=?, exam_date=?, protocol=?, base_no=?,
                        result=?, status=?, updated_at=?
                    WHERE employee_id=? AND program_id=?
                """, (
                    program_data.get('need_training', existing['need_training']),
                    program_data.get('exam_date', existing['exam_date']),
                    program_data.get('protocol', existing['protocol']),
                    program_data.get('base_no', existing['base_no']),
                    program_data.get('result', existing['result']),
                    status, now, employee_id, program_id,
                ))
            else:
                conn.execute(f"""
                    INSERT INTO {EmployeeProgramsRepo.TABLE}
                    (employee_id, program_id, need_training, exam_date, protocol,
                     base_no, result, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    employee_id, program_id,
                    program_data.get('need_training', 0),
                    program_data.get('exam_date'), program_data.get('protocol'),
                    program_data.get('base_no'), program_data.get('result'),
                    status, now,
                ))

    @staticmethod
    def update_need_training(employee_id: int, program_id: int, value: int):
        db = DatabaseManager.get_instance()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        existing = EmployeeProgramsRepo.get(employee_id, program_id)
        with db.transaction() as conn:
            if existing:
                conn.execute(f"""
                    UPDATE {EmployeeProgramsRepo.TABLE}
                    SET need_training=?, updated_at=?
                    WHERE employee_id=? AND program_id=?
                """, (value, now_str, employee_id, program_id))
            else:
                conn.execute(f"""
                    INSERT INTO {EmployeeProgramsRepo.TABLE}
                    (employee_id, program_id, need_training, status, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (employee_id, program_id, value,
                      'not_trained' if value == 1 else None, now_str))

    @staticmethod
    def update_from_api(employee_id: int, program_id: int,
                        exam_date: str, protocol: str, base_no: str, result: int):
        db = DatabaseManager.get_instance()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        existing = EmployeeProgramsRepo.get(employee_id, program_id)
        status = EmployeeProgramsRepo._calc_status(exam_date, result, program_id)
        with db.transaction() as conn:
            if existing:
                conn.execute(f"""
                    UPDATE {EmployeeProgramsRepo.TABLE}
                    SET exam_date=?, protocol=?, base_no=?, result=?, status=?, updated_at=?
                    WHERE employee_id=? AND program_id=?
                """, (exam_date, protocol, base_no, result, status, now_str, employee_id, program_id))
            else:
                conn.execute(f"""
                    INSERT INTO {EmployeeProgramsRepo.TABLE}
                    (employee_id, program_id, need_training, exam_date, protocol,
                     base_no, result, status, updated_at)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
                """, (employee_id, program_id, exam_date, protocol, base_no, result, status, now_str))

    @staticmethod
    def delete_by_employee(employee_id: int):
        DatabaseManager.get_instance().execute(
            f"DELETE FROM {EmployeeProgramsRepo.TABLE} WHERE employee_id = ?", (employee_id,))

    @staticmethod
    def get_status_counts() -> dict:
        rows = DatabaseManager.get_instance().fetchall(f"""
            SELECT status, COUNT(*) as cnt
            FROM {EmployeeProgramsRepo.TABLE}
            WHERE need_training = 1
            GROUP BY status
        """)
        counts = {'trained': 0, 'not_trained': 0, 'expired': 0}
        for r in rows:
            s = r['status'] or 'not_trained'
            if s in counts:
                counts[s] += r['cnt']
            else:
                counts['not_trained'] += r['cnt']
        return counts

    @staticmethod
    def _calc_status(exam_date: Optional[str], result: Optional[int], program_id: int = 0) -> str:
        if not exam_date or result == 0:
            return 'not_trained'
        try:
            from utils.training_rules import get_training_period_years
            dt = datetime.strptime(exam_date.split()[0], '%d.%m.%Y')
            years = get_training_period_years(program_id, True)
            if dt + relativedelta(years=years) < datetime.now():
                return 'expired'
            return 'trained'
        except (ValueError, IndexError):
            return 'unknown'
