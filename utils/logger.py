"""
Централизованное логирование с поддержкой UTF-8
Все модули должны использовать logger = logging.getLogger(__name__)
и вызывать app_logger().setup() при старте приложения.
"""
import os
import logging
import re


class SensitiveDataFilter(logging.Filter):
    """Фильтр для удаления конфиденциальных данных из логов."""
    
    SENSITIVE_PATTERNS = [
        # Пароли
        (r'(?i)password["\s:]*[^\s"]*', 'password=***'),
        (r'(?i)passwd["\s:]*[^\s"]*', 'passwd=***'),
        (r'(?i)пароль["\s:]*[^\s"]*', 'пароль=***'),
        (r'(?i)"password"\s*:\s*"[^"]*"', '"password":"***"'),
        # Логины
        (r'(?i)username["\s:]*[^\s"]*', 'username=***'),
        (r'(?i)login["\s:]*[^\s"]*', 'login=***'),
        (r'(?i)логин["\s:]*[^\s"]*', 'логин=***'),
        (r'(?i)"username"\s*:\s*"[^"]*"', '"username":"***"'),
        # Прокси с credentials (любой URL с @ - содержит пароль)
        (r'https?://[^:]+:[^@]+@[^\s]+', 'https://***:***@***'),
        (r'http://[^:]+:[^@]+@[^\s]+', 'http://***:***@***'),
        # API ключи (32+ символов hex)
        (r'(?i)api[_-]?key["\s:]*[a-f0-9]{16,}', 'api_key=***'),
        # СНИЛС
        (r'\d{3}-\d{3}-\d{2}\s\d{2}', '***-***-** ****'),
        # Токены
        (r'(?i)token["\s:]*[^\s"]*', 'token=***'),
        # Прокси URL (без credentials)
        (r'https?://[^\s]+', 'https://***'),
        # Proxy слово
        (r'(?i)прокси["\s:]*[^\s]*', 'прокси: ***'),
        (r'(?i)proxy["\s:]*[^\s]*', 'proxy: ***'),
    ]
    
    def filter(self, record):
        msg = record.getMessage()
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, replacement, msg)
        # Экранируем % чтобы избежать ошибок форматирования
        msg = msg.replace('%', '%%')
        record.msg = msg
        return True


class AppLogger:
    """Централизованный менеджер логирования."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def setup(self, log_dir: str, level: int = logging.DEBUG):
        """
        Настройка логирования.

        log_dir — директория для файлов логов
        level — уровень логирования
        """
        os.makedirs(log_dir, exist_ok=True)

        # Главный лог — все сообщения
        main_handler = logging.FileHandler(
            os.path.join(log_dir, "app.log"), encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)

        # Лог ошибок
        error_handler = logging.FileHandler(
            os.path.join(log_dir, "error.log"), encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)

        # Лог API
        api_handler = logging.FileHandler(
            os.path.join(log_dir, "api.log"), encoding='utf-8'
        )
        api_handler.setLevel(logging.DEBUG)

        # Формат
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        main_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        api_handler.setFormatter(formatter)

        # Root logger
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        # Убираем старые handlers (при перезапуске)
        for h in root.handlers[:]:
            root.removeHandler(h)
        
        # Добавляем фильтр для чувствительных данных
        sensitive_filter = SensitiveDataFilter()
        main_handler.addFilter(sensitive_filter)
        error_handler.addFilter(sensitive_filter)
        
        root.addHandler(main_handler)
        root.addHandler(error_handler)

        # API logger — отдельный handler
        api_logger = logging.getLogger('api')
        api_handler.addFilter(sensitive_filter)
        api_logger.addHandler(api_handler)
        api_logger.setLevel(logging.DEBUG)


def setup_logging(log_dir: str):
    """Удобная функция для вызова из main.py."""
    AppLogger().setup(log_dir)
