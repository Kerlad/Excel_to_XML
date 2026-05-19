import os
import sys
import tempfile
import xml.etree.ElementTree as ET
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from exporters.xml_exporter import build_xml, export_to_xml, format_snils, format_date_xsd


SAMPLE_RECORDS = [
    {
        'last_name': 'Иванов',
        'first_name': 'Иван',
        'middle_name': 'Иванович',
        'snils': '12345678900',
        'position': 'Инженер',
        'employer_inn': '7701234567',
        'employer_title': 'ООО Ромашка',
        'tc_inn': '7701234567',
        'tc_title': 'УЦ Знание',
        'result': 'Удовлетворительно',
        'program': '1',
        'date': '01.01.2025',
        'protocol': 'П-001'
    }
]


class TestXmlExport:
    def test_xml_generation(self):
        xml_content = build_xml(SAMPLE_RECORDS)
        assert xml_content is not None
        root = ET.fromstring(xml_content)
        assert root.tag == "RegistrySet"

    def test_required_fields_present(self):
        xml_content = build_xml(SAMPLE_RECORDS)
        root = ET.fromstring(xml_content)
        record = root.find("RegistryRecord")
        worker = record.find("Worker")
        assert worker.find("LastName").text == "Иванов"
        assert worker.find("FirstName").text == "Иван"
        assert worker.find("Snils").text is not None
        test = record.find("Test")
        assert test.get("isPassed") == "true"
        assert test.get("learnProgramId") == "1"

    def test_xml_escaping(self):
        records = [{
            'last_name': 'Test<>&',
            'first_name': 'User',
            'middle_name': '',
            'snils': '12345678900',
            'position': 'Engineer',
            'employer_inn': '',
            'employer_title': 'Org<>&',
            'tc_inn': '',
            'tc_title': 'Center',
            'result': 'Удовлетворительно',
            'program': '1',
            'date': '01.01.2025',
            'protocol': 'P-001'
        }]
        xml_content = build_xml(records)
        root = ET.fromstring(xml_content)
        record = root.find("RegistryRecord")
        worker = record.find("Worker")
        assert worker.find("LastName").text == 'Test<>&'
        employer = worker.find("EmployerTitle")
        assert employer.text == 'Org<>&'

    def test_malformed_values_handled(self):
        records = [{
            'last_name': '',
            'first_name': '',
            'middle_name': '',
            'snils': None,
            'position': None,
            'employer_inn': '',
            'employer_title': '',
            'tc_inn': '',
            'tc_title': '',
            'result': '',
            'program': '',
            'date': 'invalid',
            'protocol': ''
        }]
        # Should not raise any exception
        xml_content = build_xml(records)
        root = ET.fromstring(xml_content)
        record = root.find("RegistryRecord")
        assert record is not None
        worker = record.find("Worker")
        assert worker is not None

    def test_format_snils(self):
        assert format_snils("12345678900") == "123-456-789 00"
        assert format_snils(" 123-456-789 00 ") == "123-456-789 00"
        assert format_snils("invalid") == "invalid"

    def test_format_date_xsd(self):
        assert format_date_xsd("01.01.2025") == "2025-01-01"
        assert format_date_xsd("2025-01-01") == "2025-01-01"
