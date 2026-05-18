import os


def get_app_data_dir() -> str:
    path = os.path.join(get_base_dir(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def get_app_log_dir() -> str:
    path = os.path.join(get_base_dir(), "log")
    os.makedirs(path, exist_ok=True)
    return path


def get_base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
