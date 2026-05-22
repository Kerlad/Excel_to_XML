import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from protocol.commission_manager import CommissionManager
from protocol.programs_manager import ProgramsManager, BASE_PROGRAMS
from utils.crypto import clear_caches


@pytest.fixture(autouse=True)
def reset_crypto():
    clear_caches()
    yield


class TestCommissionManager:
    def test_default_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CommissionManager(tmpdir)
            data = cm.get_data()
            assert data['org_name'] == ''
            assert data['chairman_fio'] == ''

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CommissionManager(tmpdir)
            test_data = {
                'org_name': 'ООО Тест', 'order_number': '123',
                'order_date': '01.01.2025', 'exam_date': '15.01.2025',
                'chairman_fio': 'Иванов Иван Иванович',
                'chairman_position': 'Директор',
                'member1_fio': 'Петров Петр', 'member1_position': 'Зам',
                'member2_fio': 'Сидоров Сидор', 'member2_position': 'Нач',
                'member3_fio': '', 'member3_position': '',
                'union_fio': '', 'union_position': ''
            }
            ok, msg = cm.save(test_data)
            assert ok

            cm2 = CommissionManager(tmpdir)
            loaded = cm2.load()
            assert loaded['org_name'] == 'ООО Тест'
            assert loaded['chairman_fio'] == 'Иванов Иван Иванович'

    def test_is_complete_ok(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CommissionManager(tmpdir)
            cm.save({
                'org_name': 'Test', 'order_number': '1',
                'order_date': '', 'exam_date': '',
                'chairman_fio': 'Chair', 'chairman_position': '',
                'member1_fio': '', 'member1_position': '',
                'member2_fio': '', 'member2_position': '',
                'member3_fio': '', 'member3_position': '',
                'union_fio': '', 'union_position': ''
            })
            ok, msg = cm.is_complete()
            assert ok

    def test_is_complete_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CommissionManager(tmpdir)
            ok, msg = cm.is_complete()
            assert not ok
            assert 'Не заполнены' in msg

    def test_encrypted_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CommissionManager(tmpdir)
            cm.save({'org_name': 'Secret Org', 'order_number': '1', 'chairman_fio': 'Ivanov'})
            file_path = os.path.join(tmpdir, 'commission_data.json')
            with open(file_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            assert 'data' in raw
            assert raw['data'] != ''


class TestProgramsManager:
    def test_base_programs_loaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = ProgramsManager(tmpdir)
            all_progs = pm.get_all_programs()
            assert len(all_progs) == 28
            assert '1' in all_progs
            assert all_progs['1']['name'] == 'Оказание первой помощи пострадавшим'

    def test_get_program(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = ProgramsManager(tmpdir)
            prog = pm.get_program('1')
            assert prog['name'] == 'Оказание первой помощи пострадавшим'
            prog = pm.get_program('999')
            assert prog == {"name": "", "doc": "", "hours": ""}

    def test_update_program(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = ProgramsManager(tmpdir)
            pm.update_program('1', doc='НД-001', hours='16')
            prog = pm.get_program('1')
            assert prog['doc'] == 'НД-001'
            assert prog['hours'] == '16'

    def test_update_program_invalid_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = ProgramsManager(tmpdir)
            pm.update_program('999', doc='test')
            assert '999' not in pm.get_all_programs()

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = ProgramsManager(tmpdir)
            pm.update_program('2', doc='Док-002', hours='8')
            pm2 = ProgramsManager(tmpdir)
            prog = pm2.get_program('2')
            assert prog['doc'] == 'Док-002'
            assert prog['hours'] == '8'

    def test_save_returns_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = ProgramsManager(tmpdir)
            ok, msg = pm.save()
            assert ok

    def test_base_programs_have_all_fields(self):
        for pid, prog in BASE_PROGRAMS.items():
            assert 'name' in prog
            assert 'doc' in prog
            assert 'hours' in prog
