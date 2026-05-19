import os
from pathlib import Path


def get_app_data_dir() -> str:
    base = os.environ.get('APPDATA')
    if not base:
        base = str(Path.home() / 'AppData' / 'Roaming')
    path = Path(base) / "Excel_to_XML"
    os.makedirs(str(path), exist_ok=True)
    return str(path)


def get_app_log_dir() -> str:
    base = os.environ.get('APPDATA')
    if not base:
        base = str(Path.home() / 'AppData' / 'Roaming')
    path = Path(base) / "Excel_to_XML" / "log"
    os.makedirs(str(path), exist_ok=True)
    return str(path)


def get_base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
