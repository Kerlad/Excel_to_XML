import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from utils.crypto import (
    encrypt_value, decrypt_value, encrypt_data, decrypt_data,
    hash_for_search, clear_caches
)


@pytest.fixture(autouse=True)
def reset_cache():
    clear_caches()
    yield
    clear_caches()


class TestCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        plain = "Иванов Иван Иванович"
        enc = encrypt_value(plain)
        assert enc != plain
        assert enc != ''
        dec = decrypt_value(enc)
        assert dec == plain

    def test_empty_string(self):
        assert encrypt_value('') == ''
        assert decrypt_value('') == ''

    def test_special_characters(self):
        plain = "test<>'\"&@#$%^&*()_+=-[]{}|;:',./?~`"
        dec = decrypt_value(encrypt_value(plain))
        assert dec == plain

    def test_long_string(self):
        plain = "A" * 10000
        dec = decrypt_value(encrypt_value(plain))
        assert dec == plain

    def test_unicode_multilingual(self):
        plain = "日本語 Русский English 中文"
        dec = decrypt_value(encrypt_value(plain))
        assert dec == plain

    def test_numbers_only(self):
        plain = "1234567890"
        dec = decrypt_value(encrypt_value(plain))
        assert dec == plain

    def test_encrypt_data_roundtrip(self):
        data = {"key": "value", "list": [1, 2, 3], "nested": {"a": 1}}
        enc = encrypt_data(data)
        assert isinstance(enc, str)
        dec = decrypt_data(enc)
        assert dec == data

    def test_encrypt_data_empty(self):
        assert decrypt_data('') == {}

    def test_decrypt_invalid(self):
        assert decrypt_value("invalid_encrypted_data") == ''

    def test_hash_for_search(self):
        h1 = hash_for_search("123-456-789 00")
        h2 = hash_for_search("12345678900")
        h3 = hash_for_search("123-456-78900")
        assert h1 == h2
        assert h2 == h3
        assert len(h1) == 64

    def test_hash_for_search_normalized(self):
        h1 = hash_for_search(" 123-456-789 00 ")
        h2 = hash_for_search("12345678900")
        assert h1 == h2

    def test_encrypt_cache_hit(self):
        plain = "cache_test_value"
        enc1 = encrypt_value(plain)
        enc2 = encrypt_value(plain)
        assert enc1 == enc2
        assert decrypt_value(enc1) == plain

    def test_decrypt_wrong_key_after_cache_clear(self):
        plain = "test"
        enc = encrypt_value(plain)
        assert decrypt_value(enc) == plain
        clear_caches()
        assert decrypt_value(enc) == plain
