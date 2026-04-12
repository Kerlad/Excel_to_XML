"""
Централизованное логирование с поддержкой UTF-8
Все модули должны использовать logger = logging.getLogger(__name__)
и вызывать app_logger().setup() при старте приложения.
"""
import os
import logging


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
        root.addHandler(main_handler)
        root.addHandler(error_handler)

        # API logger — отдельный handler
        api_logger = logging.getLogger('api')
        api_logger.addHandler(api_handler)
        api_logger.setLevel(logging.DEBUG)


def setup_logging(log_dir: str):
    """Удобная функция для вызова из main.py."""
    AppLogger().setup(log_dir)
