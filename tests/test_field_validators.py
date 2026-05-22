import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from utils.field_validators import (
    validate_snils, validate_required, validate_program_id, validate_date, validate_name
)


class TestFieldValidators:
    def test_validate_snils_valid(self):
        assert validate_snils("123-456-789 00") is None
        assert validate_snils("12345678900") is None

    def test_validate_snils_empty(self):
        assert validate_snils("") is None

    def test_validate_snils_invalid_short(self):
        err = validate_snils("12345")
        assert err is not None
        assert '11' in err

    def test_validate_snils_invalid_letters(self):
        err = validate_snils("1234567890A")
        assert err is not None

    def test_validate_required_empty(self):
        err = validate_required("", "Тест")
        assert err is not None
        assert 'Тест' in err

    def test_validate_required_filled(self):
        assert validate_required("value", "Тест") is None

    def test_validate_required_whitespace(self):
        err = validate_required("   ", "Поле")
        assert err is not None

    def test_validate_program_id_valid(self):
        for pid in ["1", "2", "3", "4", "6", "10", "29"]:
            assert validate_program_id(pid) is None

    def test_validate_program_id_invalid(self):
        err = validate_program_id("5")
        assert err is not None
        err = validate_program_id("99")
        assert err is not None
        err = validate_program_id("0")
        assert err is not None

    def test_validate_program_id_empty(self):
        assert validate_program_id("") is None

    def test_validate_date_valid(self):
        assert validate_date("25.09.2025") is None

    def test_validate_date_with_dashes(self):
        assert validate_date("25-09-2025") is None

    def test_validate_date_invalid_format(self):
        err = validate_date("2025-09-25")
        assert err is not None

    def test_validate_date_empty(self):
        assert validate_date("") is None

    def test_validate_date_future(self):
        err = validate_date("01.01.2099")
        assert err is not None
        assert 'больше' in err.lower() or 'текущ' in err.lower()

    def test_validate_name_valid(self):
        assert validate_name("Иванов") is None
        assert validate_name("Иванов-Петров") is None

    def test_validate_name_invalid(self):
        err = validate_name("Иванов123")
        assert err is not None

    def test_validate_name_empty(self):
        assert validate_name("") is None
