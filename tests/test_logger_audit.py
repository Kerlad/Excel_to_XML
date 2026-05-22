import sys, os, tempfile, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from utils.logger import SensitiveDataFilter, mask_sensitive, filter_sensitive_text, setup_logging
from utils.audit import setup_audit_log, log_audit, AUDIT_EVENTS
import logging


class TestSensitiveDataFilter:
    def test_snils_masking(self):
        result = filter_sensitive_text("SNILS: 123-456-789 00")
        assert "***-***-*** **" in result
        assert "123-456-789 00" not in result

    def test_api_key_masking(self):
        result = filter_sensitive_text("api_key=abcdef1234567890abcdef1234567890")
        assert "api_key=***" in result

    def test_password_masking(self):
        result = filter_sensitive_text('password=secret123')
        assert 'password=***' in result

    def test_username_masking(self):
        result = filter_sensitive_text('username=admin')
        assert 'username=***' in result

    def test_fio_masking(self):
        result = filter_sensitive_text('Иванов Иван Иванович')
        assert '*** *** ***' in result

    def test_short_fio_format(self):
        result = filter_sensitive_text('Иванов И.И.')
        assert '*** *.*.' in result

    def test_http_url_masked(self):
        result = filter_sensitive_text('http://user:pass@proxy:8080')
        assert '***' in result
        assert 'user:pass' not in result

    def test_filter_applied_to_log_record(self):
        filt = SensitiveDataFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "SNILS: 123-456-789 00", (), None)
        filt.filter(record)
        assert "***-***-*** **" in record.msg
        assert "123-456-789 00" not in record.msg

    def test_no_false_positives_short(self):
        result = mask_sensitive("short")
        assert result == "short"


class TestMaskSensitive:
    def test_mask_long_text(self):
        result = mask_sensitive("abcdefghijklmnop")
        assert len(result) == len("abcdefghijklmnop")
        assert result.startswith("abcd")
        assert result.endswith("mnop")
        assert "****" in result

    def test_mask_short_text(self):
        assert mask_sensitive("12345") == "12345"
        assert mask_sensitive("") == ""
        assert mask_sensitive(None) == ''


class TestAudit:
    def test_setup_audit_log(self):
        import logging
        audit_logger = logging.getLogger("audit")
        for h in audit_logger.handlers[:]:
            h.close()
            audit_logger.removeHandler(h)
        tmpdir = tempfile.mkdtemp()
        try:
            path = setup_audit_log(tmpdir)
            assert os.path.exists(path)
            log_audit("SEND_XML", "set_id=test123")
        finally:
            for h in audit_logger.handlers[:]:
                h.close()
                audit_logger.removeHandler(h)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "SEND_XML" in content or "XML sent" in content
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_audit_events_defined(self):
        assert "SEND_XML" in AUDIT_EVENTS
        assert "LOGIN" in AUDIT_EVENTS
        assert "BACKUP" in AUDIT_EVENTS

    def test_audit_log_without_detail(self):
        import logging
        audit_logger = logging.getLogger("audit")
        for h in audit_logger.handlers[:]:
            h.close()
            audit_logger.removeHandler(h)
        tmpdir = tempfile.mkdtemp()
        try:
            setup_audit_log(tmpdir)
            log_audit("BACKUP")
            path = os.path.join(tmpdir, "audit.log")
        finally:
            for h in audit_logger.handlers[:]:
                h.close()
                audit_logger.removeHandler(h)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "backup" in content.lower()
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestSetupLogging:
    def test_setup_logging_creates_files(self):
        import logging
        root = logging.getLogger()
        for h in root.handlers[:]:
            h.close()
            root.removeHandler(h)
        tmpdir = tempfile.mkdtemp()
        try:
            setup_logging(tmpdir)
            log_path = os.path.join(tmpdir, "app.log")
            assert os.path.exists(log_path)
        finally:
            for h in root.handlers[:]:
                h.close()
                root.removeHandler(h)
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
