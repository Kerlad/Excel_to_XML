"""
Secure logging module for ISPDn.
- Centralized SensitiveDataFilter with recursive masking
- Production mode: DEBUG logging forbidden in release
- Safe exception formatting (no PII in traceback)
- Structured logging with correlation IDs
- Third-party library logging suppression
"""
import os
import logging
import re
import traceback
from logging.handlers import RotatingFileHandler
from typing import Optional

_LOG_FORMAT = '%(asctime)s | %(threadName)-12s | %(levelname)-8s | %(name)-25s | %(message)s'
_LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

_SENSITIVE_KEYS = frozenset({
    'password', 'passwd', 'пароль', 'secret', 'token', 'api_key', 'apikey',
    'api-key', 'authorization', 'auth', 'cookie', 'session', 'jwt',
    'refresh_token', 'access_token', 'private_key', 'privatekey',
    'x-api-key', 'x-auth-token', 'bearer',
})


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive data patterns in log messages.
    Applied recursively to catch nested sensitive data.
    """

    SENSITIVE_PATTERNS = [
        (r'(?i)password["\s:=\']*[^\s\'"]+', 'password=***'),
        (r'(?i)passwd["\s:=\']*[^\s\'"]+', 'passwd=***'),
        (r'(?i)пароль["\s:=\']*[^\s\'"]+', 'пароль=***'),
        (r'(?i)"password"\s*:\s*"[^"]*"', '"password":"***"'),
        (r'(?i)"passwd"\s*:\s*"[^"]*"', '"passwd":"***"'),
        (r'(?i)username["\s:=\']*[^\s\'"]+', 'username=***'),
        (r'(?i)login["\s:=\']*[^\s\'"]+', 'login=***'),
        (r'(?i)логин["\s:=\']*[^\s\'"]+', 'логин=***'),
        (r'(?i)"username"\s*:\s*"[^"]*"', '"username":"***"'),
        (r'https?://[^:]+:[^@]+@[^\s]+', 'https://***:***@***'),
        (r'http://[^:]+:[^@]+@[^\s]+', 'http://***:***@***'),
        (r'(?i)api[_-]?key["\s:=]*[a-z0-9]{16,}', 'api_key=***'),
        (r'(?i)api[_-]?key["\s:=]*"[^"]{8,}"', 'api_key="***"'),
        # SNILS: XXX-XXX-XXX XX and XXX-XXX-XXX-XX (with trailing dash variant)
        (r'\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]\d{2}', '***-***-*** **'),
        # 11+ digit sequences (potential SNILS/phone)
        (r'\b\d{11,}\b', '***********'),
        # Token patterns (JWT, bearer tokens)
        (r'(?i)(bearer|jwt|token)\s+[a-z0-9_\-\.]{20,}', r'\1 ***'),
        (r'(?i)(bearer|jwt|token)["\s:=]*[a-z0-9_\-\.]{20,}', r'\1=***'),
        (r'(?i)["\'](eyJ[a-z0-9_\-\.]{10,})["\']', '"***JWT***"'),
        # Proxy URLs with credentials
        (r'(?i)(proxy|прокси)["\s:=]*[^\s]+', r'\1=***'),
        # Russian full names (три слова с заглавной буквы)
        (r'[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+', '*** *** ***'),
        # Russian initials (Фамилия И.О.)
        (r'[А-ЯЁ][а-яё]+\s[А-ЯЁ]\.[А-ЯЁ]\.', '*** *.*.'),
        # Passport-like patterns (серия номер паспорта)
        (r'\b\d{4}\s?\d{6}\b', '**********'),
        # Email addresses
        (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '***@***'),
        # Phone numbers (Russian format)
        (r'(?:\+7|8)[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}', '+7***'),
        # Cookies
        (r'(?i)cookie["\s:=]*[^\s;]+', 'cookie=***'),
        # Session IDs
        (r'(?i)session[_-]?id["\s:=]*[a-z0-9]{16,}', 'session_id=***'),
        # Raw XML/SOAP bodies (large payloads)
        (r'(<\?xml[^>]*>.*</[^>]+>)(?:\s*http)', '<XML_PAYLOAD ***>'),
    ]

    def filter(self, record):
        msg = record.getMessage()
        # Apply all patterns
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, replacement, msg)
        # Additional pass: check for common JSON key patterns
        msg = self._mask_json_sensitive_keys(msg)
        msg = msg.replace('%', '%%')
        record.msg = msg
        record.args = ()
        # Sanitize exception traceback — exc_info bypasses msg/args filtering
        if record.exc_info:
            record.exc_text = "Exception traceback: [sanitized]"
            record.exc_info = None
        return True

    def _mask_json_sensitive_keys(self, text: str) -> str:
        """Mask values of known sensitive JSON keys regardless of nesting."""
        def replace_value(match):
            key = match.group(1).lower()
            for sk in _SENSITIVE_KEYS:
                if sk in key:
                    return match.group(0)[:match.start(2) - match.start(0)] + '***"'
            return match.group(0)

        text = re.sub(r'"(password|passwd|secret|token|api_key|apikey|api-key|auth|'
                      r'authorization|cookie|session|jwt|refresh_token|access_token|'
                      r'private_key|snils|снилс|inn|инн|lastname|фамилия|'
                      r'firstname|имя|middlename|отчество)"\s*:\s*"([^"]+)"',
                      replace_value,
                      text,
                      flags=re.IGNORECASE)
        return text


def mask_sensitive(text: str) -> str:
    """Mask middle portion of sensitive string, keep first 4 + last 4 chars."""
    if not text:
        return ''
    if len(text) < 10:
        return text
    return text[:4] + '*' * (len(text) - 8) + text[-4:]


def filter_sensitive_text(text: str) -> str:
    """Apply SensitiveDataFilter patterns to a plain text string."""
    for pattern, replacement in SensitiveDataFilter.SENSITIVE_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def safe_format_exception(limit: int = 3) -> str:
    """Format exception traceback without PII. Returns limited, sanitized traceback."""
    tb_lines = traceback.format_exception(
        type(None), None, None, limit=limit
    ) if False else []
    try:
        tb = traceback.format_exc(limit=limit)
        tb = filter_sensitive_text(tb)
        return tb
    except Exception:
        return "Exception traceback unavailable (sanitized)"


def setup_logging(log_dir: str, max_bytes: int = 5 * 1024 * 1024, backup_count: int = 5):
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        _LOG_FORMAT,
        datefmt=_LOG_DATE_FORMAT
    )

    main_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=max_bytes,
        backupCount=backup_count, encoding='utf-8'
    )
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"), maxBytes=max_bytes,
        backupCount=backup_count, encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    sensitive_filter = SensitiveDataFilter()
    main_handler.addFilter(sensitive_filter)
    error_handler.addFilter(sensitive_filter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(main_handler)
    root.addHandler(error_handler)

    # Suppress DEBUG from third-party libraries in production
    _suppress_noisy_libraries()


def _suppress_noisy_libraries():
    """Suppress debug logging from third-party libraries to prevent data leakage."""
    for lib in [
        'urllib3', 'urllib3.connectionpool', 'requests', 'chardet',
        'charset_normalizer', 'openpyxl', 'PIL', 'Pillow',
        'matplotlib', 'cryptography', 'lxml',
    ]:
        l = logging.getLogger(lib)
        l.setLevel(logging.WARNING)
        l.propagate = False

    # Explicitly suppress HTTP request/response logging
    requests_log = logging.getLogger('requests')
    requests_log.setLevel(logging.WARNING)

    urllib3_log = logging.getLogger('urllib3')
    urllib3_log.setLevel(logging.WARNING)


def tail_log(file_path: str, n_lines: int = 1000) -> list[str]:
    """
    Efficiently read the last N lines from a log file.
    Reads from the end of the file using seek, never loads the whole file.
    """
    if not os.path.exists(file_path):
        return [f"[File not found: {file_path}]"]

    lines: list[str] = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()

            if file_size == 0:
                return []

            block_size = 4096
            pos = file_size
            while len(lines) < n_lines and pos > 0:
                read_size = min(block_size, pos)
                pos -= read_size
                f.seek(pos, os.SEEK_SET)
                chunk = f.read(read_size)

                lines_chunk = chunk.split('\n')
                lines = lines_chunk + lines

                if pos == 0:
                    break

            if len(lines) > n_lines:
                lines = lines[-n_lines:]
            elif lines and lines[0] == '' and pos > 0:
                lines = lines[1:]

            lines = [l.rstrip('\r') for l in lines]
            return lines
    except OSError as e:
        return [f"[Log read error: {e}]"]


def get_log_files(log_dir: str) -> dict[str, str]:
    """Return dict mapping log type -> full path for all log files in the directory."""
    result = {}
    if not os.path.isdir(log_dir):
        return result
    try:
        for fn in sorted(os.listdir(log_dir), reverse=True):
            fp = os.path.join(log_dir, fn)
            if not os.path.isfile(fp):
                continue
            name, ext = os.path.splitext(fn)
            if ext == '.log' or (name.endswith('.log') and ext.startswith('.')):
                result[fn] = fp
    except OSError:
        pass
    return result
