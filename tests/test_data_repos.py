import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from db.database import DatabaseManager
from db.schema import create_schema
from db.employees_repo import EmployeesRepo
from db.employee_programs_repo import EmployeeProgramsRepo
from db.workers_data_repo import WorkersDataRepo
from db.exam_journal_repo import ExamJournalRepo, JournalRecord
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
    db_dir = os.path.dirname(db_path)
    backup_dir = os.path.join(db_dir, 'backups')
    if os.path.exists(backup_dir):
        import shutil
        shutil.rmtree(backup_dir, ignore_errors=True)


class TestEmployeesRepo:
    def test_upsert_new(self):
        emp_id = EmployeesRepo.upsert({
            'snils': '123-456-789 00', 'last_name': 'Иванов',
            'first_name': 'Иван', 'middle_name': 'Иванович',
            'position': 'Инженер', 'required_programs': '1,2,3'
        })
        assert emp_id is not None and emp_id > 0

    def test_upsert_update(self):
        emp_id = EmployeesRepo.upsert({
            'snils': '123-456-789 00', 'last_name': 'Иванов',
            'first_name': 'Иван', 'middle_name': 'Иванович',
            'position': 'Инженер', 'required_programs': '1'
        })
        updated_id = EmployeesRepo.upsert({
            'snils': '123-456-789 00', 'last_name': 'Петров',
            'first_name': 'Петр', 'middle_name': 'Петрович',
            'position': 'Старший инженер', 'required_programs': '1,2'
        })
        assert updated_id == emp_id
        emp = EmployeesRepo.get_by_id(emp_id)
        assert emp['last_name'] == 'Петров'
        assert emp['position'] == 'Старший инженер'

    def test_get_by_snils(self):
        EmployeesRepo.upsert({
            'snils': '111-222-333 44', 'last_name': 'Test', 'first_name': 'User',
            'middle_name': 'M', 'position': 'Pos', 'required_programs': '1'
        })
        emp = EmployeesRepo.get_by_snils('111-222-333 44')
        assert emp is not None
        assert emp['last_name'] == 'Test'
        emp2 = EmployeesRepo.get_by_snils('11122233344')
        assert emp2 is not None

    def test_get_by_snils_not_found(self):
        emp = EmployeesRepo.get_by_snils('000-000-000 00')
        assert emp is None

    def test_get_all(self):
        EmployeesRepo.upsert({'snils': '111-111-111 11', 'last_name': 'A', 'first_name': 'A', 'middle_name': 'A', 'position': 'P', 'required_programs': ''})
        EmployeesRepo.upsert({'snils': '222-222-222 22', 'last_name': 'B', 'first_name': 'B', 'middle_name': 'B', 'position': 'P', 'required_programs': ''})
        all_emp = EmployeesRepo.get_all()
        assert len(all_emp) == 2

    def test_count(self):
        assert EmployeesRepo.count() == 0
        EmployeesRepo.upsert({'snils': '333-333-333 33', 'last_name': 'C', 'first_name': 'C', 'middle_name': 'C', 'position': 'P', 'required_programs': ''})
        assert EmployeesRepo.count() == 1

    def test_delete(self):
        emp_id = EmployeesRepo.upsert({'snils': '444-444-444 44', 'last_name': 'D', 'first_name': 'D', 'middle_name': 'D', 'position': 'P', 'required_programs': ''})
        EmployeesRepo.delete(emp_id)
        assert EmployeesRepo.get_by_id(emp_id) is None

    def test_clear(self):
        EmployeesRepo.upsert({'snils': '555-555-555 55', 'last_name': 'E', 'first_name': 'E', 'middle_name': 'E', 'position': 'P', 'required_programs': ''})
        EmployeesRepo.clear()
        assert EmployeesRepo.count() == 0

    def test_update_sync(self):
        emp_id = EmployeesRepo.upsert({'snils': '666-666-666 66', 'last_name': 'F', 'first_name': 'F', 'middle_name': 'F', 'position': 'P', 'required_programs': ''})
        EmployeesRepo.update_sync(emp_id, '2025-09-25')
        emp = EmployeesRepo.get_by_id(emp_id)
        assert emp['last_sync'] == '2025-09-25'

    def test_get_all_with_programs(self):
        emp_id = EmployeesRepo.upsert({'snils': '777-777-777 77', 'last_name': 'G', 'first_name': 'G', 'middle_name': 'G', 'position': 'P', 'required_programs': '1,2'})
        result = EmployeesRepo.get_all_with_programs()
        assert emp_id in result
        assert result[emp_id]['emp']['last_name'] == 'G'


class TestEmployeeProgramsRepo:
    def test_upsert_program(self):
        emp_id = EmployeesRepo.upsert({'snils': '888-888-888 88', 'last_name': 'H', 'first_name': 'H', 'middle_name': 'H', 'position': 'P', 'required_programs': '1'})
        EmployeeProgramsRepo.upsert(emp_id, {'program_id': 1, 'need_training': 1})
        progs = EmployeeProgramsRepo.get_by_employee(emp_id)
        assert len(progs) == 1
        assert progs[0]['need_training'] == 1

    def test_get_status_counts(self):
        emp_id = EmployeesRepo.upsert({'snils': '999-999-999 99', 'last_name': 'I', 'first_name': 'I', 'middle_name': 'I', 'position': 'P', 'required_programs': '1'})
        EmployeeProgramsRepo.upsert(emp_id, {'program_id': 1, 'need_training': 1})
        counts = EmployeeProgramsRepo.get_status_counts()
        assert counts['not_trained'] > 0

    def test_update_need_training(self):
        emp_id = EmployeesRepo.upsert({'snils': 'aaa-bbb-ccc dd', 'last_name': 'J', 'first_name': 'J', 'middle_name': 'J', 'position': 'P', 'required_programs': '1'})
        EmployeeProgramsRepo.update_need_training(emp_id, 1, 1)
        prog = EmployeeProgramsRepo.get(emp_id, 1)
        assert prog is not None
        assert prog['need_training'] == 1

    def test_update_from_api(self):
        emp_id = EmployeesRepo.upsert({'snils': 'bbb-ccc-ddd ee', 'last_name': 'K', 'first_name': 'K', 'middle_name': 'K', 'position': 'P', 'required_programs': '1'})
        EmployeeProgramsRepo.update_from_api(emp_id, 1, '01.01.2025', 'П-001', 'BN-001', 1)
        prog = EmployeeProgramsRepo.get(emp_id, 1)
        assert prog is not None
        assert prog['exam_date'] == '01.01.2025'

    def test_delete_by_employee(self):
        emp_id = EmployeesRepo.upsert({'snils': 'ccc-ddd-eee ff', 'last_name': 'L', 'first_name': 'L', 'middle_name': 'L', 'position': 'P', 'required_programs': '1'})
        EmployeeProgramsRepo.upsert(emp_id, {'program_id': 1, 'need_training': 1})
        EmployeeProgramsRepo.delete_by_employee(emp_id)
        assert len(EmployeeProgramsRepo.get_by_employee(emp_id)) == 0

    def test_calc_status_not_trained(self):
        status = EmployeeProgramsRepo._calc_status(None, None)
        assert status == 'not_trained'

    def test_calc_status_not_trained_zero_result(self):
        status = EmployeeProgramsRepo._calc_status('01.01.2025', 0)
        assert status == 'not_trained'


class TestWorkersDataRepo:
    def test_add_record(self):
        rid = WorkersDataRepo.add({
            'last_name': 'Test', 'first_name': 'User', 'middle_name': 'M',
            'snils': '123-456-789 00', 'position': 'Engineer',
            'employer_inn': '7701', 'employer_title': 'LLC',
            'tc_inn': '7702', 'tc_title': 'TC',
            'result': 'Удовлетворительно', 'program': 1, 'date': '01.01.2025', 'protocol': 'P-001'
        })
        assert rid > 0

    def test_get_by_id(self):
        rid = WorkersDataRepo.add({
            'last_name': 'Get', 'first_name': 'By', 'middle_name': 'Id',
            'snils': '111-222-333 44', 'position': 'P',
            'employer_inn': '1', 'employer_title': 'T',
            'tc_inn': '2', 'tc_title': 'U',
            'result': 'Удовлетворительно', 'program': 1, 'date': '01.01.2025', 'protocol': 'P'
        })
        rec = WorkersDataRepo.get_by_id(rid)
        assert rec is not None
        assert rec['last_name'] == 'Get'

    def test_get_all(self):
        WorkersDataRepo.add({
            'last_name': 'A1', 'first_name': 'B1', 'middle_name': 'C1',
            'snils': '111-111-111 11', 'position': 'P',
            'employer_inn': '1', 'employer_title': 'T',
            'tc_inn': '2', 'tc_title': 'U',
            'result': 'Удовлетворительно', 'program': 1, 'date': '01.01.2025', 'protocol': 'P'
        })
        all_recs = WorkersDataRepo.get_all()
        assert len(all_recs) >= 1

    def test_add_many(self):
        records = [
            {'last_name': f'L{i}', 'first_name': 'F', 'middle_name': 'M',
             'snils': f'0000000000{i}', 'position': 'P',
             'employer_inn': '1', 'employer_title': 'T',
             'tc_inn': '2', 'tc_title': 'U',
             'result': 'Удовлетворительно', 'program': 1, 'date': '01.01.2025', 'protocol': 'P'}
            for i in range(3)
        ]
        count = WorkersDataRepo.add_many(records)
        assert count == 3

    def test_update(self):
        rid = WorkersDataRepo.add({
            'last_name': 'Old', 'first_name': 'Name', 'middle_name': 'M',
            'snils': '999-999-999 99', 'position': 'OldPos',
            'employer_inn': '1', 'employer_title': 'T',
            'tc_inn': '2', 'tc_title': 'U',
            'result': 'Удовлетворительно', 'program': 1, 'date': '01.01.2025', 'protocol': 'P'
        })
        WorkersDataRepo.update(rid, {'last_name': 'New', 'position': 'NewPos'})
        rec = WorkersDataRepo.get_by_id(rid)
        assert rec['last_name'] == 'New'

    def test_delete(self):
        rid = WorkersDataRepo.add({
            'last_name': 'Del', 'first_name': 'Ete', 'middle_name': 'M',
            'snils': '888-888-888 88', 'position': 'P',
            'employer_inn': '1', 'employer_title': 'T',
            'tc_inn': '2', 'tc_title': 'U',
            'result': 'Удовлетворительно', 'program': 1, 'date': '01.01.2025', 'protocol': 'P'
        })
        WorkersDataRepo.delete(rid)
        assert WorkersDataRepo.get_by_id(rid) is None

    def test_clear(self):
        WorkersDataRepo.add({
            'last_name': 'Clr', 'first_name': 'Ear', 'middle_name': 'M',
            'snils': '777-777-777 77', 'position': 'P',
            'employer_inn': '1', 'employer_title': 'T',
            'tc_inn': '2', 'tc_title': 'U',
            'result': 'Удовлетворительно', 'program': 1, 'date': '01.01.2025', 'protocol': 'P'
        })
        WorkersDataRepo.clear()
        assert WorkersDataRepo.count() == 0

    def test_get_existing_keys(self):
        WorkersDataRepo.add({
            'last_name': 'Key', 'first_name': 'Test', 'middle_name': 'M',
            'snils': '666-666-666 66', 'position': 'P',
            'employer_inn': '1', 'employer_title': 'T',
            'tc_inn': '2', 'tc_title': 'U',
            'result': 'Удовлетворительно', 'program': 1, 'date': '01.01.2025', 'protocol': 'P'
        })
        keys = WorkersDataRepo.get_existing_keys()
        assert len(keys) >= 1


class TestExamJournalRepo:
    def test_add_and_get_records(self):
        records = [
            JournalRecord(
                uuid='test-uuid-1', send_date='01.01.2025', set_id='SET-001',
                xml_file='test.xml', last_name='Иван', first_name='Иван',
                middle_name='Иван', snils='123-456-789 00', position='Инж',
                program_id='1', program_title='Первая помощь',
                exam_date='01.01.2025', protocol='П-001', result='Удовлетворительно',
                base_no='', status='pending'
            )
        ]
        ExamJournalRepo.add_records(records)
        all_recs = ExamJournalRepo.get_all()
        assert len(all_recs) == 1
        assert all_recs[0].last_name == 'Иван'

    def test_search_by_setid(self):
        records = [
            JournalRecord(
                uuid=f'uuid-{i}', send_date='01.01.2025', set_id='SET-SEARCH',
                xml_file='t.xml', last_name=f'Last{i}', first_name='First',
                middle_name='Mid', snils=f'000-000-000 0{i}', position='P',
                program_id='1', program_title='Prog',
                exam_date='01.01.2025', protocol='P-001', result='Удовлетворительно',
                base_no='', status='pending'
            ) for i in range(3)
        ]
        ExamJournalRepo.add_records(records)
        results = ExamJournalRepo.search(set_id='SET-SEARCH')
        assert len(results) == 3

    def test_search_by_status(self):
        records = [
            JournalRecord(
                uuid=f'uuid-status-{i}', send_date='01.01.2025', set_id='SET-S',
                xml_file='t.xml', last_name='N', first_name='F',
                middle_name='M', snils=f'111-111-111 1{i}', position='P',
                program_id='1', program_title='Prog',
                exam_date='01.01.2025', protocol='P', result='Удовлетворительно',
                base_no='', status='received' if i == 0 else 'pending'
            ) for i in range(2)
        ]
        ExamJournalRepo.add_records(records)
        received = ExamJournalRepo.search(status='received')
        assert len(received) == 1
        pending = ExamJournalRepo.search(status='pending')
        assert len(pending) == 1

    def test_delete_by_uuid(self):
        ExamJournalRepo.add_records([
            JournalRecord(
                uuid='delete-me', send_date='', set_id='', xml_file='',
                last_name='D', first_name='E', middle_name='L',
                snils='000-000-000 00', position='P',
                program_id='1', program_title='', exam_date='', protocol='',
                result='', base_no='', status='pending'
            )
        ])
        deleted = ExamJournalRepo.delete_by_uuid(['delete-me'])
        assert deleted == 1

    def test_update_base_no(self):
        ExamJournalRepo.add_records([
            JournalRecord(
                uuid='update-base', send_date='', set_id='SET-BASE', xml_file='',
                last_name='U', first_name='P', middle_name='D',
                snils='123-456-789 00', position='P',
                program_id='1', program_title='', exam_date='', protocol='',
                result='', base_no='', status='pending'
            )
        ])
        updated = ExamJournalRepo.update_base_no('SET-BASE', {'12345678900': 'BN-001'})
        assert updated == 1

    def test_get_unique_set_ids(self):
        ExamJournalRepo.add_records([
            JournalRecord(
                uuid=f'set-uuid-{i}', send_date='', set_id=f'SET-{i}', xml_file='',
                last_name='N', first_name='F', middle_name='M',
                snils=f'000-000-000 0{i}', position='P',
                program_id='1', program_title='', exam_date='', protocol='',
                result='', base_no='', status='pending'
            ) for i in range(2)
        ])
        ids = ExamJournalRepo.get_unique_set_ids()
        assert 'SET-0' in ids
        assert 'SET-1' in ids

    def test_get_records_by_protocol(self):
        ExamJournalRepo.add_records([
            JournalRecord(
                uuid='proto-rec', send_date='', set_id='', xml_file='',
                last_name='P', first_name='R', middle_name='O',
                snils='000-000-000 00', position='Pos',
                program_id='1', program_title='Prog',
                exam_date='', protocol='PR-001', result='Удовлетворительно',
                base_no='', status='pending'
            )
        ])
        recs = ExamJournalRepo.get_records_by_protocol('PR-001')
        assert len(recs) == 1

    def test_count(self):
        assert ExamJournalRepo.count() == 0
        ExamJournalRepo.add_records([
            JournalRecord(
                uuid='count-test', send_date='', set_id='', xml_file='',
                last_name='C', first_name='N', middle_name='T',
                snils='000-000-000 00', position='P',
                program_id='1', program_title='', exam_date='', protocol='',
                result='', base_no='', status='pending'
            )
        ])
        assert ExamJournalRepo.count() == 1
