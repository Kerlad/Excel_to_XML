import os
from pathlib import Path
from typing import Optional


def get_app_data_dir() -> str:
    """Возвращает путь к директории данных приложения (%APPDATA%/Excel_to_XML)."""
    base: Optional[str] = os.environ.get('APPDATA')
    if not base:
        base = str(Path.home() / 'AppData' / 'Roaming')
    path = Path(base) / "Excel_to_XML"
    os.makedirs(str(path), exist_ok=True)
    return str(path)


def get_app_log_dir() -> str:
    """Возвращает путь к директории логов (%APPDATA%/Excel_to_XML/log)."""
    base: Optional[str] = os.environ.get('APPDATA')
    if not base:
        base = str(Path.home() / 'AppData' / 'Roaming')
    path = Path(base) / "Excel_to_XML" / "log"
    os.makedirs(str(path), exist_ok=True)
    return str(path)


def get_resource_dir() -> str:
    """Возвращает корневую директорию проекта (с ресурсами: schema, templates, assets).
    Не использовать для runtime-данных — используйте get_app_data_dir()."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
