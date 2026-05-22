import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from exporters.xml_exporter import (
    build_xml, export_to_xml, format_snils, format_date_xsd, is_passed
)


class TestXmlExport:
    def test_format_snils_standard(self):
        assert format_snils("12345678900") == "123-456-789 00"

    def test_format_snils_with_dashes(self):
        assert format_snils("123-456-789 00") == "123-456-789 00"

    def test_format_snils_short(self):
        assert format_snils("12345") == "12345"

    def test_format_snils_empty(self):
        assert format_snils("") == ""

    def test_format_date_xsd_ddmmyyyy_dots(self):
        assert format_date_xsd("25.09.2025") == "2025-09-25"

    def test_format_date_xsd_ddmmyyyy_dashes(self):
        assert format_date_xsd("25-09-2025") == "2025-09-25"

    def test_format_date_xsd_iso(self):
        assert format_date_xsd("2025-09-25") == "2025-09-25"

    def test_format_date_xsd_empty(self):
        assert format_date_xsd("") is None

    def test_format_date_xsd_invalid(self):
        assert format_date_xsd("not-a-date") is None

    def test_is_passed_satisfactory(self):
        assert is_passed("Удовлетворительно") == "true"

    def test_is_passed_unsatisfactory(self):
        assert is_passed("Неудовлетворительно") == "false"

    def test_is_passed_unknown(self):
        assert is_passed("") == "false"

    def test_build_xml_single_record(self):
        records = [{
            'last_name': 'Иванов', 'first_name': 'Иван', 'middle_name': 'Иванович',
            'snils': '12345678900', 'position': 'Инженер',
            'employer_inn': '7701123456', 'employer_title': 'ООО Тест',
            'tc_inn': '7701123456', 'tc_title': 'УЦ Тест',
            'result': 'Удовлетворительно', 'program': '1', 'date': '25.09.2025', 'protocol': 'П-001'
        }]
        xml_bytes = build_xml(records)
        xml_str = xml_bytes.decode('utf-8')
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml_str
        assert '<RegistrySet>' in xml_str
        assert '<RegistryRecord' in xml_str
        assert '<LastName>Иванов</LastName>' in xml_str
        assert '<FirstName>Иван</FirstName>' in xml_str
        assert '<Snils>123-456-789 00</Snils>' in xml_str
        assert '<Test isPassed="true" learnProgramId="1">' in xml_str

    def test_build_xml_multiple_records(self):
        records = [
            {'last_name': 'A', 'first_name': 'B', 'middle_name': 'C',
             'snils': '11111111111', 'position': 'P1',
             'employer_inn': '111', 'employer_title': 'ET1',
             'tc_inn': '111', 'tc_title': 'TC1',
             'result': 'Удовлетворительно', 'program': '2', 'date': '01.01.2025', 'protocol': 'P1'},
            {'last_name': 'D', 'first_name': 'E', 'middle_name': 'F',
             'snils': '22222222222', 'position': 'P2',
             'employer_inn': '222', 'employer_title': 'ET2',
             'tc_inn': '222', 'tc_title': 'TC2',
             'result': 'Неудовлетворительно', 'program': '3', 'date': '02.01.2025', 'protocol': 'P2'}
        ]
        xml_bytes = build_xml(records)
        xml_str = xml_bytes.decode('utf-8')
        assert xml_str.count('<RegistryRecord') == 2

    def test_export_to_xml_file(self):
        records = [{
            'last_name': 'Тест', 'first_name': 'Тест', 'middle_name': 'Тест',
            'snils': '33333333333', 'position': 'Тест',
            'employer_inn': '333', 'employer_title': 'ООО Тест',
            'tc_inn': '333', 'tc_title': 'УЦ Тест',
            'result': 'Удовлетворительно', 'program': '1', 'date': '15.05.2025', 'protocol': 'П-001'
        }]
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            path = f.name
        try:
            success, msg = export_to_xml(records, path)
            assert success
            assert os.path.exists(path)
            with open(path, 'rb') as f:
                content = f.read()
            assert b'<RegistrySet>' in content
            assert b'<LastName>' in content
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_export_to_xml_empty(self):
        success, msg = export_to_xml([], 'dummy.xml')
        assert not success
        assert 'Нет данных' in msg

    def test_export_to_xml_too_many(self):
        records = [{'last_name': 'T', 'first_name': 'T', 'middle_name': 'T',
                    'snils': '12345678900', 'position': 'T',
                    'employer_inn': '1', 'employer_title': 'T',
                    'tc_inn': '1', 'tc_title': 'T',
                    'result': 'Удовлетворительно', 'program': '1',
                    'date': '01.01.2025', 'protocol': 'P'}] * 5001
        success, msg = export_to_xml(records, 'dummy.xml')
        assert not success
        assert '5000' in msg

    def test_build_xml_org_settings(self):
        records = [{
            'last_name': 'Иван', 'first_name': 'Иван', 'middle_name': 'Иван',
            'snils': '44444444444', 'position': 'Инж',
            'employer_inn': '444', 'employer_title': 'ООО',
            'tc_inn': '', 'tc_title': '',
            'result': 'Удовлетворительно', 'program': '1', 'date': '01.01.2025', 'protocol': 'П'
        }]
        org_settings = {'tc_inn': '999888777', 'tc_title': 'ООО УЦ'}
        xml_bytes = build_xml(records, org_settings)
        xml_str = xml_bytes.decode('utf-8')
        assert '<Inn>999888777</Inn>' in xml_str
        assert '<Title>ООО УЦ</Title>' in xml_str

    def test_xml_escaping(self):
        records = [{
            'last_name': 'Иванов', 'first_name': 'Иван', 'middle_name': 'Иванович',
            'snils': '55555555555', 'position': 'Инженер <тест>',
            'employer_inn': '555', 'employer_title': 'ООО "Тест" & Co',
            'tc_inn': '555', 'tc_title': 'УЦ',
            'result': 'Удовлетворительно', 'program': '1',
            'date': '01.01.2025', 'protocol': 'П-001'
        }]
        xml_bytes = build_xml(records)
        xml_str = xml_bytes.decode('utf-8')
        assert '&lt;тест&gt;' in xml_str or '&lt;' in xml_str
        assert '&amp;' in xml_str
