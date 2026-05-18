import logging
from datetime import datetime
from typing import List, Optional

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class EmployeeProgramsRepo:
    TABLE = "employee_programs"

    @staticmethod
    def get_by_employee(employee_id: int) -> List[dict]:
        db = DatabaseManager.get_instance()
        return db.fetchall(
            f"SELECT * FROM {EmployeeProgramsRepo.TABLE} WHERE employee_id = ? ORDER BY program_id",
            (employee_id,)
        )

    @staticmethod
    def get(employee_id: int, program_id: int) -> Optional[dict]:
        db = DatabaseManager.get_instance()
        return db.fetchone(
            f"SELECT * FROM {EmployeeProgramsRepo.TABLE} WHERE employee_id = ? AND program_id = ?",
            (employee_id, program_id)
        )

    @staticmethod
    def upsert(employee_id: int, program_data: dict):
        db = DatabaseManager.get_instance()
        program_id = program_data.get('program_id', 0)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if 'status' not in program_data or program_data.get('status') is None:
            program_data['status'] = EmployeeProgramsRepo._calc_status(
                program_data.get('exam_date'),
                program_data.get('result')
            )

        existing = EmployeeProgramsRepo.get(employee_id, program_id)
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
                    program_data.get('status', existing.get('status')),
                    now,
                    employee_id, program_id,
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
                    program_data.get('exam_date'),
                    program_data.get('protocol'),
                    program_data.get('base_no'),
                    program_data.get('result'),
                    program_data.get('status'),
                    now,
                ))

    @staticmethod
    def update_need_training(employee_id: int, program_id: int, value: int):
        db = DatabaseManager.get_instance()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        existing = EmployeeProgramsRepo.get(employee_id, program_id)
        with db.transaction() as conn:
            if existing:
                conn.execute(f"""
                    UPDATE {EmployeeProgramsRepo.TABLE}
                    SET need_training=?, updated_at=?
                    WHERE employee_id=? AND program_id=?
                """, (value, now, employee_id, program_id))
            else:
                status = 'not_trained' if value == 1 else None
                conn.execute(f"""
                    INSERT INTO {EmployeeProgramsRepo.TABLE}
                    (employee_id, program_id, need_training, status, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (employee_id, program_id, value, status, now))

    @staticmethod
    def update_from_api(employee_id: int, program_id: int,
                        exam_date: str, protocol: str, base_no: str, result: int):
        db = DatabaseManager.get_instance()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        existing = EmployeeProgramsRepo.get(employee_id, program_id)

        status = EmployeeProgramsRepo._calc_status(exam_date, result)
        with db.transaction() as conn:
            if existing:
                conn.execute(f"""
                    UPDATE {EmployeeProgramsRepo.TABLE}
                    SET exam_date=?, protocol=?, base_no=?, result=?,
                        status=?, updated_at=?
                    WHERE employee_id=? AND program_id=?
                """, (exam_date, protocol, base_no, result, status, now, employee_id, program_id))
            else:
                conn.execute(f"""
                    INSERT INTO {EmployeeProgramsRepo.TABLE}
                    (employee_id, program_id, need_training, exam_date, protocol,
                     base_no, result, status, updated_at)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
                """, (employee_id, program_id, exam_date, protocol, base_no, result, status, now))

    @staticmethod
    def delete_by_employee(employee_id: int):
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute(
                f"DELETE FROM {EmployeeProgramsRepo.TABLE} WHERE employee_id = ?",
                (employee_id,)
            )

    @staticmethod
    def get_status_counts() -> dict:
        db = DatabaseManager.get_instance()
        rows = db.fetchall(f"""
            SELECT status, COUNT(*) as cnt
            FROM {EmployeeProgramsRepo.TABLE}
            WHERE need_training = 1
            GROUP BY status
        """)
        counts = {'trained': 0, 'not_trained': 0, 'expired': 0, 'unknown': 0}
        for r in rows:
            s = r['status'] or 'unknown'
            if s in counts:
                counts[s] = r['cnt']
            else:
                counts['unknown'] += r['cnt']
        return counts

    @staticmethod
    def _calc_status(exam_date: Optional[str], result: Optional[int]) -> str:
        if not exam_date or result == 0:
            return 'not_trained'
        try:
            from datetime import datetime
            from dateutil.relativedelta import relativedelta
            dt = datetime.strptime(exam_date.split()[0], '%d.%m.%Y')
            if dt + relativedelta(years=3) < datetime.now():
                return 'expired'
            return 'trained'
        except (ValueError, IndexError):
            return 'unknown'
