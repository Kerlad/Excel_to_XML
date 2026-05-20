import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

from .database import DatabaseManager
from utils.crypto import encrypt_value, decrypt_value, hash_for_search

logger = logging.getLogger(__name__)


@dataclass
class JournalRecord:
    uuid: str
    send_date: str
    set_id: str
    xml_file: str
    last_name: str
    first_name: str
    middle_name: str
    snils: str
    position: str
    program_id: str
    program_title: str
    exam_date: str
    protocol: str
    result: str
    base_no: str = ""
    status: str = "pending"


def _row_to_record(row) -> JournalRecord:
    return JournalRecord(
        uuid=row['uuid'], send_date=row['send_date'],
        set_id=row['set_id'], xml_file=row['xml_file'],
        last_name=decrypt_value(row.get('last_name_enc','')),
        first_name=decrypt_value(row.get('first_name_enc','')),
        middle_name=decrypt_value(row.get('middle_name_enc','')),
        snils=decrypt_value(row.get('snils_enc','')),
        position=row['position'], program_id=row['program_id'],
        program_title=row['program_title'], exam_date=row['exam_date'],
        protocol=row['protocol'], result=row['result'],
        base_no=row['base_no'], status=row['status'],
    )


class ExamJournalRepo:
    TABLE = "exam_journal"

    @staticmethod
    def get_all() -> List[JournalRecord]:
        db = DatabaseManager.get_instance()
        rows = db.fetchall(f"SELECT * FROM {ExamJournalRepo.TABLE} ORDER BY id")
        return [_row_to_record(r) for r in rows]

    @staticmethod
    def add_records(records: List[JournalRecord]):
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.executemany(f"""
                INSERT INTO {ExamJournalRepo.TABLE}
                (uuid, send_date, set_id, xml_file,
                 last_name_enc, first_name_enc, middle_name_enc, snils_enc, snils_hash,
                 position, program_id, program_title, exam_date, protocol, result, base_no, status)
                VALUES (?,?,?,?, ?,?,?,?,?, ?,?,?,?,?,?,?,?)
            """, [(
                r.uuid, r.send_date, r.set_id, r.xml_file,
                encrypt_value(r.last_name), encrypt_value(r.first_name),
                encrypt_value(r.middle_name), encrypt_value(r.snils),
                hash_for_search(r.snils),
                r.position, r.program_id, r.program_title,
                r.exam_date, r.protocol, r.result, r.base_no, r.status,
            ) for r in records])

    @staticmethod
    def update_base_no(set_id: str, base_no_map: Dict[str, str]) -> int:
        db = DatabaseManager.get_instance()
        updated = 0
        with db.transaction() as conn:
            rows = conn.execute(
                f"SELECT * FROM {ExamJournalRepo.TABLE} WHERE set_id = ? AND status = 'pending'",
                (set_id,)
            ).fetchall()
            for row in rows:
                snils_plain = decrypt_value(row['snils_enc'])
                snils_key = snils_plain.replace('-','').replace(' ','')
                if snils_key in base_no_map:
                    conn.execute(
                        f"UPDATE {ExamJournalRepo.TABLE} SET base_no=?, status='received' WHERE uuid=?",
                        (base_no_map[snils_key], row['uuid'])
                    )
                    updated += 1
        return updated

    @staticmethod
    def delete_by_uuid(uuids: List[str]) -> int:
        db = DatabaseManager.get_instance()
        placeholders = ','.join('?' for _ in uuids)
        with db.transaction() as conn:
            cur = conn.execute(f"DELETE FROM {ExamJournalRepo.TABLE} WHERE uuid IN ({placeholders})", uuids)
            return cur.rowcount

    @staticmethod
    def count() -> int:
        r = DatabaseManager.get_instance().fetchone(f"SELECT COUNT(*) as cnt FROM {ExamJournalRepo.TABLE}")
        return r['cnt'] if r else 0

    @staticmethod
    def search(query: str = "", set_id: str = "",
               status: str = "all", date_from: str = "", date_to: str = "") -> List[JournalRecord]:
        all_records = ExamJournalRepo.get_all()
        results = all_records
        if query.strip():
            q = query.strip().lower()
            results = [r for r in results if q in r.last_name.lower() or q in r.first_name.lower()
                       or q in r.middle_name.lower() or q in r.snils.replace('-','').replace(' ','')]
        if set_id.strip():
            results = [r for r in results if r.set_id == set_id.strip()]
        if status != "all":
            results = [r for r in results if r.status == status]
        if date_from:
            try:
                df = datetime.strptime(date_from, "%d.%m.%Y")
                results = [r for r in results
                           if r.exam_date and datetime.strptime(r.exam_date.split()[0], '%d.%m.%Y') >= df]
            except: pass
        if date_to:
            try:
                dt = datetime.strptime(date_to, "%d.%m.%Y")
                results = [r for r in results
                           if r.exam_date and datetime.strptime(r.exam_date.split()[0], '%d.%m.%Y') <= dt]
            except: pass
        return results

    @staticmethod
    def get_unique_set_ids() -> List[str]:
        rows = DatabaseManager.get_instance().fetchall(
            f"SELECT DISTINCT set_id FROM {ExamJournalRepo.TABLE} WHERE set_id != '' ORDER BY set_id")
        return [r['set_id'] for r in rows]

    @staticmethod
    def get_records_by_protocol(protocol_number: str) -> List[JournalRecord]:
        rows = DatabaseManager.get_instance().fetchall(
            f"SELECT * FROM {ExamJournalRepo.TABLE} WHERE protocol = ? ORDER BY id", (protocol_number,))
        return [_row_to_record(r) for r in rows]
