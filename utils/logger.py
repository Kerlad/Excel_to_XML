import os
import logging
import re
from logging.handlers import RotatingFileHandler

_LOG_FORMAT = '%(asctime)s | %(threadName)-12s | %(levelname)-8s | %(name)-25s | %(message)s'
_LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


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


def tail_log(file_path: str, n_lines: int = 1000) -> list[str]:
    """
    Efficiently read the last N lines from a log file.
    Reads from the end of the file using seek, never loads the whole file.
    Returns a list of lines (without trailing newline).
    """
    if not os.path.exists(file_path):
        return [f"[Файл не найден: {file_path}]"]

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

            # trim to n_lines, skip first if it's a partial line
            if len(lines) > n_lines:
                lines = lines[-n_lines:]
            elif lines and lines[0] == '' and pos > 0:
                lines = lines[1:]

            lines = [l.rstrip('\r') for l in lines]
            return lines
    except OSError as e:
        return [f"[Ошибка чтения лога: {e}]"]


def get_log_files(log_dir: str) -> dict[str, str]:
    """
    Return dict mapping log type -> full path for all log files in the directory.
    Includes rotated backups (app.log.1, app.log.2, etc.) sorted by recency.
    """
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
