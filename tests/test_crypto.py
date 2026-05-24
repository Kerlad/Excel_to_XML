import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import tempfile
from pathlib import Path

from utils.crypto import (
    encrypt_value, decrypt_value, encrypt_data, decrypt_data,
    hash_for_search, clear_caches, rotate_master_key,
    _compute_metadata_hmac, _HMAC_TAG_LENGTH,
    _load_existing_key, CryptoProductionModeError
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

    def test_encrypt_produces_different_ciphertexts(self):
        plain = "cache_test_value"
        enc1 = encrypt_value(plain)
        enc2 = encrypt_value(plain)
        assert enc1 != enc2
        assert decrypt_value(enc1) == plain
        assert decrypt_value(enc2) == plain

    def test_decrypt_without_cache_ok_calls_fernet_every_time(self):
        plain = "test"
        enc = encrypt_value(plain)
        from utils.crypto import _fernet
        original_fernet = _fernet
        call_count = [0]
        def mock_fernet():
            call_count[0] += 1
            return original_fernet()
        import utils.crypto
        utils.crypto._fernet = mock_fernet
        try:
            decrypt_value(enc)
            decrypt_value(enc)
            assert call_count[0] >= 2
        finally:
            utils.crypto._fernet = original_fernet

    def test_decrypt_with_cache_ok_caches(self):
        plain = "cache_ok_test_value"
        enc = encrypt_value(plain)
        from utils.crypto import _fernet
        original_fernet = _fernet
        call_count = [0]
        def mock_fernet():
            call_count[0] += 1
            return original_fernet()
        import utils.crypto
        utils.crypto._fernet = mock_fernet
        try:
            decrypt_value(enc, cache_ok=True)
            decrypt_value(enc, cache_ok=True)
            assert call_count[0] == 1
        finally:
            utils.crypto._fernet = original_fernet

    def test_decrypt_wrong_key_after_cache_clear(self):
        plain = "test"
        enc = encrypt_value(plain)
        assert decrypt_value(enc) == plain
        clear_caches()
        assert decrypt_value(enc) == plain

    def test_hmac_tag_length(self):
        tag = _compute_metadata_hmac({"version": 3})
        assert len(tag) == _HMAC_TAG_LENGTH
        assert len(tag) == 32

    def test_load_existing_key_blocks_plaintext_when_pd_data_exists(self, monkeypatch):
        monkeypatch.setattr("utils.crypto._has_any_encrypted_data", lambda: True)
        monkeypatch.setattr("utils.crypto._is_production_mode", lambda: False)

        with tempfile.TemporaryDirectory() as tmpdir:
            kf = Path(tmpdir) / "master.key"
            kd = Path(tmpdir)
            kf.write_bytes(b'\x02' * 32)

            with pytest.raises(CryptoProductionModeError):
                _load_existing_key(kf, kd)

    def test_rotate_master_key_zeros_old_key(self, monkeypatch):
        zero_memory_called = []
        zero_memory_bytes_called = []
        fake_key = b'\x02' * 32

        def track_zero_memory(data):
            zero_memory_called.append(True)

        def track_zero_memory_bytes(data):
            zero_memory_bytes_called.append(True)

        monkeypatch.setattr("utils.crypto._zero_memory", track_zero_memory)
        monkeypatch.setattr("utils.crypto._zero_memory_bytes", track_zero_memory_bytes)
        monkeypatch.setattr("utils.crypto._get_or_create_master_key", lambda: fake_key)
        monkeypatch.setattr("utils.crypto.os.urandom", lambda n: b'\x01' * n)
        monkeypatch.setattr("utils.crypto._write_key_file", lambda kf, kb: None)
        monkeypatch.setattr("utils.crypto._save_key_metadata", lambda m: None)
        monkeypatch.setattr("utils.crypto._load_key_metadata", lambda: {})
        monkeypatch.setattr("utils.crypto._is_production_mode", lambda: False)

        ok, _ = rotate_master_key()
        assert ok

        assert len(zero_memory_called) >= 1
        assert len(zero_memory_bytes_called) >= 1
