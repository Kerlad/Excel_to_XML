"""
Tests for audit log HMAC verification and integrity checking.
"""
import os
import re
import json
import hmac
import hashlib
import tempfile
import logging
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock


def _cleanup_audit_logger():
    audit_logger = logging.getLogger("audit")
    for h in audit_logger.handlers[:]:
        h.close()
        audit_logger.removeHandler(h)


class TestAuditVerification:
    """Tests for verify_audit_log functionality."""

    def _cleanup_and_setup(self, tmpdir):
        _cleanup_audit_logger()
        from utils.audit import setup_audit_log, _PREV_HASH, _AUDIT_HMAC_KEY
        import utils.audit as audit_mod
        audit_mod._PREV_HASH = "0" * 64
        log_path = setup_audit_log(tmpdir)
        return log_path

    def test_verify_clean_audit_log(self):
        """Verify that an unmodified audit log passes integrity check."""
        from utils.audit import log_audit, verify_audit_log

        tmpdir = tempfile.mkdtemp()
        try:
            log_path = self._cleanup_and_setup(tmpdir)
            log_audit("STARTUP", "Test startup")
            log_audit("SHUTDOWN", "Test shutdown")
            _cleanup_audit_logger()

            violations = verify_audit_log(log_path)
            assert violations == [], f"Expected no violations, got: {violations}"
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_verify_tampered_audit_log(self):
        """Verify that a modified audit log is detected."""
        from utils.audit import log_audit, verify_audit_log

        tmpdir = tempfile.mkdtemp()
        try:
            log_path = self._cleanup_and_setup(tmpdir)
            log_audit("STARTUP", "Before tamper")
            _cleanup_audit_logger()

            fake_tag = "f" * 64
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"2025-01-01 12:00:00 | [{fake_tag}] TAMPERED | malicious data\n")

            violations = verify_audit_log(log_path)
            assert len(violations) > 0, f"Expected violations for tampered log, got {len(violations)}"
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_hmac_tag_length_64(self):
        """Verify new audit entries use 64-char HMAC tags."""
        from utils.audit import log_audit

        tmpdir = tempfile.mkdtemp()
        try:
            log_path = self._cleanup_and_setup(tmpdir)
            log_audit("STARTUP", "Tag length test")
            _cleanup_audit_logger()

            with open(log_path, 'r', encoding='utf-8') as f:
                line = f.readline()
            match = re.search(r'\[([a-f0-9]+)\]', line)
            assert match, f"No HMAC tag found in: {line}"
            tag = match.group(1)
            assert len(tag) == 64, f"Expected 64-char tag, got {len(tag)}: {tag}"
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    @patch('utils.crypto.get_key_fingerprint')
    def test_no_hmac_key_no_tag(self, mock_fingerprint):
        """Without master key, entries should have [no-hmac] tag."""
        mock_fingerprint.side_effect = Exception("No key")
        from utils.audit import log_audit

        import utils.audit as audit_mod
        audit_mod._AUDIT_HMAC_KEY = None

        tmpdir = tempfile.mkdtemp()
        try:
            log_path = self._cleanup_and_setup(tmpdir)
            log_audit("STARTUP", "No key test")
            _cleanup_audit_logger()

            with open(log_path, 'r', encoding='utf-8') as f:
                line = f.readline()
            assert '[no-hmac]' in line, f"Expected [no-hmac] tag in: {line}"
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_hash_chaining(self):
        """Verify that hash chaining detects reordering of entries."""
        from utils.audit import log_audit, verify_audit_log

        tmpdir = tempfile.mkdtemp()
        try:
            log_path = self._cleanup_and_setup(tmpdir)
            log_audit("STARTUP", "First entry")
            log_audit("LOGIN", "Second entry")
            _cleanup_audit_logger()

            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(lines[1])
                f.write(lines[0])

            violations = verify_audit_log(log_path)
            assert len(violations) > 0, f"Expected violations for reordered entries, got {len(violations)}"
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
