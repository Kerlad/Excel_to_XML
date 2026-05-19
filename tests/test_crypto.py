import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.crypto import encrypt_value, decrypt_value, encrypt_data, decrypt_data


class TestCryptoRoundtrip:
    def test_encrypt_decrypt_value(self):
        plain = "Иванов"
        encrypted = encrypt_value(plain)
        assert encrypted != plain
        assert decrypt_value(encrypted) == plain

    def test_encrypt_decrypt_empty(self):
        assert encrypt_value('') == ''
        assert decrypt_value('') == ''

    def test_encrypt_decrypt_data(self):
        data = {"key": "value", "num": 42}
        encrypted = encrypt_data(data)
        assert isinstance(encrypted, str)
        assert decrypt_data(encrypted) == data

    def test_decrypt_corrupted_value(self):
        result = decrypt_value("corrupted!@#$")
        assert result == ''

    def test_decrypt_corrupted_data(self):
        result = decrypt_data("not valid data")
        assert result == {}

    def test_encrypt_decrypt_special_chars(self):
        plain = "test<>'\"&<>test"
        encrypted = encrypt_value(plain)
        assert decrypt_value(encrypted) == plain
