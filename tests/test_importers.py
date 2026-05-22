import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from importers.xlsx_importer import (
    format_snils, FieldValidator, validate_row, load_xlsx
)
from importers.xml_importer import load_xml
from utils.crypto import clear_caches


class TestFormatSnils:
    def test_format_snils_11_digits(self):
        assert format_snils("12345678900") == "123-456-789 00"

    def test_format_snils_with_dashes_and_spaces(self):
        assert format_snils("123-456-789 00") == "123-456-789 00"

    def test_format_snils_nbsp(self):
        assert format_snils("123\u00a0456\u00a0789\u00a000") == "123-456-789 00"

    def test_format_snils_invalid_short(self):
        assert format_snils("12345") is None

    def test_format_snils_invalid_letters(self):
        assert format_snils("1234567890A") is None

    def test_format_snils_empty(self):
        assert format_snils("") is None


class TestFieldValidator:
    def test_validate_snils_valid(self):
        assert FieldValidator.validate_snils("12345678900", 1) is None

    def test_validate_snils_invalid(self):
        err = FieldValidator.validate_snils("123", 5)
        assert err is not None
        assert err['row'] == 5
        assert '11' in err['message']

    def test_validate_program_valid(self):
        assert FieldValidator.validate_program("1", 1) is None

    def test_validate_program_valid_multiple(self):
        assert FieldValidator.validate_program("1,2,3", 1) is None

    def test_validate_program_invalid(self):
        err = FieldValidator.validate_program("99", 3)
        assert err is not None
        assert '99' in err['message']

    def test_validate_program_mixed(self):
        err = FieldValidator.validate_program("1,99,2", 4)
        assert err is not None
        assert '99' in err['message']

    def test_validate_result_satisfactory(self):
        assert FieldValidator.validate_result("Удовлетворительно", 1) is None

    def test_validate_result_unsatisfactory(self):
        assert FieldValidator.validate_result("Неудовлетворительно", 1) is None

    def test_validate_result_invalid(self):
        err = FieldValidator.validate_result("Unknown", 2)
        assert err is not None
        assert 'Удовлетворительно' in err['message']

    def test_validate_name_valid(self):
        assert FieldValidator.validate_name("Фамилия", "Иванов", 1) is None

    def test_validate_name_with_hyphen(self):
        assert FieldValidator.validate_name("Фамилия", "Иванов-Петров", 1) is None

    def test_validate_name_invalid(self):
        err = FieldValidator.validate_name("Фамилия", "Иванов123", 2)
        assert err is not None

    def test_validate_name_empty(self):
        assert FieldValidator.validate_name("Фамилия", "", 1) is None

    def test_validate_date_ddmmyyyy(self):
        result = FieldValidator.validate_date("25.09.2025", 1)
        assert result == "25.09.2025"

    def test_validate_date_datetime(self):
        from datetime import datetime
        result = FieldValidator.validate_date(datetime(2025, 9, 25), 1)
        assert result == "25.09.2025"

    def test_validate_date_serial(self):
        result = FieldValidator.validate_date(45000, 1)
        assert isinstance(result, str)
        assert '.' in result

    def test_validate_date_empty(self):
        err = FieldValidator.validate_date(None, 1)
        assert isinstance(err, dict)

    def test_validate_required_empty(self):
        err = FieldValidator.validate_required("СНИЛС", "", 5)
        assert err is not None
        assert 'Пустое' in err['message']

    def test_validate_required_filled(self):
        assert FieldValidator.validate_required("СНИЛС", "12345678900", 5) is None


class TestValidateRow:
    def test_valid_row_single_program(self):
        row = {
            'Фамилия': 'Иванов', 'Имя': 'Иван', 'Отчество': 'Иванович',
            'СНИЛС': '12345678900', 'Должность': 'Инженер',
            'ИНН Заказчика': '7701123456', 'Наименование ЮЛ Заказчика': 'ООО Тест',
            'ИНН УЦ': '7701123456', 'Наименование УЦ': 'УЦ Тест',
            'Результат': 'Удовлетворительно', '№ программы': '1',
            'Дата': '25.09.2025', '№ протокола': 'П-001'
        }
        valid, result = validate_row(row, 2)
        assert valid
        assert len(result) == 1
        assert result[0]['last_name'] == 'Иванов'
        assert result[0]['program'] == '1'

    def test_valid_row_multiple_programs(self):
        row = {
            'Фамилия': 'Петров', 'Имя': 'Петр', 'Отчество': 'Петрович',
            'СНИЛС': '11122233344', 'Должность': 'Инженер',
            'ИНН Заказчика': '7701', 'Наименование ЮЛ Заказчика': 'ООО',
            'ИНН УЦ': '7702', 'Наименование УЦ': 'УЦ',
            'Результат': 'Удовлетворительно', '№ программы': '1,2,3',
            'Дата': '01.01.2025', '№ протокола': 'П-001'
        }
        valid, result = validate_row(row, 2)
        assert valid
        assert len(result) == 3

    def test_invalid_snils(self):
        row = {
            'Фамилия': 'Иван', 'Имя': 'Иван', 'Отчество': 'Иван',
            'СНИЛС': '123', 'Должность': 'Инж',
            'ИНН Заказчика': '', 'Наименование ЮЛ Заказчика': '',
            'ИНН УЦ': '', 'Наименование УЦ': '',
            'Результат': 'Удовлетворительно', '№ программы': '1',
            'Дата': '01.01.2025', '№ протокола': ''
        }
        valid, errors = validate_row(row, 2)
        assert not valid

    def test_missing_snils(self):
        row = {
            'Фамилия': 'Иван', 'Имя': 'Иван', 'Отчество': 'Иван',
            'СНИЛС': '', 'Должность': 'Инж',
            'ИНН Заказчика': '', 'Наименование ЮЛ Заказчика': '',
            'ИНН УЦ': '', 'Наименование УЦ': '',
            'Результат': 'Удовлетворительно', '№ программы': '1',
            'Дата': '01.01.2025', '№ протокола': ''
        }
        valid, errors = validate_row(row, 2)
        assert not valid

    def test_invalid_program(self):
        row = {
            'Фамилия': 'Иван', 'Имя': 'Иван', 'Отчество': 'Иван',
            'СНИЛС': '12345678900', 'Должность': 'Инж',
            'ИНН Заказчика': '', 'Наименование ЮЛ Заказчика': '',
            'ИНН УЦ': '', 'Наименование УЦ': '',
            'Результат': 'Удовлетворительно', '№ программы': '99',
            'Дата': '01.01.2025', '№ протокола': ''
        }
        valid, errors = validate_row(row, 2)
        assert not valid


class TestLoadXlsx:
    def test_load_nonexistent(self):
        result = load_xlsx("nonexistent.xlsx")
        assert result[0] is None

    def test_load_invalid_extension(self):
        result = load_xlsx("test.xls")
        assert result[0] is None


class TestLoadXml:
    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_xml("nonexistent.xml")

    def test_load_invalid_xml(self):
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w') as f:
            f.write("not xml")
            path = f.name
        try:
            result = load_xml(path)
            assert result[0] is None
        finally:
            os.remove(path)

    def test_load_registry_set_xml(self):
        xml_content = '''<?xml version="1.0"?>
<RegistrySet>
    <RegistryRecord>
        <Worker>
            <LastName>Иванов</LastName><FirstName>Иван</FirstName><MiddleName>Иванович</MiddleName>
            <Snils>123-456-789 00</Snils><Position>Инженер</Position>
            <EmployerInn>7701123456</EmployerInn><EmployerTitle>ООО Тест</EmployerTitle>
        </Worker>
        <Organization><Inn>7701123456</Inn><Title>УЦ Тест</Title></Organization>
        <Test isPassed="true" learnProgramId="1">
            <Date>2025-09-25</Date><ProtocolNumber>П-001</ProtocolNumber><LearnProgramTitle>Первая помощь</LearnProgramTitle>
        </Test>
    </RegistryRecord>
</RegistrySet>'''
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as f:
            f.write(xml_content)
            path = f.name
        try:
            records, err_count, err_msgs, xsd_errors = load_xml(path)
            assert len(records) == 1
            assert records[0]['last_name'] == 'Иванов'
            assert records[0]['program'] == '1'
            assert records[0]['date'] == '25.09.2025'
            assert err_count == 0
        finally:
            os.remove(path)

    def test_load_registry_set_invalid_program(self):
        xml_content = '''<?xml version="1.0"?>
<RegistrySet>
    <RegistryRecord>
        <Worker>
            <LastName>Test</LastName><FirstName>Test</FirstName><MiddleName>Test</MiddleName>
            <Snils>12345678900</Snils><Position>Test</Position>
            <EmployerInn>7701</EmployerInn><EmployerTitle>Test</EmployerTitle>
        </Worker>
        <Organization><Inn>7701</Inn><Title>Test</Title></Organization>
        <Test isPassed="true" learnProgramId="99">
            <Date>2025-09-25</Date><ProtocolNumber>P</ProtocolNumber>
        </Test>
    </RegistryRecord>
</RegistrySet>'''
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as f:
            f.write(xml_content)
            path = f.name
        try:
            records, err_count, err_msgs, xsd_errors = load_xml(path)
            assert len(records) == 0
            assert err_count >= 1
        finally:
            os.remove(path)

    def test_load_registry_set_missing_worker(self):
        xml_content = '''<?xml version="1.0"?>
<RegistrySet>
    <RegistryRecord>
        <Organization><Inn>7701</Inn><Title>Test</Title></Organization>
    </RegistryRecord>
</RegistrySet>'''
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as f:
            f.write(xml_content)
            path = f.name
        try:
            records, err_count, err_msgs, xsd_errors = load_xml(path)
            assert len(records) == 0
            assert err_count >= 1
        finally:
            os.remove(path)

    def test_load_xml_empty(self):
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as f:
            f.write('<?xml version="1.0"?><RegistrySet/>')
            path = f.name
        try:
            records, err_count, err_msgs, xsd_errors = load_xml(path)
            assert len(records) == 0
        finally:
            os.remove(path)
