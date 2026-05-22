import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from importers.error_report import export_error_report


class TestErrorReport:
    def test_export_error_report(self):
        error_details = [
            {'row': 2, 'type': 'Ошибка', 'field': 'СНИЛС', 'message': 'Invalid SNILS'},
            {'row': 3, 'type': 'Ошибка', 'field': 'Программа', 'message': 'Invalid program'}
        ]
        duplicate_map = {
            ('123-456-789 00', '1'): ['строка 4', 'строка 5']
        }
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        try:
            success, msg = export_error_report(error_details, duplicate_map, path)
            assert success
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_export_error_report_empty(self):
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        try:
            success, msg = export_error_report([], {}, path)
            assert success
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_export_error_report_invalid_path(self):
        success, msg = export_error_report([], {}, "/invalid/path/file.xlsx")
        assert not success
