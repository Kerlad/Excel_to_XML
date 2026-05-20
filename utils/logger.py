import os
import logging
import re
from logging.handlers import RotatingFileHandler


class SensitiveDataFilter(logging.Filter):
    SENSITIVE_PATTERNS = [
        (r'(?i)password["\s:]*[^\s"]*', 'password=***'),
        (r'(?i)passwd["\s:]*[^\s"]*', 'passwd=***'),
        (r'(?i)пароль["\s:]*[^\s"]*', 'пароль=***'),
        (r'(?i)"password"\s*:\s*"[^"]*"', '"password":"***"'),
        (r'(?i)username["\s:]*[^\s"]*', 'username=***'),
        (r'(?i)login["\s:]*[^\s"]*', 'login=***'),
        (r'(?i)логин["\s:]*[^\s"]*', 'логин=***'),
        (r'(?i)"username"\s*:\s*"[^"]*"', '"username":"***"'),
        (r'https?://[^:]+:[^@]+@[^\s]+', 'https://***:***@***'),
        (r'http://[^:]+:[^@]+@[^\s]+', 'http://***:***@***'),
        (r'(?i)api[_-]?key["\s:=]*[a-z0-9]{16,}', 'api_key=***'),
        (r'\d{3}-\d{3}-\d{3}\s\d{2}', '***-***-*** **'),
        (r'\b\d{11}\b', '***********'),
        (r'(?i)token["\s:]*[^\s"]*', 'token=***'),
        (r'https?://[^\s]+', 'https://***'),
        (r'(?i)прокси["\s:]*[^\s]*', 'прокси: ***'),
        (r'(?i)proxy["\s:]*[^\s]*', 'proxy: ***'),
        (r'[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+', '*** *** ***'),
        (r'[А-ЯЁ][а-яё]+\s[А-ЯЁ]\.[А-ЯЁ]\.', '*** *.*.'),
    ]

    def filter(self, record):
        msg = record.getMessage()
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, replacement, msg)
        msg = msg.replace('%', '%%')
        record.msg = msg
        record.args = ()
        return True


def mask_sensitive(text: str) -> str:
    if not text or len(text) < 10:
        return text
    return text[:4] + '*' * (len(text) - 8) + text[-4:]


def filter_sensitive_text(text: str) -> str:
    """Apply SensitiveDataFilter patterns to a plain text string."""
    for pattern, replacement in SensitiveDataFilter.SENSITIVE_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def setup_logging(log_dir: str, max_bytes: int = 5 * 1024 * 1024, backup_count: int = 3):
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    main_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=max_bytes,
        backupCount=backup_count, encoding='utf-8'
    )
    main_handler.setLevel(logging.DEBUG)
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
