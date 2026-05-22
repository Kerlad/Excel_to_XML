import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from db.database import DatabaseManager
from db.schema import create_schema
from db.exam_journal_repo import JournalRecord
from journal.journal_manager import JournalManager
from utils.crypto import clear_caches


@pytest.fixture(autouse=True)
def setup_db():
    clear_caches()
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    db = DatabaseManager.get_instance(db_path)
    db.initialize()
    create_schema()
    yield db
    db.close_all()
    if os.path.exists(db_path):
        os.remove(db_path)


class TestJournalManager:
    def test_add_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            jm = JournalManager(tmpdir)
            records_data = [
                {'last_name': 'Иванов', 'first_name': 'Иван', 'middle_name': 'Иванович',
                 'snils': '123-456-789 00', 'position': 'Инженер',
                 'program': '1', 'date': '01.01.2025', 'protocol': 'П-001', 'result': 'Удовлетворительно'}
            ]
            count = jm.add_records(records_data, 'SET-001', 'test.xml')
            assert count == 1
            all_recs = jm.get_all_records()
            assert len(all_recs) == 1
            assert all_recs[0].last_name == 'Иванов'
            assert all_recs[0].set_id == 'SET-001'

    def test_add_records_multiple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            jm = JournalManager(tmpdir)
            records_data = [
                {'last_name': f'User{i}', 'first_name': 'F', 'middle_name': 'M',
                 'snils': f'000-000-000 0{i}', 'position': 'P',
                 'program': str(i), 'date': '01.01.2025', 'protocol': 'P', 'result': 'Удовлетворительно'}
                for i in range(5)
            ]
            count = jm.add_records(records_data, 'SET-MULTI', 't.xml')
            assert count == 5

    def test_get_unique_set_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            jm = JournalManager(tmpdir)
            jm.add_records([{'last_name': 'A', 'first_name': 'B', 'middle_name': 'C',
                             'snils': '11111111111', 'position': 'P',
                             'program': '1', 'date': '', 'protocol': '', 'result': ''}],
                           'SET-A', 'a.xml')
            ids = jm.get_unique_set_ids()
            assert 'SET-A' in ids

    def test_delete_by_uuid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            jm = JournalManager(tmpdir)
            jm.add_records([{'last_name': 'Del', 'first_name': 'Ete', 'middle_name': 'M',
                             'snils': '22222222222', 'position': 'P',
                             'program': '1', 'date': '', 'protocol': '', 'result': ''}],
                           'SET-DEL', 'd.xml')
            recs = jm.get_all_records()
            uuid_to_del = [recs[0].uuid]
            deleted = jm.delete_by_uuid(uuid_to_del)
            assert deleted == 1
            assert jm.get_record_count() == 0

    def test_get_records_by_protocol(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            jm = JournalManager(tmpdir)
            jm.add_records([{'last_name': 'Proto', 'first_name': 'Col', 'middle_name': 'M',
                             'snils': '33333333333', 'position': 'P',
                             'program': '1', 'date': '01.01.2025', 'protocol': 'PR-001',
                             'result': 'Удовлетворительно'}],
                           'SET-P', 'p.xml')
            recs = jm.get_records_by_protocol('PR-001')
            assert len(recs) == 1

    def test_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            jm = JournalManager(tmpdir)
            jm.add_records([{'last_name': 'SearchMe', 'first_name': 'F', 'middle_name': 'M',
                             'snils': '44444444444', 'position': 'P',
                             'program': '1', 'date': '', 'protocol': '', 'result': ''}],
                           'SET-S', 's.xml')
            results = jm.search(query='SearchMe')
            assert len(results) >= 1
            results = jm.search(query='Nonexistent')
            assert len(results) == 0

    def test_get_record_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            jm = JournalManager(tmpdir)
            assert jm.get_record_count() == 0
            jm.add_records([{'last_name': 'C', 'first_name': 'N', 'middle_name': 'T',
                             'snils': '55555555555', 'position': 'P',
                             'program': '1', 'date': '', 'protocol': '', 'result': ''}],
                           'SET-C', 'c.xml')
            assert jm.get_record_count() == 1

    def test_get_program_title(self):
        assert JournalManager._get_program_title('1') == 'Оказание первой помощи пострадавшим'
        assert JournalManager._get_program_title('18') == 'Безопасные методы и приемы выполнения работ в электроустановках'
        assert JournalManager._get_program_title('999') == ''
