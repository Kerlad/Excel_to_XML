"""
Tests for crypto module thread safety and memory safety.
"""
import os
import threading
import tempfile
import pytest
from unittest.mock import patch


class TestCryptoThreadSafety:
    """Tests for thread safety of crypto module."""

    def test_concurrent_encrypt(self):
        """Ensure concurrent encrypt_value calls don't crash."""
        from utils.crypto import encrypt_value

        results = []
        errors = []

        def encrypt_thread(val):
            try:
                result = encrypt_value(val)
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t = threading.Thread(target=encrypt_thread, args=(f"test_value_{i}",))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent encrypt errors: {errors}"
        assert len(results) == 10

    def test_concurrent_encrypt_decrypt(self):
        """Encrypt and decrypt concurrently without data corruption."""
        from utils.crypto import encrypt_value, decrypt_value

        encrypted = {}
        errors = []

        def encrypt_thread(idx, val):
            try:
                encrypted[idx] = encrypt_value(val)
            except Exception as e:
                errors.append(f"encrypt {idx}: {e}")

        def decrypt_thread(idx):
            try:
                if idx in encrypted:
                    plain = decrypt_value(encrypted[idx])
                    assert plain == f"data_{idx}", f"Mismatch: {plain} != data_{idx}"
            except Exception as e:
                errors.append(f"decrypt {idx}: {e}")

        threads = []
        for i in range(5):
            t = threading.Thread(target=encrypt_thread, args=(i, f"data_{i}"))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        threads = []
        for i in range(5):
            t = threading.Thread(target=decrypt_thread, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent errors: {errors}"

    @patch('utils.crypto._is_production_mode')
    def test_cache_reverse_direction(self, mock_prod):
        """Ensure non-PD cache stores ciphertext->plaintext (not plaintext->ciphertext)."""
        from utils.crypto import encrypt_value, decrypt_value, _NON_PD_CACHE

        mock_prod.return_value = False
        _NON_PD_CACHE.clear()

        plain = "test_sensitive_123"
        cipher = encrypt_value(plain)

        # Encrypt does not cache; verify decrypt with cache_ok=True caches ciphertext
        result = decrypt_value(cipher, cache_ok=True)

        # Cache should contain ciphertext as key
        assert cipher in _NON_PD_CACHE, \
            f"Cache should have ciphertext key, has: {list(_NON_PD_CACHE.keys())[:3]}"
        assert _NON_PD_CACHE[cipher] == plain
        assert result == plain

        # Second call should return from cache
        from unittest.mock import patch as _patch
        with _patch('utils.crypto._fernet') as mock_fernet:
            result2 = decrypt_value(cipher, cache_ok=True)
            assert result2 == plain
            mock_fernet.assert_not_called()
