import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from PySide6.QtCore import Qt, QSortFilterProxyModel, QRegularExpression
from utils.table_models import (
    DataViewTableModel, ExamJournalTableModel, EmployeeSummaryTableModel,
    MultiColumnFilterProxyModel, FIELD_KEYS, COLUMN_LABELS
)
from db.exam_journal_repo import JournalRecord


class TestDataViewTableModel:
    def test_load_records(self):
        model = DataViewTableModel()
        records = [
            {'last_name': 'Иванов', 'first_name': 'Иван', 'middle_name': 'Иванович',
             'snils': '123-456-789 00', 'position': 'Инж',
             'employer_inn': '7701', 'employer_title': 'ООО',
             'tc_inn': '7702', 'tc_title': 'УЦ',
             'result': 'Удовлетворительно', 'program': '1',
             'date': '01.01.2025', 'protocol': 'П-001'}
        ]
        model.load_records(records)
        assert model.rowCount() == 1
        assert model.columnCount() == len(COLUMN_LABELS)

        idx = model.index(0, 0)
        assert model.data(idx) == 'Иванов'

    def test_empty_model(self):
        model = DataViewTableModel()
        assert model.rowCount() == 0

    def test_header_data(self):
        model = DataViewTableModel()
        assert model.headerData(0, Qt.Orientation.Horizontal) == COLUMN_LABELS[0]

    def test_get_record_at(self):
        model = DataViewTableModel()
        records = [{'last_name': 'Test', 'id': 1}]
        model.load_records(records)
        rec = model.get_record_at(0)
        assert rec['id'] == 1
        assert model.get_record_at(999) is None

    def test_set_cell_value(self):
        model = DataViewTableModel()
        model.load_records([{'last_name': 'Old', 'id': 1}])
        model.set_cell_value(0, 0, 'New')
        assert model.data(model.index(0, 0)) == 'New'

    def test_set_highlight_column(self):
        model = DataViewTableModel()
        model.set_highlight_column(0)

    def test_record_id(self):
        model = DataViewTableModel()
        model.load_records([{'id': 42}])
        assert model.get_record_id(0) == 42
        assert model.get_record_id(999) is None

    def test_get_row_data(self):
        model = DataViewTableModel()
        records = [{'last_name': 'Test', 'first_name': 'User', 'id': 1}]
        model.load_records(records)
        row_data = model.get_row_data(0)
        assert row_data['last_name'] == 'Test'

    def test_get_all_raw_records(self):
        model = DataViewTableModel()
        records = [{'id': 1}, {'id': 2}]
        model.load_records(records)
        assert len(model.get_all_raw_records()) == 2


class TestExamJournalTableModel:
    def test_load_records(self):
        model = ExamJournalTableModel()
        records = [
            JournalRecord(
                uuid='u1', send_date='01.01.2025', set_id='SET-1',
                xml_file='f.xml', last_name='Иван', first_name='Иван',
                middle_name='Иван', snils='123-456-789 00', position='Инж',
                program_id='1', program_title='Первая помощь',
                exam_date='01.01.2025', protocol='П-001',
                result='Удовлетворительно', base_no='BN-001', status='received'
            )
        ]
        model.load_records(records)
        assert model.rowCount() == 1
        assert model.columnCount() == 14

    def test_empty_model(self):
        model = ExamJournalTableModel()
        assert model.rowCount() == 0

    def test_get_record(self):
        model = ExamJournalTableModel()
        rec = JournalRecord(
            uuid='u2', send_date='', set_id='', xml_file='',
            last_name='Test', first_name='U', middle_name='M',
            snils='000-000-000 00', position='P',
            program_id='1', program_title='T', exam_date='', protocol='',
            result='', base_no='', status='pending'
        )
        model.load_records([rec])
        assert model.get_record(0) is rec
        assert model.get_record(999) is None

    def test_status_display(self):
        model = ExamJournalTableModel()
        rec = JournalRecord(
            uuid='u3', send_date='01.01.2025', set_id='S-1',
            xml_file='f.xml', last_name='N', first_name='F',
            middle_name='M', snils='000-000-000 00', position='P',
            program_id='1', program_title='T',
            exam_date='01.01.2025', protocol='P-001',
            result='Удовлетворительно', base_no='BN-001', status='received'
        )
        model.load_records([rec])
        status_idx = model.index(0, 13)
        assert 'получен' in model.data(status_idx).lower()

    def test_user_role_returns_uuid(self):
        model = ExamJournalTableModel()
        rec = JournalRecord(
            uuid='uuid-return', send_date='', set_id='', xml_file='',
            last_name='N', first_name='F', middle_name='M',
            snils='000-000-000 00', position='P',
            program_id='1', program_title='', exam_date='', protocol='',
            result='', base_no='', status='pending'
        )
        model.load_records([rec])
        assert model.data(model.index(0, 0), Qt.ItemDataRole.UserRole) == 'uuid-return'

    def test_get_records(self):
        model = ExamJournalTableModel()
        model.load_records([1, 2, 3])
        assert model.get_records() == [1, 2, 3]


class TestEmployeeSummaryTableModel:
    def test_load_data(self):
        model = EmployeeSummaryTableModel()
        model.set_headers(['ФИО', 'Статус', 'СНИЛС'])
        model.load_data([
            ['Иванов Иван', 'Обучен', '123-456-789 00'],
            ['Петров Петр', 'Не обучен', '111-222-333 44']
        ], [1, 2])
        assert model.rowCount() == 2
        assert model.columnCount() == 3
        assert model.data(model.index(0, 0)) == 'Иванов Иван'

    def test_empty_model(self):
        model = EmployeeSummaryTableModel()
        assert model.rowCount() == 0

    def test_user_role(self):
        model = EmployeeSummaryTableModel()
        model.set_headers(['Name'])
        model.load_data([['Test']], [42])
        assert model.data(model.index(0, 0), Qt.ItemDataRole.UserRole) == 42

    def test_sort(self):
        model = EmployeeSummaryTableModel()
        model.set_headers(['Name', 'Status'])
        model.load_data([
            ['B', 'X'],
            ['A', 'Y'],
        ], [1, 2])
        model.sort(0, Qt.SortOrder.AscendingOrder)
        assert model.data(model.index(0, 0)) == 'A'
        assert model.data(model.index(1, 0)) == 'B'

    def test_sort_descending(self):
        model = EmployeeSummaryTableModel()
        model.set_headers(['Name'])
        model.load_data([['A'], ['B']], [1, 2])
        model.sort(0, Qt.SortOrder.DescendingOrder)
        assert model.data(model.index(0, 0)) == 'B'
        assert model.data(model.index(1, 0)) == 'A'


class TestMultiColumnFilterProxyModel:
    def test_filter_by_text(self):
        source = DataViewTableModel()
        source.load_records([{'last_name': 'Иванов', 'first_name': 'Иван'}])
        proxy = MultiColumnFilterProxyModel()
        proxy.setSourceModel(source)
        proxy.setFilterRegularExpression(QRegularExpression("Иван"))
        assert proxy.rowCount() >= 1
        proxy.setFilterRegularExpression(QRegularExpression("НетТакогоИмени"))
        assert proxy.rowCount() == 0

    def test_empty_filter_shows_all(self):
        source = DataViewTableModel()
        source.load_records([{'last_name': 'Test'}])
        proxy = MultiColumnFilterProxyModel()
        proxy.setSourceModel(source)
        assert proxy.rowCount() == 1
